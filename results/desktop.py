#!/usr/bin/env python3

#{{{ imports
import glob
import itertools
import math
import os
import re
import subprocess
import xdg.IconTheme
#}}}


MOD_BIT_SHIFT = 1
MOD_BIT_CTRL = 1 << 1
MOD_BIT_ALT = 1 << 2

class Results: # need to remove duplicates
#{{{ def __init__(maxResults, maxResultsCancel)
	def __init__(self, maxResults, maxResultsCancel):
		self.desktops = []
		self.maxResults = maxResults
		self.maxResultsCancel = maxResultsCancel

		pathIterators = ();
		if os.path.isdir(os.path.expanduser("~") + "/.local/share/applications"):
			pathIterators += (glob.iglob(os.path.expanduser("~") + "/.local/share/applications" + "/**/*.desktop", recursive=True),);
		if os.path.isdir("/usr/local/share/applications"):
			pathIterators += (glob.iglob("/usr/local/share/applications" + "/**/*.desktop", recursive=True),);
		if os.path.isdir("/usr/share/applications"):
			pathIterators += (glob.iglob("/usr/share/applications" + "/**/*.desktop", recursive=True),);
		for path in itertools.chain(*pathIterators):
			Name = Keywords = Icon = TryExec = Exec = Path = Terminal = Type = abort = False

	#{{{ get values
			# not using pyXDG for this as it doesn't have getKeywords so would have to anyway
			try:
				desktop = open(path, "r")
			except OSError:
				continue
			for line in desktop: # needs NotShowIn and OnlyShowIn, localized Name
				if line[0] in '#[':
					continue
				try:
					key, value = line.split("=", 1)
				except ValueError:
					continue
				key = key.strip()
				if key:
					if Name == False and key == "Name":
						Name = value.strip()
					if Keywords == False and key == "Keywords":
						Keywords = value.strip()
					if Icon == False and key == "Icon":
						Icon = value.strip()
					if TryExec == False and key == "TryExec":
						TryExec = value.strip()
					if Exec == False and key == "Exec":
						Exec = value.strip()
					if Path == False and key == "Path":
						Path = value.strip()
					if Terminal == False and key == "Terminal":
						Terminal = value.strip()
					if Type == False and key == "Type":
						Type = value.strip()
						if Type != "Application":
							abort = True
							break
					if key in ["NoDisplay", "Hidden"]:
						abort = value.strip()
						if abort in ["true", "1"]:
							abort = True
							break
			desktop.close()
	#}}}

			if (
				abort == True or
				not (Name and Exec) or
				(TryExec and not os.access(TryExec, os.X_OK))
			):
				continue
			self.desktops.append([
				Name,
				Keywords or "",
				(xdg.IconTheme.getIconPath(Icon, 128) if Icon else "") or "",
				Exec,
				Path,
				Terminal in ["true", "1"]
			])
#}}}

#{{{ def getResults(content)
	def getResults(self, content):
		if re.search("^\s*$", content):
			return []
		results = []
		resultsMatch = []
		resultsKeywords = []
		for index, result in enumerate(self.desktops):
			match = re.search("\W" + re.escape(content.lower()) + "\w*", " " + result[0].lower())
			if match:
				resultsMatch.append(len(match.group(0)))
				results.append([result[2] if result[2][-4:] == ".png" else "open: ", result[0], index])
			elif content.lower() in result[1].lower().split(";"):
				resultsKeywords.append([result[2] if result[2][-4:] == ".png" else "open: ", result[0], index])
		results = [result for _, result in sorted(zip(resultsMatch, results))]
		results = resultsKeywords + results
		if len(results) > self.maxResultsCancel:
			return []
		if not math.isinf(self.maxResults):
			return results[:self.maxResults]
		else:
			return results
#}}}

#{{{ def selectResult(index)
	def selectResult(self, index, mods):
		command = re.sub("(?: %\w)+$", "", self.desktops[index][3])
		if self.desktops[index][4]:
			command = "cd " + self.desktops[index][4] + "&& " + command
		command = command.replace("'", "\\'") # not sure what else needs escaping (if anything), need examples of broken things
		if self.desktops[index][5] and not mods & MOD_BIT_SHIFT:
			subprocess.Popen("xterm -e '" + command + "; $SHELL'", shell=True) # need to figure out options for result generators and have one for terminal
		else:
			subprocess.Popen(command, shell=True)
#}}}
