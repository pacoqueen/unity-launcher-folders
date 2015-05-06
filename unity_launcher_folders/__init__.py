# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
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

import optparse

from locale import gettext as _

from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, Gio
from tabLabel import TabLabel
from generateIcon import GenerateIcon
from drawerPreview import DrawerPreview
import os, sys, re
import subprocess
import csv, pickle
import util
from unity_launcher_folders_lib.helpers import get_data_file
from unity_launcher_folders_lib import magic

# pylint: disable=E0611

# from unity_launcher_folders import UnityLauncherFoldersWindow

# from unity_launcher_folders_lib import set_up_logging, get_version

def parse_options():
    """Support for command line options"""
    parser = optparse.OptionParser(version="%%prog %s" % get_version())
    parser.add_option(
        "-v", "--verbose", action="count", dest="verbose",
        help=_("Show debug messages (-vv debugs unity_launcher_folders_lib also)"))
    (options, args) = parser.parse_args()

    set_up_logging(options)

(URI_LIST_MIME_TYPE, TEXT_LIST_MIME_TYPE) = range(2)
(COLUMN_TEXT, COLUMN_PIXBUF) = range(2)


DELETE_DRAWER = 1
DRAG_ACTION = Gdk.DragAction.COPY

LOCAL_APP_DIR = os.getenv('HOME') + "/.local/share/applications/"
SYSTEM_APP_DIR = "/usr/share/applications/"
CONFIG_DIR = os.getenv('HOME') + "/.appDrawerConfig/"
CURR_WORK_DIR = os.path.abspath(os.path.dirname(__file__))

UI_INFO = """
<ui>
  <popup name='PopupMenu'>
    <menuitem action='Properties' />
    <separator />
    <menuitem action='DeleteItem' />
  </popup>
</ui>
"""

