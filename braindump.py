#!/usr/bin/env python
#    Filename: braindump.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: BrainDump application class and program initialization code
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Copyright (C) Darren Hart, 2007
#
# 2007-Jun-30:	Initial version by Darren Hart <darren@dvhart.com>

import gtk, gtk.glade
from gui import *
from gui_datastores import *
import gnome
import gtd
from gtd import GTD

class GTDSignalTest:
    def __init__(self):
        self.title = "GTDSignalTest" # FIXME: I'm sure Python can print the class of an instance...
        GTD().sig_realm_visible_changed.connect(self.on_realm_visible_changed)
        GTD().sig_realm_renamed.connect(self.on_realm_renamed)
        GTD().sig_realm_added.connect(self.on_realm_added)
        GTD().sig_realm_removed.connect(self.on_realm_removed)
        GTD().sig_area_renamed.connect(self.on_area_renamed)
        GTD().sig_area_added.connect(self.on_area_added)
        GTD().sig_area_removed.connect(self.on_area_removed)
        GTD().sig_project_renamed.connect(self.on_project_renamed)
        GTD().sig_project_added.connect(self.on_project_added)
        GTD().sig_project_removed.connect(self.on_project_removed)
        GTD().sig_task_renamed.connect(self.on_task_renamed)
        GTD().sig_task_added.connect(self.on_task_added)
        GTD().sig_task_removed.connect(self.on_task_removed)
        GTD().sig_context_renamed.connect(self.on_context_renamed)
        GTD().sig_context_added.connect(self.on_context_added)
        GTD().sig_context_removed.connect(self.on_context_removed)

    def on_realm_visible_changed(self, realm):
        print self.title, "on_realm_visible_changed:", realm.title, ".visible =", realm.visible
    def on_realm_renamed(self, realm):
        print self.title, "realm_renamed:", realm.title
    def on_realm_added(self, realm):
        print self.title, "realm_added:", realm.title
    def on_realm_removed(self, realm):
        print self.title, "realm_removed:", realm.title
    def on_area_renamed(self, area):
        print self.title, "area_renamed:", area.title
    def on_area_added(self, area):
        print self.title, "area_added:", area.title
    def on_area_removed(self, area):
        print self.title, "area_removed:", area.title
    def on_project_renamed(self, project):
        print self.title, "project_renamed:", project.title
    def on_project_added(self, project):
        print self.title, "project_added:", project.title
    def on_project_removed(self, project):
        print self.title, "project_removed:", project.title
    def on_task_renamed(self, task):
        print self.title, "task_renamed:", task.title
    def on_task_added(self, task):
        print self.title, "task_added:", task.title
    def on_task_removed(self, task):
        print self.title, "task_removed:", task.title
    def on_context_renamed(self, context):
        print self.title, "context_renamed:", context.title
    def on_context_added(self, context):
        print self.title, "context_added:", context.title
    def on_context_removed(self, context):
        print self.title, "context_removed:", context.title


