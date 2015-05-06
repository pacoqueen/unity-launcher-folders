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
import os, sys, subprocess, pickle, re, cairo
from unity_launcher_folders_lib.helpers import get_data_file
from unity_launcher_folders.generateIcon import GenerateIcon
import unity_launcher_folders.util as util

LOCAL_APP_DIR = os.getenv('HOME') + "/.local/share/applications/"
CONFIG_DIR = os.getenv('HOME') + "/.appDrawerConfig/"
CURR_WORK_DIR = os.path.abspath(os.path.dirname(__file__))

(COLUMN_TEXT, COLUMN_PIXBUF) = range(2)

#right now iconsize is still openeded as an argument, NOT from config file
class MainWindow(Gtk.Window):
	def __init__(self, configFile):
		Gtk.Window.__init__(self, title="")
		self.configList = self.unpickleSettings(configFile)
		self.drawerType = self.configList['drawerType'][0]
		self.numColumns = 0
		if self.drawerType == "Box":
			self.numColumns = self.configList['drawerType'][1]

		self.setWindowSettings(self.configList)

		self.screen = self.get_screen()
		self.visual = self.screen.get_rgba_visual()
		if self.visual != None and self.screen.is_composited():
			self.set_visual(self.visual)

		self.connect("focus-out-event", self.onFocusOut)
		self.set_app_paintable(True)
		self.connect("draw", self.area_draw)

		iconScrollView = ScrolledWindowIconView(self, self.configList, self.configList['iconSize'], self.numColumns)
		
		hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
		hbox.pack_start(iconScrollView, True, True, 0)
		self.add(hbox)

	def setWindowSettings(self, settingsList):
		itemWidth = settingsList['itemWidth'] 
		if self.drawerType == "Horizontal" or self.drawerType == "Box":
			winWidth = 200
			winHeight = int(settingsList['iconSize']) * 2
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

	def unpickleSettings(self, fileName):
		return pickle.load(open(fileName, "rb"))

	#Quit app drawer if clicked outside of the window
	def onFocusOut(self, widget, event):
		print ""
		Gtk.main_quit()

	def area_draw(self, widget, cr):
		cr.set_source_rgba(.2, .2, .2, 0)
		cr.set_operator(cairo.OPERATOR_SOURCE)
		cr.paint()
		cr.set_operator(cairo.OPERATOR_OVER)

class ScrolledWindowIconView(Gtk.ScrolledWindow):
	def __init__(self, parent, configList, iconSize, numberColumns):
		Gtk.ScrolledWindow.__init__(self)
		itemWidth = configList['itemWidth']
		#self.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.NEVER)

		ourIconView = ShortcutsView(parent, configList, iconSize, numberColumns)
		#TODO: make sure 'content_width' is NOT bigger the screen width
		if parent.drawerType == "Horizontal" or parent.drawerType == "Box":
			self.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.NEVER)
			content_width = (itemWidth * ourIconView.get_columns() * 2) + 40
			content_height = iconSize * 2
		elif parent.drawerType == "Vertical":
			self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
			content_width = itemWidth * 1.5
			content_height = itemWidth * len(configList['appList']) * 1.5

		#content_width = (int(configList[0][5]) * ourIconView.get_columns() * 2) + 40
		
		self.set_min_content_width(content_width)
		self.set_min_content_height(content_height)
		self.add(ourIconView)

class ShortcutsView(Gtk.IconView):
	def __init__(self, parent, configList, iconSize, numberColumns):

		Gtk.IconView.__init__(self)
		self.launchDict = {}

		#fontO = Pango.FontDescription("Ubuntu " + str(configList[0][4]))
		fontO = Pango.FontDescription("Ubuntu " + str(configList['fontSize']))
		self.modify_font(fontO)

		self.set_item_padding(0)
		#if item width is the same as icon size, text cuts of at smaller icon sizes
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
			self.model.set_value(row, COLUMN_PIXBUF, self.getPixBuffFromFile(item[1], iconSize))
			numColumns += 1
			self.launchDict[item[0]] = item[2]

		if parent.drawerType == "Horizontal":
			pass
		elif parent.drawerType == "Vertical":
			numColumns = 1
		elif parent.drawerType == "Box":
			numColumns = numberColumns

		self.set_columns(numColumns)
		self.set_text_column(COLUMN_TEXT)
		self.set_pixbuf_column(COLUMN_PIXBUF)
		

	def getPixBuffFromFile(self, fileName, iconSize):
		newFileName = ""
		if os.path.isfile(fileName):
			newFileName = fileName	
		else:
			newFileName = self.lookupIcon(fileName, iconSize)

		pixbuf = GdkPixbuf.Pixbuf.new_from_file(newFileName)
		pixbuf = pixbuf.scale_simple(iconSize, iconSize, GdkPixbuf.InterpType.BILINEAR)
		
		return pixbuf

	def lookupIcon(self, iconName, iconSize):
		icon_theme = Gtk.IconTheme.get_default()
		icon = icon_theme.lookup_icon(iconName, iconSize, 0)
		if icon:
			return icon.get_filename()

	def on_item_activated(self, widget, item):
		model = widget.get_model()
		appTitle = model[item][COLUMN_TEXT]
		if "file://" in self.launchDict[appTitle]:
			self.launchFile(self.launchDict[appTitle])
			#self.unselect_all()
			Gtk.main_quit()
		else:
			bashCommand = self.launchDict[appTitle]
			subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
			#self.unselect_all()
			self.owner.destroy()
		self.unselect_all()
		Gtk.main_quit()

	def launchFile(self, uri):
		gio_file = Gio.File.new_for_uri(uri)
		handler = gio_file.query_default_handler(None)
		handler.launch([gio_file], None)

	def unpickleSettings(self, fileName):
		return pickle.load(open(fileName, "rb"))