class MainWindow(Gtk.Window):
    def __init__(self, editDrawer):
        Gtk.Window.__init__(self, title="LauncherFolders Editor")
        if not os.path.isdir(os.getenv('HOME') + "/.appDrawerConfig"):
            path = os.getenv('HOME') + "/.appDrawerConfig"
            os.mkdir( path, 0755 );
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_decorated(True)
        self.set_opacity(0.9)

        screen = Gdk.Screen.get_default()

        print get_data_file('deleteAddIconLauncher.sh')

        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(get_data_file("themed.css"))

        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, css_provider,
                                Gtk.STYLE_PROVIDER_PRIORITY_USER)

        self.toolbar = self.createToolbar()

        self.notebook = Tabs()
        if editDrawer != None:
            drawerFile = LOCAL_APP_DIR + editDrawer + ".desktop"
            drawerName, drawerIcon, execPath = util.getAppInfo(drawerFile)
            self.notebook.createPage(drawerName, drawerIcon, False)

        hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        hbox.pack_start(self.toolbar, False, True, 0)
        hbox.pack_end(self.notebook, True, True, 0)

        self.add(hbox)

    def createToolbar(self):
        toolbar = Gtk.Toolbar.new()
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)

        newDrawerBtn = Gtk.ToolButton.new()
        newDrawerBtn.set_icon_name("document-new")
        newDrawerBtn.set_tooltip_text("New Drawer")
        newDrawerBtn.connect("clicked", self.newDrawerClicked)

        openDrawerBtn = Gtk.ToolButton.new()
        openDrawerBtn.set_icon_name("document-open")
        openDrawerBtn.set_tooltip_text("Open Drawer")
        openDrawerBtn.connect("clicked", self.openDrawerClicked)

        saveDrawerBtn = Gtk.ToolButton.new()
        saveDrawerBtn.set_icon_name("document-save")
        saveDrawerBtn.set_tooltip_text("Save Drawer and add to launcher")
        saveDrawerBtn.connect("clicked", self.saveDrawerClicked)

        drawerPreferencesBtn = Gtk.ToolButton.new()
        drawerPreferencesBtn.set_icon_name("gtk-preferences")
        drawerPreferencesBtn.set_tooltip_text("Drawer Settings")
        drawerPreferencesBtn.connect("clicked", self.drawerPreferencesClicked)

        drawerPreviewBtn = Gtk.ToolButton.new()
        drawerPreviewBtn.set_icon_name("media-playback-start")
        drawerPreviewBtn.set_tooltip_text("Preview Drawer")
        drawerPreviewBtn.connect("clicked", self.drawerPreviewClicked)

        toolbar.insert(newDrawerBtn, -1)
        toolbar.insert(openDrawerBtn, -1)
        toolbar.insert(saveDrawerBtn, -1)
        toolbar.insert(Gtk.SeparatorToolItem.new(), -1)
        toolbar.insert(drawerPreferencesBtn, -1)
        toolbar.insert(drawerPreviewBtn, -1)

        return toolbar

    def newDrawerClicked(self, widget):
        #Gtk-WARNING **: Can't set a parent on widget which has a parent
        #FIXED by adding self.show_all()
        newDrawerDialog = NewDrawerDialog(self)
        newDrawerDialog.connect('key-press-event', self.on_newDialog_key_press)
        response = newDrawerDialog.run()

        if response == Gtk.ResponseType.OK:
            drawerName = newDrawerDialog.drawerName.get_text()
            drawerIcon = newDrawerDialog.drawerIconFileName

            if not drawerName:
                print "Enter Drawer Name"
            else:
                self.notebook.createPage(drawerName, drawerIcon, True)
        elif response == Gtk.ResponseType.CANCEL:
            print "cancel clicked"
        newDrawerDialog.destroy()

    def on_newDialog_key_press(self, dialog, event):
        if event.keyval == Gdk.KEY_Return:
            dialog.response(Gtk.ResponseType.OK)
            return True
        if event.keyval == Gdk.KEY_Escape:
            dialog.response(Gtk.ResponseType.CANCEL)
            return True
        return False

    def openDrawerClicked(self, widget):
        openDrawerDialog = OpenDrawerDialog(self)
        openDrawerDialog.connect("response", self.openDrawerResponse)

    def openDrawerResponse(self, dialog, response_id):
        if response_id == DELETE_DRAWER:
            warningDialog = WarningDeleteDrawerDialog(self, dialog.selectedValue)
            response_id = warningDialog.run()

            if response_id == Gtk.ResponseType.OK:
                util.deleteDrawerFiles(LOCAL_APP_DIR, CONFIG_DIR, dialog.selectedValue)
                dialog.model.remove(dialog.tree_iter)
            warningDialog.destroy()
            
        elif response_id == Gtk.ResponseType.OK:
            configFile = CONFIG_DIR + dialog.selectedValue
            drawerFile = LOCAL_APP_DIR + dialog.selectedValue + ".desktop"

            drawerName, drawerIcon, execPath = util.getAppInfo(drawerFile)
            self.notebook.createPage(drawerName, drawerIcon, False)

            dialog.destroy()
        elif response_id == Gtk.ResponseType.CANCEL:
            dialog.destroy()

    def saveDrawerClicked(self, widget):
        currentPage = self.notebook.get_current_page()
        if currentPage == -1:
            pass
        else:
            ourScrolledWindow = self.notebook.get_nth_page(currentPage)
            ourIconView = ourScrolledWindow.getIconView()
            iconSize = ourIconView.iconSize
            if len(ourIconView.drawerSettings['appList']) > 0:
                #This list is needed to generate a drawer icon
                iconFileNamesList = []

                for item in ourIconView.drawerSettings['appList']:
                    iconFileNamesList.append(item[1])

                if ourScrolledWindow.isNewFile:
                    #If the icon for the drawer was not selected we generate it
                    if not ourScrolledWindow.drawerIconFileName:
                        generateIcon = GenerateIcon(iconFileNamesList, ourScrolledWindow.drawerName)
                        ourIconView.drawerSettings['drawerIcon'] = generateIcon.getIconFileName()
                        self.writeDekstopFileDrawer(ourIconView.drawerSettings['appList'], ourScrolledWindow.drawerName, generateIcon.getIconFileName(), iconSize, ourIconView.drawerType)
                    else:
                        self.writeDekstopFileDrawer(ourIconView.drawerSettings['appList'], ourScrolledWindow.drawerName, ourScrolledWindow.drawerIconFileName, iconSize, ourIconView.drawerType)
                        ourIconView.drawerSettings['drawerIcon'] = ourScrolledWindow.drawerIconFileName
                    subprocess.call([get_data_file('deleteAddIconLauncher.sh'), str(ourScrolledWindow.drawerName)])
                else:
                    if os.path.isfile(CONFIG_DIR + ourScrolledWindow.drawerName + ".png"):
                        generateIcon = GenerateIcon(iconFileNamesList, ourScrolledWindow.drawerName)
                        ourIconView.drawerSettings['drawerIcon'] = generateIcon.getIconFileName()
                        self.writeDekstopFileDrawer(ourIconView.drawerSettings['appList'], ourScrolledWindow.drawerName, generateIcon.getIconFileName(), iconSize, ourIconView.drawerType)
                    else:
                        self.writeDekstopFileDrawer(ourIconView.drawerSettings['appList'], ourScrolledWindow.drawerName, ourScrolledWindow.drawerIconFileName, iconSize, ourIconView.drawerType)
                        ourIconView.drawerSettings['drawerIcon'] = ourScrolledWindow.drawerIconFileName
                    subprocess.call([get_data_file('deleteAddIconLauncher.sh'), str(ourScrolledWindow.drawerName)])
                self.pickleDrawerSettings(ourIconView.drawerSettings, ourScrolledWindow.drawerName)
                self.writeChromeWebApp(ourIconView.drawerSettings)
                pass
            else:
                pass

    def drawerPreferencesClicked(self, widget):
        currentPage = self.notebook.get_current_page()
        if currentPage == -1:
            pass
        else:
            ourScrolledWindow = self.notebook.get_nth_page(currentPage)
            ourIconView = ourScrolledWindow.getIconView()
            preferencesDialog = PreferencesDrawerDialog(self, ourIconView.iconSize, ourIconView.fontSize, ourIconView.itemWidth)
            preferencesDialog.connect("response", self.drawerPreferencesResonse)

    def drawerPreferencesResonse(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            currentPage = self.notebook.get_current_page()
            ourScrolledWindow = self.notebook.get_nth_page(currentPage)
            ourIconView = ourScrolledWindow.getIconView()

            iconSize = dialog.iconSize.get_value()
            fontSize = dialog.fontSize.get_value()
            itemWidth = dialog.itemWidth.get_value()
            drawerType = dialog.drawerTypeName
            intIconSize = int(float(iconSize))

            ourIconView.fontSize = int(float(fontSize))
            ourIconView.itemWidth = int(float(itemWidth))
            ourIconView.drawerType = drawerType
            ourIconView.numColumns = int(float(dialog.numColumns.get_value()))
            ourIconView.set_font()

            self.reloadIcons(ourIconView, intIconSize)
            if ourIconView.drawerType == "Box":
                ourIconView.drawerSettings['drawerType'] = [ourIconView.drawerType, ourIconView.numColumns]
            else:
                ourIconView.drawerSettings['drawerType'] = [ourIconView.drawerType]
            print ourIconView.drawerSettings
            ourIconView.set_item_width(ourIconView.itemWidth)
            
            dialog.destroy()
        elif response_id == Gtk.ResponseType.CANCEL:
            dialog.destroy()

    def reloadIcons(self, ourIconView, iconSize):
        ourIconView.model.clear()
        ourIconView.drawerSettings['iconSize'] = iconSize
        ourIconView.drawerSettings['fontSize'] = ourIconView.fontSize
        ourIconView.drawerSettings['itemWidth'] = ourIconView.itemWidth

        for item in ourIconView.drawerSettings['appList']:
            row = ourIconView.model.append()
            appName = item[0]
            appIcon = item[1]
            ourIconView.model.set_value(row, COLUMN_TEXT, appName)
            ourIconView.model.set_value(row, COLUMN_PIXBUF, util.getPixBuffFromFile(appIcon, iconSize))

            ourIconView.iconSize = iconSize
        
    def drawerPreviewClicked(self, widget):
        currentPage = self.notebook.get_current_page()
        if currentPage == -1:
            pass
        else:
            ourScrolledWindow = self.notebook.get_nth_page(currentPage)
            ourIconView = ourScrolledWindow.getIconView()
            preview_win = DrawerPreview(ourIconView.drawerSettings, ourIconView.drawerType, ourIconView.numColumns)
            self.writeChromeWebApp(ourIconView.drawerSettings)

    def pickleDrawerSettings(self, settingsList, drawerName):
        with open(CONFIG_DIR + drawerName + ".pickle", 'wb') as f:
            pickle.dump(settingsList, f)

    def writeDekstopFileDrawer(self, settingsList, drawerName, drawerIconFileName, iconSize, drawerType):
        filename = LOCAL_APP_DIR + drawerName + ".desktop"
        f = open(filename, 'w')
        f.write("[Desktop Entry]\n")
        f.write("Name=" + drawerName + "\n")
        f.write("Exec=" + get_data_file("drawer.py") + " \"" + CONFIG_DIR + drawerName + ".pickle\" %f" + "\n")
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
        f.write("Exec=/usr/bin/unity-launcher-folders " + "\"" + drawerName + "\"" + "\n")
        f.write("Path=" + CURR_WORK_DIR + "/\n")
        f.write("OnlyShowIn=Unity;\n")
        f.close()
        os.chmod(filename, 0755)

    def writeChromeWebApp(self, settingsList):
        appList = settingsList['appList']
        for app in appList:
            execPath = app[2]
            chromeWebAppRegex = re.search('/opt/google/chrome/google-chrome --app=', execPath)
            fileRegEx = re.search('file://', execPath)
            if chromeWebAppRegex:
                chromeAppName = app[0]
                chromeAppIcon = app[1]

                cleanUrl = re.sub('/opt/google/chrome/google-chrome --app=', '', execPath)
                cleanUrl = re.sub(r'http[s]?://', '', cleanUrl)
                cleanUrl = re.sub(r'\/$', '', cleanUrl)
                startupWmClassUrl = re.sub('/', '__', cleanUrl, count=1)
                startupWmClassUrl = re.sub('/', '_', startupWmClassUrl)
                s = re.search(r'[\?!#<>:\\|](.*)', startupWmClassUrl)
                if s:
                    startupWmClassUrl = re.sub(r'[\?#!](.*)', '', startupWmClassUrl)
                    startupWmClassUrl = startupWmClassUrl.rstrip("__")
                else:
                    pass
                
                if os.path.isfile(LOCAL_APP_DIR + chromeAppName + ".desktop"):
                    pass
                else:
                    filename = LOCAL_APP_DIR + chromeAppName + ".desktop"
                    f = open(filename, 'w')
                    f.write("#!/usr/bin/env xdg-open\n")
                    f.write("[Desktop Entry]\n")
                    f.write("Version=1.0\n")
                    f.write("Terminal=false\n")
                    f.write("Type=Application\n")
                    f.write("Name=" + chromeAppName + "\n")
                    f.write("Exec=" + execPath + "\n")
                    f.write("Icon=" + chromeAppIcon + "\n")
                    f.write("StartupWMClass=" + startupWmClassUrl + "\n")
                    f.close()
                    os.chmod(filename, 0755)

class Tabs(Gtk.Notebook):
    def __init__(self):
        Gtk.Notebook.__init__(self)
        self.targets = Gtk.TargetList.new([])
        self.targets.add_uri_targets(URI_LIST_MIME_TYPE)
        self.targets.add_text_targets(TEXT_LIST_MIME_TYPE)

    def createPage(self, drawerLabel, drawerIconFileName, isNewFile):
        scrolled_window = self.createContent(drawerLabel, drawerIconFileName, isNewFile)

        tab_label = TabLabel(drawerLabel, drawerIconFileName)

        tab_label.connect("close-clicked", self.on_close_clicked, self, scrolled_window)

        self.append_page(scrolled_window, tab_label)
        self.show_all()

    def on_close_clicked(self, tab_label, notebook, tab_widget):
        self.remove_page(notebook.page_num(tab_widget))

    def createContent(self, drawerLabel, drawerIconFileName, isNewFile):
        return ScrolledWindowIconView(self.targets, drawerLabel, drawerIconFileName, isNewFile)

class WarningDeleteDrawerDialog(Gtk.MessageDialog):
    def __init__(self, parent, drawerName):
        Gtk.MessageDialog.__init__(self, parent, 0, Gtk.MessageType.WARNING,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK),
            "This will delete the " + drawerName + " drawer and all of its contents!")
        self.show_all()

