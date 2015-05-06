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
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, Gio
from unity_launcher_folders_lib.helpers import get_data_file
import os, subprocess
import util

CURR_WORK_DIR = os.getcwd()
(COLUMN_TEXT, COLUMN_PIXBUF) = range(2)

class DrawerPreview(Gtk.Window):
	def __init__(self, settingsList, drawerType, numColumns):
		Gtk.Window.__init__(self, title="Drawer Preview")
		self.drawerType = drawerType
		self.setWindowSettings(settingsList)
		self.connect("focus-out-event", self.onFocusOut)

		#iconScrollView = ScrolledWindowIconView(self, settingsList, settingsList[0][3], numColumns)
		iconScrollView = ScrolledWindowIconView(self, settingsList, settingsList['iconSize'], numColumns)

		hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
		hbox.pack_start(iconScrollView, True, True, 0)
		self.add(hbox)

		self.show_all()

	def setWindowSettings(self, settingsList):
		#itemWidth = settingsList[0][5]
		itemWidth = settingsList['itemWidth']
		if self.drawerType == "Horizontal" or self.drawerType == "Box":
			winWidth = 200
			winHeight = settingsList['iconSize'] * 2
			#winHeight = settingsList[0][3] * 2
		elif self.drawerType == "Vertical":
			winWidth = itemWidth * 1.5
			winHeight = itemWidth * len(settingsList['appList'])
		self.set_default_size(winWidth, winHeight)
		self.set_position(Gtk.WindowPosition.MOUSE)
		self.props.can_focus = True

		self.set_decorated(False)
		self.set_opacity(0.9)

		screen = Gdk.Screen.get_default()
		css_provider = Gtk.CssProvider()
		css_provider.load_from_path(get_data_file("themed.css"))

		context = Gtk.StyleContext()
		context.add_provider_for_screen(screen, css_provider,
                                Gtk.STYLE_PROVIDER_PRIORITY_USER)

	def onFocusOut(self, widget, event):
		self.destroy()

class ScrolledWindowIconView(Gtk.ScrolledWindow):
	def __init__(self, parent, configList, iconSize, numColumns):
		Gtk.ScrolledWindow.__init__(self)

		#itemWidth = configList[0][5]
		itemWidth = configList['itemWidth']
		ourIconView = ShortcutsView(parent, configList, iconSize, numColumns)
		#TODO: make sure 'content_width' is NOT bigger the screen width
		if parent.drawerType == "Horizontal" or parent.drawerType == "Box":
			self.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.NEVER)
			content_width = (itemWidth * ourIconView.get_columns() * 2) + 40
			content_height = iconSize * 2
		elif parent.drawerType == "Vertical":
			self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
			content_width = itemWidth * 1.5
			content_height = itemWidth * len(configList['appList']) * 1.5
		
		
		self.set_min_content_width(content_width)
		self.set_min_content_height(content_height)
		self.add(ourIconView)

class ShortcutsView(Gtk.IconView):
	def __init__(self, parent, configList, iconSize, numberColumns):
		Gtk.IconView.__init__(self)

		self.launchDict = {}
		self.owner = parent

		#fontO = Pango.FontDescription("Ubuntu " + str(configList[0][4]))
		fontO = Pango.FontDescription("Ubuntu " + str(configList['fontSize']))
		self.modify_font(fontO)

		self.set_item_padding(0)
		#if item width is the same as icon size, text cuts of at smaller icon sizes
		#self.set_item_width(configList[0][5])
		self.set_item_width(configList['itemWidth'])
		self.set_column_spacing(0)
		self.props.activate_on_single_click = True

		self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
		self.connect("item-activated", self.on_item_activated)

		self.model = Gtk.ListStore(str, GdkPixbuf.Pixbuf)
		self.set_model(self.model)

		numColumns = 0
		for item in configList['appList']:
			row = self.model.append()
			self.model.set_value(row, COLUMN_TEXT, item[0])
			self.model.set_value(row, COLUMN_PIXBUF, util.getPixBuffFromFile(item[1], iconSize))
			numColumns += 1
			self.launchDict[item[0]] = item[2]

		#box with #columns has all Horizontal settings
		#just specify the num columns
		if parent.drawerType == "Horizontal":
			pass
		elif parent.drawerType == "Vertical":
			numColumns = 1
		elif parent.drawerType == "Box":
			numColumns = numberColumns
		self.set_columns(numColumns)
		self.set_text_column(COLUMN_TEXT)
		self.set_pixbuf_column(COLUMN_PIXBUF)

	def on_item_activated(self, widget, item):
		model = widget.get_model()
		appTitle = model[item][COLUMN_TEXT]

		if "file://" in self.launchDict[appTitle]:
			self.launchFile(self.launchDict[appTitle])
			self.unselect_all()
			self.owner.destroy()
		else:
			bashCommand = self.launchDict[appTitle]
			subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
			self.unselect_all()
			self.owner.destroy()

	def launchFile(self, uri):
		gio_file = Gio.File.new_for_uri(uri)
		handler = gio_file.query_default_handler(None)
		handler.launch([gio_file], None)