class AddNewItemAndReconfigure:
	def __init__(self, configFileName, droppedItemFileName):
		self.configList = util.unpickleSettings(configFileName)
		fileName, fileExtension = os.path.splitext(droppedItemFileName)
		if fileExtension == ".sh":
			execPath = "gnome-terminal -x " + fileName + fileExtension
			fileName, fileIcon = util.getUriIconForFile(droppedItemFileName)
			self.configList['appList'].append([fileName, fileIcon, execPath])
			self.genIcon(configFileName)

		else:
			execPath = "file://" + fileName + fileExtension
			fileName, fileIcon = util.getUriIconForFile(droppedItemFileName)
			self.configList['appList'].append([fileName, fileIcon, execPath])
			self.genIcon(configFileName)

			
	def genIcon(self, configFileName):
		if os.path.isfile(CONFIG_DIR + self.configList['drawerName'] + ".png"):
			iconFileNamesList = []
			for item in self.configList['appList']:
				iconFileNamesList.append(item[1])
			generateIcon = GenerateIcon(iconFileNamesList, self.configList['drawerName'])
			self.configList['drawerIcon'] = generateIcon.getIconFileName()
		self.writeDekstopFileDrawer(self.configList['appList'], self.configList['drawerName'], self.configList['drawerIcon'], self.configList['iconSize'], self.configList['drawerType'])
		util.pickleDrawerSettings(self.configList, configFileName)
		subprocess.call([get_data_file('deleteAddIconLauncher.sh'), str(self.configList['drawerName'])])

	def writeDekstopFileDrawer(self, settingsList, drawerName, drawerIconFileName, iconSize, drawerType):
		filename = LOCAL_APP_DIR + drawerName + ".desktop"
		f = open(filename, 'w')
		f.write("[Desktop Entry]\n")
		f.write("Name=" + drawerName + "\n")
		f.write("Exec=" + get_data_file("drawer.py") + " " + CONFIG_DIR + drawerName + ".pickle %f" + "\n")
		f.write("MimeType=application/octet-stream\n")
		f.write("Terminal=false\n")
		f.write("Type=Application\n")
		f.write("Icon=" + drawerIconFileName + "\n")

		f.write("Actions=")
		for item in settingsList:
			f.write(item[0] + ";")
			#print "App Name: " + item[0]
		f.write("Edit Drawer;")
		f.write("\n")
		for item in settingsList:
			f.write("[Desktop Action " + item[0] + "]\n")
			f.write("Name=" + item[0] + "\n")
			fileRegEx = re.search('file://', item[2])
			if fileRegEx:
				gio_file = Gio.File.new_for_uri(item[2])
				handler = gio_file.query_default_handler(None)
				line = re.sub('file://', '', item[2])
				rightClickExecPath = handler.get_executable() + " " + line
			else:
				rightClickExecPath = item[2]
			f.write("Exec=" + rightClickExecPath + "\n")
			f.write("OnlyShowIn=Unity;\n")
		f.write("[Desktop Action Edit Drawer]\n")
		f.write("Name=Edit Drawer\n")
		f.write("Exec=/usr/bin/unity-launcher-folders " + drawerName + "\n")
		f.write("Path=" + CURR_WORK_DIR + "/\n")
		f.write("OnlyShowIn=Unity;\n")
		f.close()
		os.chmod(filename, 0755)

if __name__ == "__main__":

	if len(sys.argv) == 2:
		configFileName = sys.argv[1]
		win = MainWindow(configFileName)
		win.connect("delete-event", Gtk.main_quit)
		win.show_all()
		Gtk.main()
	elif len(sys.argv) == 3:
		configFileName = sys.argv[1]
		droppedItemFileName = sys.argv[2]
		doIt = AddNewItemAndReconfigure(configFileName, droppedItemFileName)
