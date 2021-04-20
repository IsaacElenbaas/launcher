#!/usr/bin/env python3

#{{{ imports
import importlib
import math
import subprocess
import sys
import time
import traceback

import cairocffi as cairo
import cairocffi.xcb
import xcffib as xcb
import xcffib.xproto
import xcffib.render
#}}}

#{{{ options
# need color+styling options
# selecting content
# prefix highlight
# spell checker
# unit conversion
# open in editor

positionY = 1/3 # ratio of monitor height to move window down from top
targetWidth = 3/8 # of monitor width at 16:9, though it is relative to height to keep font size standard
mainRatio = 1/15 # changes main height (which affects font size)
selectedRatio = 0 # optional, changes selected height (which affects font size)
otherRatio = 0 # optional, changes other height (which affects font size)
textPadding = 0 # optional if textPaddingRatio set, on each side, takes priority
textPaddingRatio = 1/4 # optional, on each side relative to element height
maxResults = 0 # optional
maxResultsPer = 0 # optional, per script
maxResultsPerCancel = 0#7 # optional, if a script has more than this many it won't display *any*

resultSources = ["calc", "desktop"]
#}}}


#{{{ def processKey(keycode, down)
def processKey(keycode, down):
	global mods, content, position, selected
	keysym = keysyms[keysymsPer*(keycode-setup.min_keycode)]

	#{{{ mods
	if keysym == 65505 or keysym == 65506: # shift
		mods ^= MOD_BIT_SHIFT
	elif keysym == 65507 or keysym == 65508: # ctrl
		mods ^= MOD_BIT_CTRL
	elif keysym == 65513 or keysym == 65514: # alt
		mods ^= MOD_BIT_ALT
	#}}}

	#{{{ special
	elif keysym == 65307: # escape
		close()
	elif (keysym == 65293 or keysym == 65421) and down: # enter
		updateResults(True) # for if enter was queued and so at least one letter was not added to result queury
		i = 0
		for resultGroupIndex, resultGroup in enumerate(results):
			i += len(resultGroup)
			if i >= selected+1:
				i-=len(resultGroup)
				break
		resultSources[resultGroupIndex].selectResult(results[resultGroupIndex][selected-i][2], mods)
		close()
	elif keysym == 65288 and down: # backspace
		if position:
			position -= 1
			content = content[:position]+content[position+1:]
			updateResults(False)
			return True
		return False
	elif (keysym == 65535 or keysym == 65439) and down: # delete
		if len(content) == position:
			return False
		content = content[:position] + content[position+1:]
		updateResults(False)
		return True
	#}}}

	#{{{ movement
	elif (keysym == 65361 or keysym == 65430) and down: # left
		position = max(0, position-1)
		paint()
	elif (keysym == 65364 or keysym == 65433) and down: # down
		selected = min(selected+1, lenResults-1)
		paint()
	elif (keysym == 65362 or keysym == 65431) and down: # up
		selected = max(0, selected-1)
		paint()
	elif (keysym == 65360 or keysym == 65429) and down: # home
		position = 0
		paint()
	elif (keysym == 65367 or keysym == 65436) and down: # end
		position = len(content)
		paint()
	elif (keysym == 65363 or keysym == 65432) and down: # right
		position = min(len(content), position+1)
		paint()
	#}}}

	#{{{ text
	else:
		keysym = keysyms[keysymsPer*(keycode-setup.min_keycode)+(mods & MOD_BIT_SHIFT)]
		if keysym != 0 and ord(chr(keysym)) < 128 and down:
			content = content[:position] + chr(keysym) + content[position:]
			position += 1
			updateResults(False)
			return True
		return False
	#}}}
#}}}

#{{{ def updateResults()
def updateResults(enter):
	global selected, results, lenResults
	if not enter:
		selected = 0
	results = []
	for resultSource in resultSources:
		if checkEvent(False): # cancels result creation if more was typed
			break
		results.append(resultSource.getResults(content))
	else:
		lenResults = 0
		for resultGroup in results:
			lenResults += len(resultGroup)
		lenResults = min(maxResults, lenResults)
		if not enter:
			paint()
#}}}