class PreferencesDrawerDialog(Gtk.Dialog):
    def __init__(self, parent, iconSize, fontSize, itemWidth):
        Gtk.Dialog.__init__(self, "Drawer Preferences", parent, 0, 
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_APPLY, Gtk.ResponseType.OK))
        self.set_modal(True)
        self.set_default_size(300, 400)
        self.drawerTypeName = "Horizontal"

        currentPage = parent.notebook.get_current_page()
        ourScrolledWindow = parent.notebook.get_nth_page(currentPage)
        ourIconView = ourScrolledWindow.getIconView()

        print ourIconView.drawerType
        drawerTypes = Gtk.ListStore(str)
        drawerTypes.append(["Horizontal Strip"])
        drawerTypes.append(["Vertical Strip"])
        drawerTypes.append(["Box"])

        self.iconSize = Gtk.HScale.new_with_range(16, 64, 2)
        self.iconSize.add_mark(48, Gtk.PositionType.BOTTOM, None)
        self.iconSize.set_value(iconSize)

        self.fontSize = Gtk.HScale.new_with_range(1, 24, 1)
        self.fontSize.add_mark(11, Gtk.PositionType.BOTTOM, None)
        self.fontSize.set_value(fontSize)

        self.itemWidth = Gtk.HScale.new_with_range(16, 128, 1)
        self.itemWidth.add_mark(48, Gtk.PositionType.BOTTOM, None)
        self.itemWidth.set_value(itemWidth)

        self.numColumns = Gtk.HScale.new_with_range(2, 9, 1)
        self.numColumns.add_mark(3, Gtk.PositionType.BOTTOM, None)
        self.numColumns.set_value(ourIconView.numColumns)

        self.drawerType = Gtk.ComboBox.new_with_model(drawerTypes)
        self.drawerType.connect("changed", self.onDrawerTypeSelected)

        drawerTypeRenderer = Gtk.CellRendererText()

        self.drawerType.pack_start(drawerTypeRenderer, True)
        self.drawerType.add_attribute(drawerTypeRenderer, "text", 0)

        box = self.get_content_area()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        hboxIconSize = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hboxIconSize.pack_start(Gtk.Label.new("Icon Size"), False, True, 0)
        hboxIconSize.pack_end(self.iconSize, True, True, 20)

        hboxFontSize = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hboxFontSize.pack_start(Gtk.Label.new("Font Size"), False, True, 0)
        hboxFontSize.pack_end(self.fontSize, True, True, 20)

        hboxItemWidth = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hboxItemWidth.pack_start(Gtk.Label.new("Item Width"), False, True, 0)
        hboxItemWidth.pack_end(self.itemWidth, True, True, 20)

        hboxDrawerType = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hboxDrawerType.pack_start(Gtk.Label.new("Drawer Type"), False, True, 0)
        hboxDrawerType.pack_end(self.drawerType, True, True, 20)

        self.hboxNumColumns = self.setHboxNumColumns(self.numColumns)

        vbox.pack_start(hboxIconSize, False, True, 0)
        vbox.pack_start(hboxFontSize, False, True, 0)
        vbox.pack_start(hboxItemWidth, False, True, 0)
        vbox.pack_start(hboxDrawerType, False, True, 0)
        vbox.pack_start(self.hboxNumColumns, False, True, 0)

        box.add(vbox)
        self.show_all()
        if ourIconView.drawerType == "Horizontal":
            self.drawerType.props.active = 0
            self.hboxNumColumns.props.visible = False
        elif ourIconView.drawerType == "Vertical":
            self.drawerType.props.active = 1
            self.hboxNumColumns.props.visible = False
        elif ourIconView.drawerType == "Box":
            self.drawerType.props.active = 2
            self.hboxNumColumns.props.visible = True

    def setHboxNumColumns(self, numColumns):
        hboxNumColumns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hboxNumColumns.pack_start(Gtk.Label.new("Number of columns"), False, True, 0)
        hboxNumColumns.pack_end(numColumns, True, True, 20)
        
        return hboxNumColumns

    def onDrawerTypeSelected(self, combo):
        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        drawerType = model[tree_iter][0]
        if drawerType == "Box":
            self.hboxNumColumns.props.visible = True
            self.drawerTypeName = "Box"
        elif drawerType == "Horizontal Strip":
            try:
                self.hboxNumColumns.props.visible = False
            except AttributeError:
                pass
            self.drawerTypeName = "Horizontal"
        elif drawerType == "Vertical Strip":
            try:
                self.hboxNumColumns.props.visible = False
            except AttributeError:
                pass
            self.drawerTypeName = "Vertical"
        
