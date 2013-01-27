#!/usr/bin/env python
"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
#comunication with http://garyc.mooo.com:3232/sketch/
import cairo
import gtk

import time
import urllib2
import xml.dom.minidom

"""
TODO:
-injection test
-draw order bigger to smaller (+ natural)
-filling algorithm
-calculate curvesmooth with bounding box or something (perceptive detail level)
"""

#http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/65212
def baseN(num,b):
    return ((num == 0) and  "0" ) or ( baseN(num // b, b).lstrip("0") + "0123456789abcdefghijklmnopqrstuvwxyz"[num % b])

def base36(num, pad) :
    return baseN(num, 36).rjust(pad, '0')

EX_DRAWING = [[(0, 0), (100, 100), (-100, 0), (100, -100)]]

def boundingBox(line) :
    x1, y1, x2, y2 = float('infinity'), float('infinity'), 0, 0

    for x, y in line :
        if x1 > x : x1 = x
        if x2 < x : x2 = x
        if y1 > y : y1 = y
        if y2 < y : y2 = y

    return (x1, y1, x2, y2)

def rectArea(rect) :
    x1, y1, x2, y2 = rect
    return (x2 - x1) * (y2 - y1)

def SVGVertex(line, curvesmooth = 10):
    line = line.replace(',', ' ').split(' ')

    ln = len(line)
    p = 0

    mode = 'z'

    p1 = (0, 0)
    p2 = (0, 0)
    p3 = (0, 0)
    p4 = (0, 0)

    while p < ln :
        if p >= ln :
            break
        elif line[p] == 'M' :
            mode = 'M'
            p += 1
            continue
        elif line[p] == 'C' :
            mode = 'C'
            p += 7
            p2 = float(line[p - 6]) , float(line[p - 5])
            p3 = float(line[p - 4]) , float(line[p - 3])
            p4 = float(line[p - 2]) , float(line[p - 1])

            dt = 1. / float(curvesmooth - 1)
            for i in range(curvesmooth) :
                t = i*dt
                x = ((1-t)**3)*p1[0] + 3*t*(1-t)*(1-t)*p2[0] + \
                    3*t*t*(1-t)*p3[0] + (t**3)*p4[0]
                y = ((1-t)**3)*p1[1] + 3*t*(1-t)*(1-t)*p2[1] + \
                    3*t*t*(1-t)*p3[1] + (t**3)*p4[1]
                yield (x, y)

            p1 = p4
            #yield p1
            continue
        elif line[p] == 'L' :
            mode = 'L'
            p += 1
            continue
        elif line[p] == 'z' or line[p] == 'Z':
            mode = 'z'
            p += 1
            continue
        elif line[p] == '':
            break

        if mode == 'M' or mode == 'L' :
            p += 2
            p1 = int(float(line[p - 2])) , int(float(line[p - 1]))
            yield p1
            continue

def vertex36(line):
    ln = len(line)
    p = 0

    while p < ln :
        yield int(line[p : p + 2], 36) , int(line[p + 2 : p + 4], 36)
        p = p + 4

def SVGpaths(name):
    doc = xml.dom.minidom.parse(name)
    return [[v for v in SVGVertex(p.attributes['d'].nodeValue)] for p in doc.getElementsByTagName("path")]

def decode(b36str):
    return [[v for v in vertex36(w)] for w in b36str.upper().split()]

# falta padding de zeros
def encode(sketch):
    return ' '.join(["".join([base36(int(p[0]), 2) + base36(int(p[1]), 2) for p in l]) for l in sketch])

def drawShape(ctx, sketch):
    ctx.save()

    ctx.new_path()
    ctx.translate(0, 0)

    for l in sketch :
        ctx.move_to(l[0][0], l[0][1])
        for p in l[1:] :
            ctx.line_to(p[0], p[1])
        ctx.stroke()

    ctx.restore()

class SketchSwapper(gtk.Window):
	def __init__(self):
                self.drawnies = []

		gtk.Window.__init__(self)

		self.set_title("SketchSwapper")
		self.connect('destroy', gtk.main_quit)
		self.set_default_size(900, 600)

		layout = gtk.HBox(False)
		self.add(layout)


		self.drawingarea = gtk.DrawingArea()
		#layout.add(drawingarea)
		layout.pack_start(self.drawingarea, True)
		self.drawingarea.connect('expose_event', self.da_expose)

		toolbar = gtk.Toolbar()
		layout.pack_start(toolbar, False)
		toolbar.set_orientation(gtk.ORIENTATION_VERTICAL)

		b = gtk.ToolButton(gtk.STOCK_CLEAR)
		b.connect("clicked", self.clearDrawnies)
		b.set_tooltip_text("Clear drawing area.")
		toolbar.add(b)

		b = gtk.ToolButton(gtk.STOCK_OPEN)
		b.connect("clicked", self.showLoadSVG)
		b.set_tooltip_text("Load svg file.")
		toolbar.add(b)

		b = gtk.ToolButton(gtk.STOCK_EXECUTE)
		b.connect("clicked", self.sendDrawny)
		b.set_tooltip_text("Send drawing to server.")
		toolbar.add(b)

		b = gtk.ToolButton(gtk.STOCK_OPEN)
		b.connect("clicked", self.retrieveDrawny)
		b.set_tooltip_text("Retrieve drawing from server.")
		toolbar.add(b)

		self.show_all()

	def da_expose (self, da, event):
		ctx = da.window.cairo_create()

		ctx.save()

		ctx.set_line_width(1)

		ctx.move_to(0, 0)
		ctx.rel_line_to(800, 0)
		ctx.rel_line_to(0, 600)
		ctx.rel_line_to(-800, 0)
		ctx.close_path()

		ctx.set_source_rgb (1, 1, 1)
		ctx.fill_preserve ()
		ctx.set_source_rgb (0, 0, 0)
		ctx.stroke ()

		ctx.restore()

		ctx.set_source_rgb(0, 0, 0)

		ctx.set_line_width(3)
		ctx.set_tolerance(0.1)

		ctx.set_line_join(cairo.LINE_JOIN_ROUND)

		drawShape(ctx, self.drawnies)

	def showLoadSVG(self, widget = None) :
		filesel = gtk.FileSelection("Choose file to load.")
		filename = filesel.get_filename()

		def _okClick(w) :
			self.loadSVG(filesel.get_filename())
			filesel.destroy()


		#filesel.connect("destroy", self.destroy)
		# Connect the ok_button to file_ok_sel method
		filesel.ok_button.connect("clicked", _okClick)
	    
		# Connect the cancel_button to destroy the widget
		filesel.cancel_button.connect("clicked",
		                                 lambda w: filesel.destroy())
	    
		filesel.show()

	def loadSVG(self, filename) :
		self.clearDrawnies()
		self.insertDrawny(SVGpaths(filename))

	def sendDrawny(self, widget = None) :
		try :
			print "Getting drawnie from server..."

			f =  urllib2.urlopen('http://garyc.mooo.com:3232/sketch/swap.php', encode(self.drawnies))

			#f = open(url, "r")
			sid = f.read() # swapping id

			r = 'wait'
			while 1 :
				f =  urllib2.urlopen('http://garyc.mooo.com:3232/sketch/get.php?id='+sid)
				r = f.read()
				if r == 'wait' :
					time.sleep(5)
				else :
					break

			self.clearDrawnies()
			self.insertDrawny(decode(r))

		except urllib2.HTTPError:
			print 'HTTP error.'
			return 0

	def retrieveDrawny(self, widget = None) :
		try :
			print "Getting drawnie from server..."

			f =  urllib2.urlopen('http://garyc.mooo.com:3232/sketch/get.php')

			#f = open(url, "r")
			r = f.read()
			self.clearDrawnies()
			self.insertDrawny(decode(r))

		except urllib2.HTTPError:
			print 'HTTP error.'
			return 0

	def clearDrawnies(self, widget = None) :
		self.drawnies = []
		self.drawingarea.queue_draw()

	def insertDrawny(self, drawny) :
		self.drawnies = drawny
		self.drawingarea.queue_draw()
		


if __name__ == '__main__':
    SketchSwapper().show()
    gtk.main()

    #print rectArea(boundingBox(((3, 2), (2, 3), (1, 1))))


