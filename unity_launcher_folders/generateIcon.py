#!/usr/bin/python
### BEGIN LICENSE
# Copyright (C) 2014 Anton Sukhovatkin <laucnherfolders@exceptionfound.com>
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE
from gi.repository import Gdk, GdkPixbuf
import Image
import os

CONFIG_DIR = os.getenv('HOME') + "/.appDrawerConfig/"

MINI_ICON_WIDTH = 18
MINI_ICON_HEIGHT = 18

ICON_WIDTH = 64
ICON_HEIGHT = 64

#Image does not open *.svg and *.xpm files
#PixBuf can read xpm, try converting that way
#SVG !fixed! by converting to a tmp png file
class GenerateIcon:
	def __init__(self, iconFileNameList, drawerName):

		if os.path.isfile(CONFIG_DIR + drawerName + ".png"):
			os.remove(CONFIG_DIR + drawerName + ".png")

		self.drawerName = drawerName
		blankImage = Image.new("RGBA", (ICON_WIDTH, ICON_HEIGHT))
		mini_icons_list = []
		tmp_png_icons = []

		for iconFileName in iconFileNameList:
			fileName, fileExtension = os.path.splitext(iconFileName)
			if fileExtension == ".svg":
				base=os.path.basename(iconFileName)
				convertedPngFileName = os.path.splitext(base)[0]

				self.convertSvgToPng(iconFileName, convertedPngFileName + ".png")
				iconFileName = CONFIG_DIR + convertedPngFileName + ".png"
				tmp_png_icons.append(iconFileName)
			elif fileExtension == ".xpm":
				base=os.path.basename(iconFileName)
				convertedPngFileName = os.path.splitext(base)[0]
				self.convertXpmToPng(iconFileName, convertedPngFileName + ".png")
				iconFileName = CONFIG_DIR + convertedPngFileName + ".png"
				tmp_png_icons.append(iconFileName)

			icon = Image.open(open(iconFileName, 'rb'))
			self.setThumbnail(icon)
			mini_icons_list.append(icon)

		self.addRows(blankImage, mini_icons_list)
		
		blankImage.save(CONFIG_DIR + drawerName + ".png", "PNG")
		for item in tmp_png_icons:
			if os.path.isfile(item):
				os.remove(item)


	def addRows(self, image, mini_icons_list):
		x = 2
		y = 2
		for item in mini_icons_list[0:3]:
			image.paste(item, (x, y))
			x += 20
		x = 2
		y = 22
		for item in mini_icons_list[3:6]:
			image.paste(item, (x, y))
			x += 20
		x = 2
		y = 42
		for item in mini_icons_list[6:9]:
			image.paste(item, (x, y))
			x += 20

	def setThumbnail(self, image):
		image.thumbnail((MINI_ICON_WIDTH, MINI_ICON_HEIGHT))

	def getIconFileName(self):
		return CONFIG_DIR + self.drawerName + ".png"

	def convertSvgToPng(self, svgImage, pngImageName):
		#outputImg = cairo.ImageSurface(cairo.FORMAT_ARGB32, 48, 48)
		#ctx = cairo.Context(outputImg)
		#handler = Rsvg.Handle.new_from_file(svgImage)
		#handler.render_cairo(ctx)
		#outputImg.write_to_png(CONFIG_DIR + pngImageName)

		pixbuf = GdkPixbuf.Pixbuf.new_from_file(svgImage)
		pixbuf = pixbuf.scale_simple(48, 48, GdkPixbuf.InterpType.BILINEAR)

		pixbuf.savev(CONFIG_DIR + pngImageName, "png", [], [])

	def convertXpmToPng(self, xpmImage, pngImageName):
		pixbuf = GdkPixbuf.Pixbuf.new_from_file(xpmImage)
		pixbuf = pixbuf.scale_simple(48, 48, GdkPixbuf.InterpType.BILINEAR)

		pixbuf.savev(CONFIG_DIR + pngImageName, "png", [], [])