class OpenDrawerDialog(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, "Open Launcher Folder", parent, 0, 
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
                Gtk.STOCK_DELETE, DELETE_DRAWER))

        self.set_default_size(200, 400)
        box = self.get_content_area()

        self.model = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        self.populate_model(self.model)
        self.treeview = Gtk.TreeView(model=self.model)

        drawerIconRenderer = Gtk.CellRendererPixbuf()
        drawerIconColumn = Gtk.TreeViewColumn("Icon", drawerIconRenderer, pixbuf=0)

        appNameRenderer = Gtk.CellRendererText()
        appNameColumn = Gtk.TreeViewColumn('Launcher Folder', appNameRenderer, text=1)
        appNameColumn.set_sort_column_id(0) 

        self.treeview.append_column(drawerIconColumn)
        self.treeview.append_column(appNameColumn)

        self.tree_selection = self.treeview.get_selection()
        self.tree_selection.props.mode = Gtk.SelectionMode.SINGLE
        self.tree_selection.connect("changed", self.onSelectionChanged)
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(self.treeview)
        scrolled_window.set_min_content_height(400)

        box.add(scrolled_window)
        self.show_all()

    def onSelectionChanged(self, widget):
        (model, pathlist) = self.tree_selection.get_selected_rows()
        for path in pathlist:
            self.tree_iter = model.get_iter(path)
            value = model.get_value(self.tree_iter, 1)
            self.selectedValue = value

    def populate_model(self, model):
        for filename in os.listdir(CONFIG_DIR):
            if ".pickle" in filename:
                drawerIconName = util.getDrawerIconFromPickle(CONFIG_DIR + filename)
                pixbuf = util.getDrawerIconPixbuf(drawerIconName)
                filename = filename.replace(".pickle", "")
                model.append([pixbuf, filename])    

