#!/usr/bin/env python3

#{{{ imports
import math
import re
import subprocess
import sys # use-eval needs to be swapped for config file parsing
#}}}


def fstr(num):
	return re.sub("(?:(\.[1-9]+)|\.)0{10,}[1-9]*$", "\\1", format(num, ".20f"))


class Results:
#{{{ def __init__(maxResults, maxResultsCancel)
	def __init__(self, *args):
		pass
#}}}

#{{{ def getResults(content)
	def getResults(self, content):
		if re.search("^\s*$", content):
			return []
		content = re.sub("\s*", "", content)
		content = re.sub("=?{(.*)};?", "=\\1;", content)
		equations = content.split(";")
		self.functions = self.defaultFunctions.copy()
		self.vars = self.defaultVars.copy()
		self.privateVars = {}
		for equation in equations:

	#{{{ sanity checks
			if equation == "":
				continue
			# remember getResults is running every character typed, loop is worth it to avoid unnecessary work
			enclosing = ""
			for char in equation:
				if char in "([": # arrays are supported at least for arguments, not sure if more is needed
					enclosing += char
				elif char == ")":
					if len(enclosing) and enclosing[-1] == "(":
						enclosing = enclosing[:-1]
					else:
						if "calc" in sys.argv[0] and len(sys.argv[1:]):
							raise ValueError("Unbalanced parentheses!")
						else:
							return []
				elif char == "]":
					if len(enclosing) and enclosing[-1] == "[":
						enclosing = enclosing[:-1]
					else:
						if "calc" in sys.argv[0] and len(sys.argv[1:]):
							raise ValueError("Unbalanced parentheses!")
						else:
							return []
			if enclosing:
				if "calc" in sys.argv[0] and len(sys.argv[1:]):
					raise ValueError("Unbalanced parentheses!")
				else:
					return []
			# check for illegal characters for early cancel?
	#}}}

	#{{{ format to be solved (and more sanity checks)
			if re.search("\)\d", equation): # (2*2)2 isn't allowed
				return []
			equation = re.sub("\)([a-zA-Z(])", ")*\\1", equation) # but (2*2)x is - also, (2*2)(2*2)
			equation = re.sub("(?<!\w)(\d+\.?\d*)([a-zA-Z(])", "\\1*\\2", " " + equation)[1:] # 2.5x, 2(2*2) but ignores atan2(1)
			equation = re.sub("-([a-zA-Z(])", "-1*\\1", equation) # -(2*2), -pow(2, 2)
			if "-e" in sys.argv[1:] or "--use-eval" in sys.argv[1:]:
				equation = re.sub("\^", "**", equation)
			else:
				equation = re.sub("\*\*", "^", equation)
	#}}}

			if "calc" in sys.argv[0] and len(sys.argv[1:]):
				print("Solving (top level): " + equation)
			if "calc" in sys.argv[0] and len(sys.argv[1:]):
				solved = self.solve(equation)
			else:
				try:
					solved = self.solve(equation)
				except Exception:
					return []
		if "calc" in sys.argv[0] and len(sys.argv[1:]):
			return solved
		else:
			return [["calc: ", solved, solved]]
#}}}