#{{{ class paintClass()
# I mean to treat init+call as a single function because they can (should) be read as one (first paint is the same as subsequent ones, just saves what it can)
class paintClass():
	#{{{ def paint()
		#{{{ def __init__()
	def __init__(self):
		global surface, context, mainSurface, selectedSurface, otherSurface

			#{{{ draw main background
		mainSurface = cairo.ImageSurface(cairo.FORMAT_RGB24, round(windowWidth), round(mainHeight))
		mainContext = cairo.Context(mainSurface)
		self.roundedRect(mainContext, 0, 0, round(windowWidth), round(mainHeight), 0, 1, 1, 1, False)
		mainSurface.flush()
			#}}}

			#{{{ draw selected background
		selectedSurface = cairo.ImageSurface(cairo.FORMAT_RGB24, round(windowWidth), round(selectedHeight))
		selectedContext = cairo.Context(selectedSurface)
		selectedContext.set_source_rgb(0.5, 0.5, 0.5)
		self.roundedRect(selectedContext, 0, 0, round(windowWidth), round(selectedHeight), 0, 1, 1, 1, False)
		selectedSurface.flush()
			#}}}

			#{{{ draw unselected background
		otherSurface = cairo.ImageSurface(cairo.FORMAT_RGB24, round(windowWidth), round(otherHeight))
		otherContext = cairo.Context(otherSurface)
		otherContext.set_source_rgb(0.25, 0.25, 0.25)
		self.roundedRect(otherContext, 0, 0, round(windowWidth), round(otherHeight), 0, 1, 1, 1, False)
		otherSurface.flush()
			#}}}

		surface = cairo.xcb.XCBSurface(conn, window, self.findRootVisual(conn), round(windowWidth), round(windowHeight))
		context = cairo.Context(surface)
		#}}}

	def __call__(self):
		global textOffset
		#conn.core.ClearArea(False, window, 0, 0, 0, 0) # don't know what this does and xcb docs are nonexistent
		conn.core.ConfigureWindow(window, xcb.xproto.ConfigWindow.Height, [ round(mainHeight)+(round(selectedHeight) if lenResults else 0)+round(otherHeight)*max(0, lenResults-1) ])

		#{{{ draw content
		context.set_source_surface(mainSurface)
		context.rectangle(0, 0, round(windowWidth), round(mainHeight))
		context.fill()
		padding = textPadding if textPadding else round(textPaddingRatio*mainHeight)

			#{{{ text sideways scrolling
		# allows content greater than the width
		context.move_to(-textOffset, 0)
		context.text_path(content[:position])
		linePos = context.get_current_point()[0]
		textOffset += max(0, linePos-(round(windowWidth)-padding)) # typing past end
		textOffset -= max(0, padding-linePos) # moving back left with arrows or home
		context.text_path(content[position:])
		textOffset -= max(0, (round(windowWidth)-padding)-context.get_current_point()[0]) # deleting and end visible
		textOffset = max(-padding, textOffset) # stops above line from forcing right aligned text
		context.new_path()
			#}}}

			#{{{ draw text and position line
		context.set_source_rgb(1, 1, 1)
		context.move_to(-textOffset, round(mainHeight)-padding)
		context.set_font_size((round(mainHeight)-2*padding)*96/72)
		context.show_text(content[:position])
		linePos = context.get_current_point()
		context.show_text(content[position:])
		context.rectangle(linePos[0], linePos[1]-round(1.25*(mainHeight-2*padding)), 1, round(1.5*(round(mainHeight)-2*padding)))
		context.fill()
			#}}}
		#}}}

		#{{{ draw results
		for resultIndex in range(0, lenResults):

			#{{{ get result
			i = 0
			for resultGroupIndex, resultGroup in enumerate(results): # gets index of result group in results with result of index
				i += len(resultGroup)
				if i > resultIndex:
					i-=len(resultGroup)
					break
			# result of resultIndex is now accessible as results[resultGroupIndex][resultIndex-i]
			#}}}

			if resultIndex == selected:
			#{{{ draw selected
				context.set_source_surface(selectedSurface, 0, mainHeight+resultIndex*otherHeight)
				context.rectangle(0, mainHeight+resultIndex*otherHeight, round(windowWidth), round(selectedHeight))
				context.fill()
				self.resultText(mainHeight+resultIndex*otherHeight, selectedHeight, results[resultGroupIndex][resultIndex-i])
			#}}}
			else:
				if resultIndex < selected:
			#{{{ draw unselected above selected
					context.set_source_surface(otherSurface, 0, mainHeight+resultIndex*otherHeight)
					context.rectangle(0, mainHeight+resultIndex*otherHeight, round(windowWidth), round(otherHeight))
					context.fill()
					self.resultText(mainHeight+resultIndex*otherHeight, otherHeight, results[resultGroupIndex][resultIndex-i])
			#}}}
				else:
			#{{{ draw unselected below selected
					context.set_source_surface(otherSurface, 0, mainHeight+(resultIndex-1)*otherHeight+selectedHeight)
					context.rectangle(0, mainHeight+(resultIndex-1)*otherHeight+selectedHeight, round(windowWidth), round(otherHeight))
					context.fill()
					self.resultText(mainHeight+(resultIndex-1)*otherHeight+selectedHeight, otherHeight, results[resultGroupIndex][resultIndex-i])
			#}}}
		#}}}

		surface.flush()
		conn.flush()
	#}}}

	#{{{ def roundedRect(context, x, y, width, height, radius, fadeR, fadeG, fadeB, fadeToPoint)
	def roundedRect(self, context, x, y, width, height, radius, fadeR, fadeG, fadeB, fadeToPoint):
		if min(width, height) < 2*radius:
			raise ValueError("Radius is too large for dimensions!")

		#{{{ corner fade
		rectColor = context.get_source().get_rgba()
		with context:
			for sideY in [0, 1]:
				for sideX in [0, 1]:
					# either center of fillet or corner of rect
					fadeToX = x+sideX*width+(0 if fadeToPoint else (-1 if sideX else 1)*radius)
					fadeToY = y+sideY*height+(0 if fadeToPoint else (-1 if sideY else 1)*radius)
					fadeToRadius = 1/2 if fadeToPoint else math.ceil(math.sqrt(2)*radius)
					# center of fillet
					filletX = x+sideX*width+(-1 if sideX else 1)*radius
					filletY = y+sideY*height+(-1 if sideY else 1)*radius
					fadeCorner = cairo.RadialGradient(fadeToX, fadeToY, fadeToRadius, filletX, filletY, radius)
					fadeCorner.add_color_stop_rgb(0, fadeR, fadeG, fadeB)
					fadeCorner.add_color_stop_rgba(1, *rectColor)
					context.set_source(fadeCorner)
					context.rectangle(x+(width-radius if sideX else 0), y+(height-radius if sideY else 0), radius, radius)
					context.fill()
		#}}}

		#{{{ rounded rectangle
		context.new_sub_path()
		context.arc(x+width-radius, y+height-radius, radius, 0, 1/2*math.pi)
		context.arc(x+radius, y+height-radius, radius, 1/2*math.pi, math.pi)
		context.arc(x+radius, y+radius, radius, math.pi, 3/2*math.pi)
		context.arc(x+width-radius, y+radius, radius, 3/2*math.pi, 2*math.pi)
		context.close_path()
		context.fill()
		#}}}
	#}}}

	#{{{ def resultText(context, y, height, result)
	def resultText(self, y, height, result):
		global context
		padding = textPadding if textPadding else round(textPaddingRatio*mainHeight)
		if result[0][-4:] == ".png": # none of the numbers in this section are what they should be but this works and that doesn't
			imageSurface = cairo.ImageSurface.create_from_png(result[0])
			matrix = context.get_matrix()
			scale = (height-padding/2)/imageSurface.get_width()
			context.scale(scale, scale)
			context.set_source_surface(imageSurface, padding/2/scale, (y+padding/4)/scale)
			context.paint()
			imageSurface.finish()
			context.set_matrix(matrix)
			context.set_source_rgb(1, 1, 1)
			context.set_font_size((round(height)-2*padding)*96/72)
			context.move_to(height+padding/2, y+round(height)-padding)
		else:
			context.set_source_rgb(1, 1, 1)
			context.set_font_size((round(height)-2*padding)*96/72)
			context.move_to(padding, y+round(height)-padding)
			context.show_text(result[0])
		context.show_text(result[1])
		context.fill()
	#}}}

	#{{{ def findRootVisual(conn)
	def findRootVisual(self, conn):
		default_screen = conn.setup.roots[conn.pref_screen]
		for i in default_screen.allowed_depths:
			for v in i.visuals:
				if v.visual_id == default_screen.root_visual:
					return v
	#}}}