class NewDrawerDialog(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, "New Drawer", parent, 0, 
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
        box = self.get_content_area()

        self.drawerIconFileName = ""

        #dImage = "gtk-page-setup"
        #dImage = "gtk-missing-image"
        dImage = "gtk-select-color"

        self.drawerName = Gtk.Entry()
        self.drawerIcon = Gtk.Button.new_from_icon_name(dImage, 4)
        self.drawerIcon.connect("clicked", self.on_new_drawer_icon_click)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        hbox.pack_start(self.drawerName, False, True, 0)
        hbox.pack_end(self.drawerIcon, True, True, 0)

        box.add(hbox)
        self.show_all()

    def on_new_drawer_icon_click(self, widget):
        dialog = DrawerIconChooserDialog(self)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.drawerIconFileName = dialog.get_filename()
            self.drawerIcon.set_image(Gtk.Image.new_from_pixbuf(self.getPixBuffFromFile(self.drawerIconFileName)))
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
        dialog.destroy()

    def getPixBuffFromFile(self, fileName):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(fileName)
        pixbuf = pixbuf.scale_simple(48, 48, GdkPixbuf.InterpType.BILINEAR)
        
        return pixbuf

class DrawerIconChooserDialog(Gtk.FileChooserDialog):
    def __init__(self, parent):
        Gtk.FileChooserDialog.__init__(self, "Choose Drawer Icon", parent, 
            Gtk.FileChooserAction.OPEN,
        (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
         Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        initDir = os.getenv('HOME') + "/Pictures/icons"
        self.set_current_folder(initDir)
    
class ItemPropertiesDialog(Gtk.Dialog):
    def __init__(self, iterator, appSettings):
        Gtk.Dialog.__init__(self, appSettings[0] + " Properties", None, 0, 
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_APPLY, Gtk.ResponseType.OK))
        
        self.appSettings = appSettings
        self.row = iterator
        self.itemIcon = self.appSettings[1]
        self.execPath = self.appSettings[2]

        matchUrl = re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', self.execPath)
        fileName, fileExtension = os.path.splitext(self.execPath)

        self.set_modal(True)
        self.set_default_size(400, 400)

        self.appNameEntry = Gtk.Entry()
        self.appNameEntry.set_text(self.appSettings[0])

        self.appIconBtn = Gtk.Button.new()
        #itemSize = self.appSettings[3]
        pixbuf = util.getPixBuffFromFile(self.itemIcon, 48)
        self.appIconBtn.set_image(Gtk.Image.new_from_pixbuf(pixbuf))
        self.appIconBtn.connect("clicked", self.on_change_icon_clicked)

        box = self.get_content_area()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        hboxAppName = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hboxAppName.pack_start(Gtk.Label.new("App Name: "), False, True, 0)
        hboxAppName.pack_end(self.appNameEntry, True, True, 20)

        hboxAppIcon = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hboxAppIcon.pack_start(Gtk.Label.new("App Icon: "), False, True, 0)
        hboxAppIcon.pack_end(self.appIconBtn, False, True, 20)

        vbox.pack_start(hboxAppName, False, True, 0)
        vbox.pack_start(hboxAppIcon, False, True, 0)

        if matchUrl:
            line = re.sub('/opt/google/chrome/google-chrome --app=', '', self.execPath)
            line = re.sub('firefox', '', line)
            line = re.sub('google-chrome', '', line).strip()
            self.cleanLink = line

            openWithModel = Gtk.ListStore(str)
            openWithModel.append(["Google Chrome Web App"])
            openWithModel.append(["Google Chrome"])
            openWithModel.append(["Firefox"])

            openWithCbx = Gtk.ComboBox.new_with_model(openWithModel)
            openWithCbx.connect("changed", self.onOpenWithSelected)

            chromeWebAppRegex = re.search('/opt/google/chrome/google-chrome --app=', self.execPath)
            firefoxBrowserRegex = re.search('firefox', self.execPath)
            if chromeWebAppRegex:           
                openWithCbx.props.active = 0
            elif firefoxBrowserRegex:
                openWithCbx.props.active = 2
            else:
                openWithCbx.props.active = 1

            openWithCbxRenderer = Gtk.CellRendererText()

            openWithCbx.pack_start(openWithCbxRenderer, True)
            openWithCbx.add_attribute(openWithCbxRenderer, "text", 0)

            hboxOpenWith = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
            hboxOpenWith.pack_start(Gtk.Label.new("Open With: "), False, True, 0)
            hboxOpenWith.pack_end(openWithCbx, True, True, 20)
            vbox.pack_start(hboxOpenWith, False, True, 0)

        elif fileExtension == ".sh":
            self.execPathEntry = Gtk.Entry()
            self.execPathEntry.set_text(self.execPath)
            self.execPathEntry.connect("changed", self.onExecPathChanged)

            hboxShellScriptPath = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
            hboxShellScriptPath.pack_start(Gtk.Label.new("Execution Path: "), False, True, 0)
            hboxShellScriptPath.pack_end(self.execPathEntry, True, True, 20)
            vbox.pack_start(hboxShellScriptPath, False, True, 0)

        box.add(vbox)
        self.show_all()

    def onExecPathChanged(self, entry):
        self.execPath = entry.get_text()

    def onOpenWithSelected(self, combo):
        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        selectedString = model[tree_iter][0]

        if selectedString == "Google Chrome Web App":
            self.execPath = '/opt/google/chrome/google-chrome --app=' + self.cleanLink
        elif selectedString == "Google Chrome":
            self.execPath = 'google-chrome ' + self.cleanLink
        elif selectedString == "Firefox":
            self.execPath = 'firefox ' + self.cleanLink

        print self.execPath

    def on_change_icon_clicked(self, widget):
        dialog = DrawerIconChooserDialog(self)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            #itemSize = self.appSettings[3]
            self.itemIcon = dialog.get_filename()
            pixbuf = util.getPixBuffFromFile(self.itemIcon, 48)
            self.appIconBtn.set_image(Gtk.Image.new_from_pixbuf(pixbuf))
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
        dialog.destroy()

class ScrolledWindowIconView(Gtk.ScrolledWindow):
    def __init__(self, targets, drawerName, drawerIconFileName, isNewFile):
        Gtk.ScrolledWindow.__init__(self)

        self.isNewFile = isNewFile

        self.set_min_content_height(200)
        self.set_min_content_width(400)
        self.drawerName = drawerName
        self.drawerIconFileName = drawerIconFileName

        self.set_border_width(0)
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)

        self.iconView = ShortcutsView()
        self.iconView.drag_dest_set_target_list(targets)    

        if not self.isNewFile:
            configFile = CONFIG_DIR + drawerName
            configList = util.unpickleSettings(configFile + ".pickle")

            self.iconView.iconSize = configList['iconSize']
            self.iconView.fontSize = configList['fontSize']
            self.iconView.itemWidth = configList['itemWidth']
            self.iconView.drawerType = configList['drawerType'][0]
            self.iconView.numColumns = 3
            if len(configList['drawerType']) > 1:
                self.iconView.numColumns = configList['drawerType'][1]

            for item in configList['appList']:
                row = self.iconView.model.append()
                appName = item[0]
                appIcon = item[1]
                execPath = item[2]
    
                self.iconView.model.set_value(row, COLUMN_TEXT, appName)
                self.iconView.model.set_value(row, COLUMN_PIXBUF, util.getPixBuffFromFile(appIcon, self.iconView.iconSize))

                if os.path.isfile(appIcon):
                    pass
                else:
                    appIcon = util.getIconPathFromFileName(appIcon)

                self.iconView.launchDict[appName] = execPath
                self.iconView.drawerSettings = configList

        else:
            self.iconView.iconSize = 48
            self.iconView.fontSize = 9
            self.iconView.itemWidth = 48
            self.iconView.drawerType = "Horizontal"
            self.iconView.numColumns = 3

            self.iconView.drawerSettings['drawerName'] = drawerName
            self.iconView.drawerSettings['iconSize'] = self.iconView.iconSize
            self.iconView.drawerSettings['fontSize'] = self.iconView.fontSize
            self.iconView.drawerSettings['itemWidth'] = self.iconView.itemWidth
            self.iconView.drawerSettings['drawerType'] = [self.iconView.drawerType]
            self.iconView.drawerSettings['appList'] = []
            
        self.iconView.set_font()
        self.iconView.set_item_width(self.iconView.itemWidth)
        self.add(self.iconView)

    def getIconView(self):
        return self.iconView
                
class ShortcutsView(Gtk.IconView):
    def __init__(self):

        self.drawerSettings = {}
        self.launchDict = {}
        self.iconFileNamesList = []

        Gtk.IconView.__init__(self)

        action_group = Gtk.ActionGroup("right_click_actions")

        action_deleteItem = Gtk.Action("DeleteItem", "Delete", None, None)
        action_deleteItem.connect("activate", self.on_delete_item)
        action_group.add_action(action_deleteItem)

        action_properties=Gtk.Action("Properties", "Properties", None, None)
        action_properties.connect("activate", self.on_item_properties)
        action_group.add_action(action_properties)

        self.uimanager = Gtk.UIManager()
        self.uimanager.insert_action_group(action_group)
        self.uimanager.add_ui_from_string(UI_INFO)
        self.popup=self.uimanager.get_widget("/PopupMenu")

        self.set_item_padding(0)
        #self.set_item_width(self.iconSize)
        self.set_columns(4)
        self.set_column_spacing(0)
        self.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.props.activate_on_single_click = False

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("item-activated", self.on_item_activated)
        self.connect("button-release-event", self.on_mouse_click)
        self.connect("motion-notify-event", self.on_pointer_motion)

        self.model = Gtk.ListStore(str, GdkPixbuf.Pixbuf)
        self.set_model(self.model)

        self.set_text_column(COLUMN_TEXT)
        self.set_pixbuf_column(COLUMN_PIXBUF)

        self.drag_dest_set(Gtk.DestDefaults.ALL, [], DRAG_ACTION)
        self.connect("drag-data-received", self.on_drag_data_received)

    def on_item_properties(self, widget, data=None):
        path = self.get_selected_items()
        iterator = self.model.get_iter(path)
        appName = self.model.get_value(iterator, COLUMN_TEXT)

        appSettings = []

        for sublist in self.drawerSettings['appList']:
            if appName in sublist[0]:
                appSettings = sublist

        itemPropertiesDialog = ItemPropertiesDialog(iterator, appSettings)
        itemPropertiesDialog.connect("response", self.itemPropertiesDialogResponse)

    def on_delete_item(self, widget, data=None):
        path = self.get_selected_items()
        iterator = self.model.get_iter(path)
        appName = self.model.get_value(iterator, COLUMN_TEXT)

        for sublist in self.drawerSettings['appList']:
            if appName in sublist[0]:
                self.drawerSettings['appList'].remove(sublist)
                self.launchDict.pop(appName, None)

        self.model.remove(iterator)

    def itemPropertiesDialogResponse(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:

            for sublist in self.drawerSettings['appList']:
                if dialog.appSettings[0] in sublist[0]:
                    self.launchDict.pop(dialog.appSettings[0], None)
                    sublist[0] = dialog.appNameEntry.get_text()
                    sublist[1] = dialog.itemIcon
                    sublist[2] = dialog.execPath
                    self.launchDict[sublist[0]] = dialog.execPath

            self.model.set_value(dialog.row, COLUMN_TEXT, dialog.appNameEntry.get_text())
            self.model.set_value(dialog.row, COLUMN_PIXBUF, self.getPixBuffFromFile(dialog.itemIcon, self.iconSize))
            dialog.destroy()
        elif response_id == Gtk.ResponseType.CANCEL:
            dialog.destroy()

    def set_font(self):
        fontO = Pango.FontDescription("Ubuntu " + str(self.fontSize))
        self.modify_font(fontO)

    def on_drag_data_received(self, widget, drag_context, x,y, data,info, time):
        if info == URI_LIST_MIME_TYPE:
            uris = data.get_uris()
            #print data.get_text()
            for uri in uris:
                #TODO add more url matching like ftp:// etc
                matchUrl = re.match(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', uri)
                #Check if firefox URL was dropped
                if matchUrl:
                    appName = uri
                    execPath = "firefox " + uri
                    linkIcon = self.lookupIcon("text-html")
                    if appName in self.launchDict:
                        pass
                    else:
                        row = self.model.append()
                        self.model.set_value(row, COLUMN_TEXT, appName)
                        self.model.set_value(row, COLUMN_PIXBUF, self.getPixBuffFromFile(linkIcon, self.iconSize))
                        self.launchDict[appName] = execPath
                        self.drawerSettings['appList'].append([appName, linkIcon, execPath])

                else:
                    if "application://" in uri:
                        filename = uri.replace("application://", "")
                        if os.path.isfile(LOCAL_APP_DIR + filename):
                            uri = LOCAL_APP_DIR + filename
                        else:
                            uri = SYSTEM_APP_DIR + filename

                    fileName, fileExtension = os.path.splitext(uri)
                    if fileExtension == ".desktop":
                        fileName = fileName.replace("file://", "")
                        fileName = util.checkForSpaceInFileAndReplace(fileName)

                        appName, appIcon, execPath = util.getAppInfo(fileName + fileExtension)
                        #print util.getAppInfo(fileName + fileExtension)

                        if appName in self.launchDict:
                            pass
                        else:
                            row = self.model.append()
                            self.model.set_value(row, COLUMN_TEXT, appName)
                            self.model.set_value(row, COLUMN_PIXBUF, self.getPixBuffFromFile(appIcon, self.iconSize))
                            self.launchDict[appName] = execPath

                            if os.path.isfile(appIcon):
                                pass
                            else:
                                appIcon = util.getIconPathFromFileName(appIcon)

                            self.drawerSettings['appList'].append([appName, appIcon, execPath])
                            print self.drawerSettings
                    elif fileExtension == ".sh":
                        fileName = fileName.replace("file://", "")
                        fileName = util.checkForSpaceInFileAndReplace(fileName)
                        execPath = "gnome-terminal -x " + fileName + fileExtension

                        gio_file = Gio.File.new_for_uri(uri)
                        file_info = gio_file.query_info('standard::icon', Gio.FileQueryInfoFlags.NONE, None)
                        uri_icon = file_info.get_icon().get_names()[0]

                        fileName = gio_file.get_basename()
                        fileIcon = self.lookupIcon(uri_icon)

                        row = self.model.append()
                        self.model.set_value(row, COLUMN_TEXT, fileName)
                        self.model.set_value(row, COLUMN_PIXBUF, self.getPixBuffFromFile(fileIcon, self.iconSize))

                        self.drawerSettings['appList'].append([fileName, fileIcon, execPath])
                    else:
                        gio_file = Gio.File.new_for_uri(uri)

                        uri = uri.replace("file://", "")
                        type_ = magic.from_file(uri, mime=True)

                        print self.getIconPathFromMime(type_)

                        fileName = gio_file.get_basename()
                        fileIcon = self.getIconPathFromMime(type_)

                        row = self.model.append()
                        self.model.set_value(row, COLUMN_TEXT, fileName)
                        self.model.set_value(row, COLUMN_PIXBUF, self.getPixBuffFromFile(fileIcon, self.iconSize))

                        self.drawerSettings['appList'].append([fileName, fileIcon, uri])
        else:
            uri = data.get_text()
            matchUrl = re.match(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', uri)
            if matchUrl:
                appName = uri
                execPath = "/opt/google/chrome/google-chrome --app=" + uri
                linkIcon = self.lookupIcon("text-html")
                if appName in self.launchDict:
                    pass
                else:
                    row = self.model.append()
                    self.model.set_value(row, COLUMN_TEXT, appName)
                    self.model.set_value(row, COLUMN_PIXBUF, self.getPixBuffFromFile(linkIcon, self.iconSize))
                    self.launchDict[appName] = execPath
                    self.drawerSettings['appList'].append([appName, linkIcon, execPath])
                
    def getIconPathFromMime(self, mimType):
        icon = Gio.content_type_get_icon(mimType)
        theme = Gtk.IconTheme.get_default()
        info = theme.choose_icon(icon.get_names(), 64, 0)
        return info.get_filename()

    def launchFile(self, uri):
        gio_file = Gio.File.new_for_uri(uri)
        handler = gio_file.query_default_handler(None)
        handler.launch([gio_file], None)

    def lookupIcon(self, iconName):
        icon_theme = Gtk.IconTheme.get_default()
        icon = icon_theme.lookup_icon(iconName, 64, 0)
        if icon:
            return icon.get_filename()

    def getPixBuffFromFile(self, fileName, iconSize):
        newFileName = ""
        if os.path.isfile(fileName):
            newFileName = fileName  
        else:
            newFileName = self.lookupIcon(fileName)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(newFileName)
        pixbuf = pixbuf.scale_simple(iconSize, iconSize, GdkPixbuf.InterpType.BILINEAR)
        
        return pixbuf

    def on_item_activated(self, widget, item):
        model = widget.get_model()
        appTitle = model[item][COLUMN_TEXT]

        if appTitle in self.launchDict:
            bashCommand = self.launchDict[appTitle]
            subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
            self.unselect_all()

    def on_mouse_click(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            try:
                path=self.get_selected_items()
            except:
                path=None
                print "path exception"
                pass
            if event.button == 3 and path != None:
                iterator = self.model.get_iter(path)
                value=self.model.get_value(iterator, COLUMN_TEXT)
                self.popup.popup(None, None, None, None, event.button, event.time)

    def on_pointer_motion(self, widget, event):
        path = self.get_path_at_pos(event.x, event.y)
        if path != None:
            self.select_path(path)
        if path == None:
            self.unselect_all()

def main():
    'constructor for your class instances'
    # parse_options()

    # Run the application.    

    if len(sys.argv) > 1:
        editDrawerName = sys.argv[1]
    else:
        editDrawerName = None
    win = MainWindow(editDrawerName)
    win.set_default_size(400, 200)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