#{{{ def solve(equation)
	# finds each first-level group and solves it (recurses) then (after P) solves self and returns
	# due to that after variable expansion it's always working with only a simple symbols-only equation
	# as xpow(2, 2), though valid, is changed to x4.0 while solving, we have to allow that too. This can cause confusion if you make a variable called x4 (the variable has priority), so I recommend x_4 format
	def solve(self, equation):
		if len(equation) == 0:
			return ""
		if equation[0] in "^*/%+" or equation[-1] in "^*/%" or (equation[-1] == "+" and equation[-2] != "+"):
			raise ValueError("Starting or ending with operator!")
		if equation.count("=") >= 1:
	#{{{ user-defined variables and functions
			split = equation.split("=", 1)
			if "(" in split[0]:
				if not (split[0].count("(") == 1 and split[0].count(")") == 1 and split[0].index(")") == len(split[0])-1):
					# params need to be simple names, refer to them as assumed type (once types are added. . . ) if needed as normally in Python. Parentheses check is here, everything else is handled when called as variables won't resolve
					raise ValueError("Incorrect function format!")
				self.functions[split[0][:split[0].index("(")]] = split[0][split[0].index("("):] + split[1]
				return ""
			else:
				if not re.search("^[a-zA-Z_]\w*(\^|\*|/|%|\+|-)?$", split[0]):
					raise ValueError("Invalid variable name!")
				else:
					solved = self.solve(split[1] if not split[0][-1] in "^*/%+-" else split[0][:-1] + "=" + split[0][:-1] + split[0][-1] + "(" + split[1] + ")")
					self.vars[split[0]] = float(solved)
					return solved
	#}}}

	#{{{ P
		while True:
			start = equation.find("(")
			if not start+1:
				break
			length = 1
			enclosing = 1
			notAllDigits = 0
			for index, char in enumerate(equation[start+1:]):
				length += 1
				if char == "(":
					enclosing += 1
				elif char == ")":
					enclosing -= 1
				elif char not in "0123456789":
					notAllDigits += 1
				if not enclosing:
					break
			if enclosing:
				raise ValueError("Unbalanced parentheses!")
			if notAllDigits:
				solvedContents = self.solve(equation[start+1:start+length-1])
			else:
				solvedContents = equation[start+1:start+length-1]
			if "calc" in sys.argv[0] and len(sys.argv[1:]):
				print("Working on section: " + equation[:start+1] + solvedContents + equation[start+length-1:])
			possibleFunction = re.search("\w*$", equation[:start])
			if possibleFunction:

		#{{{ functions
				#for i in range(possibleFunction.end()-possibleFunction.start()-1, -1, -1): # smaller functions have priority
				for i in range(0, possibleFunction.end()-possibleFunction.start()): # larger functions have priority
					if possibleFunction.group()[i:] in self.functions:
						function = self.functions[possibleFunction.group()[i:]]
						if "calc" in sys.argv[0] and len(sys.argv[1:]): # causes double print, but shows what function actually was called. In cases of xsin(0), you would get xsin(0) and then sin(0)
							print([possibleFunction.group()[i:] + "(" + solvedContents + ")"]) # array to be clearer in debug like all other operations
						# maybe json parsing then iterate over contents with float()? eval works fine though and it has to be all numbers here
						# issue is you have to handle things like "2, [[2, 2], 2]" so can't split by commas
						#arguments = tuple(float(num) for num in solvedContents.split(",")) # doesn't work with array params
						arguments = eval(solvedContents) # returns single number or tuple
						if not (type(arguments) is tuple): # ensure it is a tuple so can be passed
							arguments = (arguments,);
						start -= len(possibleFunction.group())-i
						if type(function) == str:
							for index, paramName in enumerate(function[1:function.index(")")].split(",")):
								self.privateVars[paramName] = arguments[index]
							solvedContents = self.solve(function[function.index(")")+1:])
							self.privateVars = {}
						else:
							solvedContents = fstr(function(*arguments))
						equation = equation[:start] + "(" + solvedContents + ")" + equation[start+length+len(possibleFunction.group())-i:]
						length = len(solvedContents)+2
						break
		#}}}

			# removes parentheses to continue on next
			if solvedContents[0] == "-" and start+length < len(equation) and equation[start+length] == "^": # fixes powers of negative numbers
				if equation[start+length+1] == "(":
					equation = equation[:start] + "pow(" + solvedContents + "," + equation[start+length+2:]
					if "calc" in sys.argv[0] and len(sys.argv[1:]):
						print("Working on section: " + equation)
				else:
					split = re.split("\d(?=\D)|[a-zA-Z_](?=[^a-zA-Z_])", equation[start+length+1:])
					if "calc" in sys.argv[0] and len(sys.argv[1:]):
						print("[" + solvedContents + ", '^', " + split[0] + "]") # array to be clearer in debug like all other operations
					equation = equation[:start] + fstr(math.pow(float(solvedContents), float(self.solve(split[0])))) + (split[1] if len(split) == 2 else "")
			else:
				equation = equation[:start] + solvedContents + equation[start+length:]
	#}}}

		while True: # AD can deal with +- but nothing else (and this would save cycles + many more regex matches anyway)
			minusPlus = re.search("[+-]{2,}", equation)
			if not minusPlus:
				break
			if minusPlus.group()[0] == minusPlus.group()[1] and len(minusPlus.group()) == 2 and len(equation) == minusPlus.end():
				equation = self.solve(equation[:minusPlus.start()+1] + "=1")
			else:
				equation = equation[:minusPlus.start()] + ("-" if minusPlus.group().count("-")%2 else "+") + equation[minusPlus.end():]

	#{{{ variable expansion
		expandedVars = False
		allVars = {**self.vars, **self.privateVars}
		while True:
			possibleVar = re.search("[a-zA-Z_]\w*", equation)
			if not possibleVar:
				break
			expandedVars = True
			#for i in range(-1, possibleVar.end()-possibleVar.start()-1): # smaller vars have priority
			for i in range(possibleVar.end()-possibleVar.start(), 0, -1): # larger vars have priority
				if possibleVar.group()[:i] in allVars:
					if "calc" in sys.argv[0] and len(sys.argv[1:]):
						print([possibleVar.group()[:i]]) # array to be clearer in debug like all other operations
					head = "^" + equation[:possibleVar.start()] # carat fixes variables at start
					tail = equation[possibleVar.end()-(possibleVar.end()-possibleVar.start()-i):] + "^" # carat fixes variables at end
					equation = head[1:] + ("*" if not head[-1] in "^*/%+-,[" else "") + fstr(allVars[possibleVar.group()[:i]]) + ("*" if not tail[0] in "^*/%+-,]" else "") + tail[:-1]
					break
			else:
				if "calc" in sys.argv[0] and len(sys.argv[1:]):
					print(allVars)
					print(equation)
					print(possibleVar.group())
				raise ValueError("Variable or function not found!")
		if expandedVars and "calc" in sys.argv[0] and len(sys.argv[1:]):
			print("After expanding vars: " + equation)
	#}}}

		# actual solve (eval is safe, it's only numbers and symbols at this point due to the recursive solve parentheses first)
		# not including factorial as its location in PEMDAS isn't clear, it doesn't work with eval, and properly throwing error with negative numbers is hard
		if "calc" in sys.argv[0] and len(sys.argv[1:]):
			print("Solving basic math: " + equation)
		if "-e" in sys.argv[1:] or "--use-eval" in sys.argv[1:]:

	#{{{ EMODAS (eval)
			equation = re.sub("(\d*\.?\d*)%(\d*\.?\d*)", "math.fmod(\\1, \\2)", equation, 1)
			# in the case of current equation being parameters, this is eval'd here and turned back into normal output instead of eval'd above and shoved right in so that things like pow(1, min(2, 3)) work without having to change the function names (the whole recursive parentheses model). If I wanted something to just turn a string into proper evalable text I would have done that
			equation = fstr(eval(equation)).strip("()") # removes parentheses if was args and became tuple
	#}}}

		else:

	#{{{ EMODAS (manual)
		#{{{ E
			while True: # pow() needs to be handled separately as can't properly match `([stuff],` as [stuff] could have any number of nested groups
				split = equation.split("^", 1)
				if not len(split)-1:
					break
				pos0 = re.search("(?<=\D)-?\d*\.?\d*$", " " + split[0]).start()-1
				pos1 = re.search("^-?\d*\.?\d*", split[1]).end()
				if "calc" in sys.argv[0] and len(sys.argv[1:]):
					print([float(split[0][pos0:]), "^", float(split[1][:pos1])])
				equation = split[0][:pos0] + fstr(math.pow(float(split[0][pos0:]), float(split[1][:pos1]))) + split[1][pos1:]
		#}}}

		#{{{ MOD (get it? Multiply, Divide, MODulus?)
			while True:
				multiply = equation.find("*")+1
				divide = equation.find("/")+1
				modulus = equation.find("%")+1
				if not (multiply or divide or modulus):
					break
				minOpPos = min(multiply or math.inf, divide or math.inf, modulus or math.inf)
				operation = "*" if minOpPos == multiply else ("/" if minOpPos == divide else "%")
				split = equation.split(operation, 1)
				# positive lookbehind non-digit makes things like 2+-2*4 get -2 properly and 2-2*4 not grab it. This is necessary as AS is not able to deal with anything but +, -, or +-
				pos0 = re.search("(?<=\D)-?\d*\.?\d*$", " " + split[0]).start()-1
				pos1 = re.search("^-?\d*\.?\d*", split[1]).end()
				if "calc" in sys.argv[0] and len(sys.argv[1:]):
					print([float(split[0][pos0:]), operation, float(split[1][:pos1])])
				if operation == "*":
					equation = split[0][:pos0] + fstr(float(split[0][pos0:])*float(split[1][:pos1])) + split[1][pos1:]
				elif operation == "/":
					equation = split[0][:pos0] + fstr(float(split[0][pos0:])/float(split[1][:pos1])) + split[1][pos1:]
				else:
					equation = split[0][:pos0] + fstr(math.fmod(float(split[0][pos0:]), float(split[1][:pos1]))) + split[1][pos1:]
		#}}}

		#{{{ AS
			while True:
				add = equation.find("+")+1
				subtract = re.search("(?<=\d)-", equation)
				if not (add or subtract):
					break
				add = True if (add or math.inf) < (subtract.start()+1 if subtract else math.inf) else False
				split = equation.split("+", 1) if add else [equation[:subtract.start()], equation[subtract.end():]]
				pos0 = re.search("-?\d*\.?\d*$", split[0]).start() # there won't be operation minus left of split
				pos1 = re.search("^-?\d*\.?\d*", split[1]).end()
				if "calc" in sys.argv[0] and len(sys.argv[1:]):
					print([float(split[0][pos0:]), "+" if add else "-", float(split[1][:pos1])])
				equation = split[0][:pos0] + fstr(float(split[0][pos0:])+(1 if add else -1)*float(split[1][:pos1])) + split[1][pos1:]
		return equation
		#}}}
	#}}}
