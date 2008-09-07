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
import logging

class GTDSignalTest:
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
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
        self.log.debug('on_realm_visible_changed: %s.visible = %s' % (realm.title, realm.visible))
    def on_realm_renamed(self, realm):
        self.log.debug('realm_renamed: %s' % (realm.title))
    def on_realm_added(self, realm):
        self.log.debug('realm_added: %s' % (realm.title))
    def on_realm_removed(self, realm):
        self.log.debug('realm_removed: %s' % (realm.title))
    def on_area_renamed(self, area):
        self.log.debug('area_renamed: %s' % (area.title))
    def on_area_added(self, area):
        self.log.debug('area_added: %s' % (area.title))
    def on_area_removed(self, area):
        self.log.debug('area_removed: %s' % (area.title))
    def on_project_renamed(self, project):
        self.log.debug('project_renamed: %s' % (project.title))
    def on_project_added(self, project):
        self.log.debug('project_added: %s' % (project.title))
    def on_project_removed(self, project):
        self.log.debug('project_removed: %s' % (project.title))
    def on_task_renamed(self, task):
        self.log.debug('task_renamed: %s' % (task.title))
    def on_task_added(self, task):
        self.log.debug('task_added: %s' % (task.title))
    def on_task_removed(self, task):
        self.log.debug('task_removed: %s' % (task.title))
    def on_context_renamed(self, context):
        self.log.debug('context_renamed: %s' % (context.title))
    def on_context_added(self, context):
        self.log.debug('context_added: %s' % (context.title))
    def on_context_removed(self, context):
        self.log.debug('context_removed: %s' % (context.title))