#}}}

#{{{ def checkEvent(wait)
# this acts as the main loop, but if called with wait=False will handle any pending events and return whether content was updated
# that allows handling any key events between result scripts and not wasting time getting outdated results
def checkEvent(wait):
	global paint, endFocus
	updatedContent = False
	while True:
		event = conn.poll_for_event() # fixes very fast events, eg. qmk shifted keys
		if not event: # this is so that even on startup if there are pending events they are handled
			if wait:
				event = conn.wait_for_event()
			else:
				return updatedContent

	#{{{ event handling
		if isinstance(event, xcb.xproto.ExposeEvent):
			try:
				paint()
			except NameError:
				paint = paintClass()
				paint()
		elif isinstance(event, xcb.xproto.KeyPressEvent):
			if processKey(event.detail, True):
				updatedContent = True
		elif isinstance(event, xcb.xproto.KeyReleaseEvent):
			processKey(event.detail, False)
		elif isinstance(event, xcb.xproto.ButtonPressEvent):
			reply = conn.core.GetInputFocus().reply()
			endFocus = reply.focus if reply.focus != window else endFocus
			conn.core.SetInputFocus(xcb.xproto.InputFocus._None, window, xcb.CurrentTime)
			conn.flush()
	#}}}
#}}}

#{{{ class Monitor
# can't figure out how to get these through bash xrandr or xcffib
class Monitor:
	def __init__(self):
		focus = subprocess.Popen("herbstclient list_monitors | grep [FOCUS]", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0].decode("utf-8")
		indexX = focus.index("x")
		self.width = int(focus[focus.index(" ")+1:indexX])
		indexPlus = focus.index("+")
		self.height = int(focus[indexX+1:indexPlus])
		offsets = focus[indexPlus+1:]
		self.offsetX = int(offsets[0:offsets.index("+")])
		self.offsetY = int(offsets[offsets.index("+")+1:offsets.index(" ")])
