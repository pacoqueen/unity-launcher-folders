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
import csv, os, re, pickle
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio
#when the file is dropped a string in the format Google%20Maps is returned
# %20 represents a 'space' character
def checkForSpaceInFileAndReplace(fileName):
	if "%20" in fileName:
		return fileName.replace("%20", " ")	
	else:
		return fileName

#The actual name of the file and the app name defined in the .desktop file
#can be different. Also .desktop file can contain multiple "Name" keys
#so we grab the first one we find
#NO LONGER USED, replaced with getAppInfo method
def getAppNameFromFile(fileName):
		tmpArr = []
		for row in csv.reader(open(fileName, "r"), delimiter="=" ):
			if len(row) > 1:
				if row[0] == "Name":
					tmpArr.append(row[1])
		return tmpArr[0]

#GET app info from .desktop file
#just read the file and extract 'appName', 'icon', 'execPath'
#NO LONGER USED IN: createDrawer.py
def getAppNameAndIcon(fileName):
		newFileName = ""
		ins = open(fileName, "r")
		appName = getAppNameFromFile(fileName)
		icon = ""
		execPath = ""
		for line in ins:
			if "Icon=" in line:
				line = line.replace("Icon=", "")
				line = line.rstrip()
				icon = line
			elif "Exec=" in line:
				line = line.replace("Exec=", "")
				line = line.rstrip()
				execPath = line
		ins.close()

		#Google Maps created an exec path with " character
		#did not execute
		if "\"" in execPath:
			execPath = execPath.replace("\"", "")

		return appName, icon, execPath

#execPath can contain an argument we remove it with regex
def getAppInfo(fileName):
	execArr = []
	nameArr = []
	iconArr = []
	for row in csv.reader(open(fileName, "r"), delimiter="="):
		if len(row) > 1:
			if row[0] == "Exec":
				if len(row) > 2:
					line = "=".join(row)
					line = line.replace("Exec=", "")
					execArr.append(line)
				else:
					execArr.append(row[1])
			elif row[0] == "Name":
				nameArr.append(row[1])
			elif row[0] == "Icon":
				iconArr.append(row[1])
	
	appName = nameArr[0]
	icon = iconArr[0]
	execPath = execArr[0]

	if "\"" in execPath:
		execPath = execPath.replace("\"", "")
	execPath = re.sub(r'\%[^0-9]{1}', "", execPath).rstrip()
	return appName, icon, execPath

def getConfigFromFile(fileName):
	configList = csv.reader(open(fileName, "r"))
	return configList

def unpickleSettings(fileName):
		return pickle.load(open(fileName, "rb"))

def pickleDrawerSettings(settingsList, pickleFile):
		with open(pickleFile, 'wb') as f:
			pickle.dump(settingsList, f)

def getDrawerIconFromPickle(fileName):
	f = open(fileName, "rb")
	settings = pickle.load(f)
	f.close()
	return settings['drawerIcon']

def getDrawerIconPixbuf(iconName):
	pixbuf = GdkPixbuf.Pixbuf.new_from_file(iconName)
	pixbuf = pixbuf.scale_simple(48, 48, GdkPixbuf.InterpType.BILINEAR)
	return pixbuf

def deleteDrawerFiles(localAppDir, configAppDir, selectedValue):
	drawerDesktopFile = localAppDir + selectedValue + ".desktop"
	drawerPngIconFile = configAppDir + selectedValue + ".png"

	if os.path.isfile(drawerDesktopFile):
		os.remove(drawerDesktopFile)		
	if os.path.isfile(drawerPngIconFile):
		os.remove(drawerPngIconFile)
	os.remove(configAppDir + selectedValue + ".pickle")

def lookupIcon(iconName):
	icon_theme = Gtk.IconTheme.get_default()
	icon = icon_theme.lookup_icon(iconName, 64, 0)
	if icon:
		return icon.get_filename()

def getUriIconForFile(fileName):
	gio_file = Gio.File.new_for_path(fileName)
	file_info = gio_file.query_info('standard::icon', Gio.FileQueryInfoFlags.NONE, None)
	uri_icon = file_info.get_icon().get_names()[0]

	fileName = gio_file.get_basename()
	fileIcon = lookupIcon(uri_icon)

	return fileName, fileIcon

def getPixBuffFromFile(fileName, iconSize):
		newFileName = ""
		if os.path.isfile(fileName):
			newFileName = fileName	
		else:
			newFileName = lookupIcon(fileName)

		pixbuf = GdkPixbuf.Pixbuf.new_from_file(newFileName)
		pixbuf = pixbuf.scale_simple(iconSize, iconSize, GdkPixbuf.InterpType.BILINEAR)

		return pixbuf

def getIconPathFromFileName(fileName):
	newFileName = ""
	if os.path.isfile(fileName):
		newFileName = fileName	
	else:
		newFileName = lookupIcon(fileName)
	return newFileName

def drop_get_uris(selection):
	uris = []
	if selection.targets_include_uri():
		data = selection.get_data()
		lines = re.split('\\s*[\\n\\r]+\\s*', data.strip())

	for line in lines:
		if not line.startswith('#'):
			uris.append(line)
			
	return uris