# GUI Classses and callbacks
class BrainDump(object):
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

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
        GTD().sig_realm_renamed.connect(self.realm_store.on_gtd_renamed)
        GTD().sig_realm_added.connect(self.realm_store.on_gtd_added)
        GTD().sig_realm_removed.connect(self.realm_store.on_gtd_removed)

        GTD().sig_realm_renamed.connect(self.realm_area_store.on_realm_renamed)
        GTD().sig_realm_added.connect(self.realm_area_store.on_realm_added)
        GTD().sig_realm_removed.connect(self.realm_area_store.on_realm_removed)
        GTD().sig_area_renamed.connect(self.realm_area_store.on_area_renamed)
        GTD().sig_area_added.connect(self.realm_area_store.on_area_added)
        GTD().sig_area_removed.connect(self.realm_area_store.on_area_removed)

        GTD().sig_realm_visible_changed.connect(self.area_store.refilter)
        GTD().sig_realm_visible_changed.connect(self.project_store.refilter)
        GTD().sig_realm_visible_changed.connect(self.task_store.refilter)

        GTD().sig_area_renamed.connect(self.area_store.on_gtd_renamed)
        GTD().sig_area_added.connect(self.area_store.on_gtd_added)
        GTD().sig_area_removed.connect(self.area_store.on_gtd_removed)

        GTD().sig_project_renamed.connect(self.project_store.on_gtd_renamed)
        GTD().sig_project_added.connect(self.project_store.on_gtd_added)
        GTD().sig_project_removed.connect(self.project_store.on_gtd_removed)

        GTD().sig_task_renamed.connect(self.task_store.on_gtd_renamed)
        GTD().sig_task_added.connect(self.task_store.on_gtd_added)
        GTD().sig_task_removed.connect(self.task_store.on_gtd_removed)

        GTD().sig_context_renamed.connect(self.context_store.on_gtd_renamed)
        GTD().sig_context_added.connect(self.context_store.on_gtd_added)
        GTD().sig_context_removed.connect(self.context_store.on_gtd_removed)

        # Menus and Toolbars
        self.realm_toggles = RealmToggles("realm_toggles")
        self.gtd_row_popup = GTDRowPopup("gtd_row_popup")

        # Task Tab
        self.task_filter_list = TaskFilterListView("task_filter_list", self.context_store_action,
                                                   self.project_store_filter_by_realm_no_action)
        GUI().get_widget("taskfilterby").widget.set_active(0)

        self.task_store_filter_by_selection = \
            self.task_store.filter_by_selection(self.task_filter_list.widget.get_selection(), True)
        self.task_list = TaskListView("task_list", self.task_store_filter_by_selection, self.on_new_task)
        self.task_filter_list.widget.get_selection().connect("changed", self.task_store.refilter)

        # FIXME: we pass this callback down two levels from here... seems kinda bad...
        # perhaps we should just set up the callbacks from here?
        self.task_details_form = TaskDetailsForm("task_details_form",
                                                 self.project_store_filter_by_realm_no_action)


        # Project Tab
        self.area_filter_list = AreaFilterListView("area_filter_list", self.area_store_filter_by_realm_no_action)
        self.area_filter_list.widget.get_selection().connect("changed", self.project_store.refilter)
        self.project_store_filter_by_area = \
            self.project_store.filter_by_area(self.area_filter_list.widget.get_selection(), True)
        self.project_list = ProjectListView("project_list", self.project_store_filter_by_area)

        self.project_details_form = ProjectDetailsForm("project_details_form",
                                                       self.area_store_filter_by_realm_no_action)


        # New task default form
        self.default_project_combo = GTDCombo("default_project_combo",
                                              self.project_store_filter_by_realm_no_action, ProjectNone())
        self.default_project_combo.set_active(None)
        self.default_context_combo = GTDCombo("default_context_combo", self.context_store_filter_no_action)
        self.default_context_combo.set_active(None)

        # Dialog boxes
        self.realm_area_dialog = RealmAreaDialog("realm_area_dialog", self.realm_area_store)
        self.about_dialog = AboutDialog("about_dialog")

        # FIXME: get the last selection and filterby from last time we were run
        self.task_filter_list.widget.get_selection().select_all()
        self.area_filter_list.widget.get_selection().select_all()

        # Noew that everything is created, connect the signals
        GUI().signal_autoconnect(self)

    # Application logic follows
    # Menu-item callbacks
    def on_quit_activate(self, menuitem):
        gtk.main_quit()

    def on_realms_and_areas_activate(self, menuitem):
        self.realm_area_dialog.widget.show()

    def on_new_task_defaults_activate(self, menuitem):
        form = GUI().get_widget("new_task_defaults_form").widget
        if menuitem.active:
            form.show()
            self.task_list.follow_new = False
        else:
            form.hide()
            self.default_project_combo.widget.set_active(0)
            self.default_context_combo.widget.set_active(0)
            self.task_list.follow_new = True

    def on_details_activate(self, menuitem):
        # FIXME: the main window should grow/shrink to accomodate this form
        #        consider moving both forms to the same parent hbox so it can
        #        be shown/hidden in one shot.
        task_form = GUI().get_widget("task_details_form").widget
        project_form = GUI().get_widget("project_details_form").widget
        if menuitem.active:
            task_form.show()
            project_form.show()
        else:
            task_form.hide()
            project_form.hide()

    def on_about_activate(self, menuitem):
        self.about_dialog.widget.show()
    # End menu-item callbacks

    def on_new_task(self, title):
        '''Create a new task from the new task defaults, initiated from the task list.'''
        project = self.default_project_combo.get_active()
        context = self.default_context_combo.get_active()
        gtd.Task(title, project, [context])

    def on_window_destroy(self, widget):
        gtk.main_quit()



# test to see if we were run directly
if __name__ == "__main__":
    # FIXME: why the try block here? What are the props for?
    #try:
    #    props = { gnome.PARAM_APP_DATADIR : '/usr/share'}
    #    prog = gnome.program_init('braindump', '0.01', properties=props)
    #except:
    #    prog = gnome.program_init('braindump', '0.01')
    #    prog.set_property('app-datadir', '/usr/share')
    logging.basicConfig(level=logging.DEBUG) # DEBUG INFO WARNING ERROR CRITICAL
    gnome.init("braindump", "0.01") # simpler alternative to the props/prog bits above
    app = BrainDump()
    gtk.main()