# GUI Classses and callbacks
class BrainDump:
    def __init__(self):
        # aggregate widgets, with member callbacks
        GUI("glade/braindump.glade")

        # load test data for now, later get the last filename from gconf
        #self.filename = "test.gtd"
        self.filename = None
        GTD(self.filename)
        if self.filename == None:
            GTD().load_test_data()
        self.gst = GTDSignalTest() # DELETEME.... later :)
        
         # Instantiate the various GUI datastores and filters from the GTD() singleton tree
        self.realm_store = RealmStore()
        self.realm_store_action = self.realm_store.filter_actions(True)
        self.realm_store_no_action = self.realm_store.filter_actions(False)

        self.realm_area_store = RealmAreaStore()

        self.area_store = AreaStore()
        self.area_store_filter_by_realm = self.area_store.filter_by_realm(True)
        self.area_store_filter_by_realm_no_action = self.area_store.filter_by_realm(False)

        self.project_store = ProjectStore()
        self.project_store_filter_by_realm = self.project_store.filter_by_realm(True)
        self.project_store_filter_by_realm_no_action = self.project_store.filter_by_realm(False)

        self.task_store = TaskStore()

        self.context_store = ContextStore()
        self.context_store_action = self.context_store.filter_actions(True)
        self.context_store_filter_no_action = self.context_store.filter_actions(False)

        # Connect Signals
        GTD().sig_realm_renamed.connect(self.realm_store.on_realm_renamed)
        GTD().sig_realm_added.connect(self.realm_store.on_realm_added)
        GTD().sig_realm_removed.connect(self.realm_store.on_realm_removed)

        GTD().sig_realm_renamed.connect(self.realm_area_store.on_realm_renamed)
        GTD().sig_realm_added.connect(self.realm_area_store.on_realm_added)
        GTD().sig_realm_removed.connect(self.realm_area_store.on_realm_removed)
        GTD().sig_area_renamed.connect(self.realm_area_store.on_area_renamed)
        GTD().sig_area_added.connect(self.realm_area_store.on_area_added)
        GTD().sig_area_removed.connect(self.realm_area_store.on_area_removed)

        GTD().sig_realm_visible_changed.connect(self.area_store.refilter)
        GTD().sig_realm_visible_changed.connect(self.project_store.refilter)
        GTD().sig_realm_visible_changed.connect(self.task_store.refilter)

        GTD().sig_area_renamed.connect(self.area_store.on_area_renamed)
        GTD().sig_area_added.connect(self.area_store.on_area_added)
        GTD().sig_area_removed.connect(self.area_store.on_area_removed)

        GTD().sig_project_renamed.connect(self.project_store.on_project_renamed)
        GTD().sig_project_added.connect(self.project_store.on_project_added)
        GTD().sig_project_removed.connect(self.project_store.on_project_removed)

        GTD().sig_task_renamed.connect(self.task_store.on_task_renamed)
        GTD().sig_task_added.connect(self.task_store.on_task_added)
        GTD().sig_task_removed.connect(self.task_store.on_task_removed)

        GTD().sig_context_renamed.connect(self.context_store.on_context_renamed)
        GTD().sig_context_added.connect(self.context_store.on_context_added)
        GTD().sig_context_removed.connect(self.context_store.on_context_removed)


        # Build the GUI and connect the signals
        BrainDumpWindow(GUI().get_widget("braindump_window").widget)

        # Task Tab
        TaskFilterBy(GUI().get_widget("taskfilterby").widget)
        task_filter_list = TaskFilterListView(GUI().get_widget("task_filter_list").widget,
                                              self.context_store_action,
                                              self.project_store_filter_by_realm_no_action)

        self.task_store_filter_by_selection = \
            self.task_store.filter_by_selection(task_filter_list.widget.get_selection(), True)
        TaskListView(GUI().get_widget("task_list").widget, self.task_store_filter_by_selection)
        task_filter_list.widget.get_selection().connect("changed", self.task_store.refilter)

        context_table = ContextTable(GUI().get_widget("task_contexts_table").widget)
        GTD().sig_context_renamed.connect(context_table.on_context_renamed)
        GTD().sig_context_added.connect(context_table.on_context_added)
        GTD().sig_context_removed.connect(context_table.on_context_removed)

        project_combo = ProjectCombo(GUI().get_widget("task_project").widget,
                                     self.project_store_filter_by_realm_no_action)
        GTD().sig_project_renamed.connect(project_combo.on_project_renamed)

        # Project Tab
        area_filter_list = AreaFilterListView(GUI().get_widget("area_filter_list").widget,
                                              self.area_store_filter_by_realm_no_action)
        area_filter_list.widget.get_selection().connect("changed", self.project_store.refilter)
        self.project_store_filter_by_area = \
            self.project_store.filter_by_area(area_filter_list.widget.get_selection(), True)
        ProjectListView(GUI().get_widget("project_list").widget, self.project_store_filter_by_area)

        area_combo = AreaCombo(GUI().get_widget("project_area").widget,
                               self.area_store_filter_by_realm_no_action)

        # add the realm toggle buttons
        realm_toggles = RealmToggles(GUI().get_widget("realm_toggles").widget,
                                     self.realm_store_no_action)

        # FIXME: get the last selection and filterby from last time we were run
        GUI().get_widget("task_filter_list").widget.get_selection().select_all()
        GUI().get_widget("area_filter_list").widget.get_selection().select_all()

        # Build the menu bar (and connect the signals)
        MenuBar(GUI().get_widget("menubar").widget)

        # Build the realms and areas dialog (and connect the signals)
        realm_area_dialog = RealmAreaDialog(GUI().get_widget("realm_area_dialog").widget, self.realm_area_store)
        # Build the GTD Row popup menu (and connect the signals)
        gtd_row_popup = GTDRowPopup(GUI().get_widget("gtd_row_popup").widget)


# test to see if we were run directly
if __name__ == "__main__":
    # FIXME: why the try block here? What are the props for?
    #try:
    #    props = { gnome.PARAM_APP_DATADIR : '/usr/share'}
    #    prog = gnome.program_init('braindump', '0.01', properties=props)
    #except:
    #    prog = gnome.program_init('braindump', '0.01')
    #    prog.set_property('app-datadir', '/usr/share')
    gnome.init("braindump", "0.01") # simpler alternative to the props/prog bits above
    app = BrainDump()
    gtk.main()