#}}}

#{{{ setup
	#{{{ xcb setup
conn = xcb.connect()
conn.render = conn(xcb.render.key)
setup = conn.get_setup()
root = setup.roots[conn.pref_screen].root
depth = setup.roots[conn.pref_screen].root_depth
visual = setup.roots[conn.pref_screen].root_visual
window = conn.generate_id()
	#}}}

	#{{{ window size
currentMonitor = Monitor()
if currentMonitor.width > currentMonitor.height: # size is actually relative to height as it better represents monitor size
	windowWidth = currentMonitor.height*targetWidth*16/9
else: # goes relative to "width" if vertical monitor
	windowWidth = currentMonitor.width*targetWidth
mainHeight = mainRatio*windowWidth
selectedHeight = (selectedRatio or mainRatio)*windowWidth
otherHeight = (otherRatio or mainRatio)*windowWidth
windowX = currentMonitor.offsetX+(currentMonitor.width-windowWidth)/2
windowY = currentMonitor.offsetY+currentMonitor.height*positionY
windowHeight = currentMonitor.height - windowY # really window max height, actual height changes to keep transparency
	#}}}

	#{{{ window setup
conn.core.CreateWindow(depth, window, root,
                       round(windowX), round(windowY), round(windowWidth), round(mainHeight), 0,
                       xcb.xproto.WindowClass.InputOutput, visual,
                       xcb.xproto.CW.OverrideRedirect | xcb.xproto.CW.EventMask,
                       [ True, xcb.xproto.EventMask.Exposure | xcb.xproto.EventMask.ButtonPress | xcb.xproto.EventMask.ButtonRelease | xcb.xproto.EventMask.KeyPress | xcb.xproto.EventMask.KeyRelease ])
conn.core.MapWindow(window)
endFocus = conn.core.GetInputFocus().reply().focus
conn.core.SetInputFocus(xcb.xproto.InputFocus._None, window, xcb.CurrentTime)
conn.flush()
	#}}}

	#{{{ keyboard setup
mods = 0
MOD_BIT_SHIFT = 1
MOD_BIT_CTRL = 1 << 1
MOD_BIT_ALT = 1 << 2
reply = conn.core.GetKeyboardMapping(setup.min_keycode, setup.max_keycode-setup.min_keycode+1).reply()
keysyms = reply.keysyms
keysymsPer = reply.keysyms_per_keycode
	#}}}

	#{{{ misc.
content = "" # user input
position = 0 # in user input
textOffset = 0 # used when user input too long
results = []
selected = 0 # result index
maxResults = min(maxResults or math.inf, math.floor((windowHeight-mainHeight-selectedHeight)/otherHeight)+1)
lenResults = 0 # result count, as it has nested arrays
for index, resultSource in enumerate(resultSources):
	resultSources[index] = importlib.import_module("results." + resultSource).Results(maxResultsPer or math.inf, maxResultsPerCancel or math.inf)
	#}}}
#}}}

#{{{ def close()
def close():
	conn.core.DestroyWindow(window)
	conn.core.SetInputFocus(xcb.xproto.InputFocus._None, endFocus, xcb.CurrentTime)
	conn.flush()
	if "--startuptime" not in sys.argv[1:]:
		time.sleep(1) # SetInputFocus didn't work sometimes w/o this
	conn.disconnect()
	sys.exit()
#}}}

try:
	checkEvent("--startuptime" not in sys.argv[1:])
except Exception:
	traceback.print_exc()
	close()
close()