#}}}

#{{{ defaultVars
	defaultVars = {
		"e": math.e,
		"inf": math.inf,
		"pi": math.pi,
		"tau": math.tau,
	}
#}}}

#{{{ defaultFunctions
	defaultFunctions = { # bin, hex, octal? they would mess up the rest of the equation but would be fine for simple conversions
		"abs": abs,
		"acos": math.acos,
		"acosh": math.acosh,
		"asin": math.asin,
		"asinh": math.asinh,
		"atan": math.atan,
		"atan2": math.pow,
		"atanh": math.atanh,
		"ceil": math.ceil,
		"comb": math.comb,
		"copysign": math.copysign,
		"cos": math.cos,
		"cosh": math.cosh,
		"degrees": math.degrees,
		"dist": math.dist,
		"exp": math.exp,
		"expm1": math.expm1,
		"fabs": math.fabs,
		"factorial": math.factorial,
		"floor": math.floor,
		"fmod": math.fmod,
		"fsum": math.fsum,
		"gcd": math.gcd,
		"hypot": math.hypot,
		"int": int,
		"isqrt": math.isqrt,
		"ldexp": math.ldexp,
		"len": len,
		"log": math.log,
		"log10": math.log10,
		"log1p": math.log1p,
		"log2": math.log2,
		"max": max,
		"min": min,
		"nCr": math.comb,
		"nPr": math.perm,
		"perm": math.perm,
		"pow": math.pow,
		"prod": math.prod,
		"radians": math.radians,
		"remainder": math.remainder,
		"round": round,
		"sin": math.sin,
		"sinh": math.sinh,
		"sqrt": math.sqrt,
		"sum": sum,
		"tan": math.tan,
		"tanh": math.tanh,
		"trunc": math.trunc,
	}
#}}}

#{{{ def selectResult(index)
	def selectResult(self, answer, mods):
		subprocess.Popen("printf " + answer + " | xsel -ib", shell=True)
#}}}

if "calc" in sys.argv[0] and len(sys.argv[1:]):
	print("Input: " + sys.argv[-1])
	print(Results().getResults(str(sys.argv[-1])))
