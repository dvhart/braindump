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
# 2007-Jun-30:  Initial version by Darren Hart <darren@dvhart.com>

from inspect import currentframe
import datetime

import logging
from logging import debug, info, warning, error, critical

import gtk, gtk.glade
import gnome, gnome.ui
import sys
import os

from config import Config
import gtd
from gtd import GTD
from gui.combo_menu import *
from gui.context_table import *
from gui.stacked_filters import *
from gui.details import *
from gui.widgets import *
from gui_datastores import *
from filters import *

# FIXME: make this in a package, and import each module in a package
# (ie support multiple backing stores)
from xmlstore import *

class GTDSignalTest:
    def __init__(self):
        GTD().connect("realm_visible_changed", self.on_realm_visible_changed)
        GTD().connect("realm_modified", self.on_realm_modified)
        GTD().connect("realm_added", self.on_realm_added)
        GTD().connect("realm_removed", self.on_realm_removed)
        GTD().connect("area_modified", self.on_area_modified)
        GTD().connect("area_added", self.on_area_added)
        GTD().connect("area_removed", self.on_area_removed)
        GTD().connect("project_modified", self.on_project_modified)
        GTD().connect("project_added", self.on_project_added)
        GTD().connect("project_removed", self.on_project_removed)
        GTD().connect("task_modified", self.on_task_modified)
        GTD().connect("task_added", self.on_task_added)
        GTD().connect("task_removed", self.on_task_removed)
        GTD().connect("context_modified", self.on_context_modified)
        GTD().connect("context_added", self.on_context_added)
        GTD().connect("context_removed", self.on_context_removed)

    def on_realm_visible_changed(self, tree, realm):
        debug('on_realm_visible_changed: %s.visible = %s' % (realm.title, realm.visible))
    def on_realm_modified(self, tree, realm):
        debug('realm_modified: %s' % (realm.title))
    def on_realm_added(self, tree, realm):
        debug('realm_added: %s' % (realm.title))
    def on_realm_removed(self, tree, realm):
        debug('realm_removed: %s' % (realm.title))
    def on_area_modified(self, tree, area):
        debug('area_modified: %s' % (area.title))
    def on_area_added(self, tree, area):
        debug('area_added: %s' % (area.title))
    def on_area_removed(self, tree, area):
        debug('area_removed: %s' % (area.title))
    def on_project_modified(self, tree, project):
        debug('project_modified: %s' % (project.title))
    def on_project_added(self, tree, project):
        debug('project_added: %s' % (project.title))
    def on_project_removed(self, tree, project):
        debug('project_removed: %s' % (project.title))
    def on_task_modified(self, tree, task):
        debug('task_modified: %s' % (task.title))
    def on_task_added(self, tree, task):
        debug('task_added: %s' % (task.title))
    def on_task_removed(self, tree, task):
        debug('task_removed: %s' % (task.title))
    def on_context_modified(self, tree, context):
        debug('context_modified: %s' % (context.title))
    def on_context_added(self, tree, context):
        debug('context_added: %s' % (context.title))
    def on_context_removed(self, tree, context):
        debug('context_removed: %s' % (context.title))


# GUI Classses and callbacks
class BrainDump(object):
    def __init__(self):
        self.config = Config() 
        if not sys.modules.has_key("braindump"):
            # FIXME: throw a proper exception
            print "FATAL ERROR: braindump module not found"

        # Calculate the install prefix for things like glade and images
        bd_path = sys.modules["braindump"].__path__[0]
        self.data_dir = bd_path[0:bd_path.find("/lib/python")]

        # aggregate widgets, with member callbacks
        GUI(os.path.join(self.data_dir, "share/braindump/glade/braindump.glade"))
        self.gst = GTDSignalTest() # DELETEME.... later :)

        # Initialize the GTD Tree and load the user data
        GTD(None)
        self.backing_store = XMLStore()
        self.backing_store.load(self.config.braindump_dir)
        self.backing_store.connect(GTD())

        ##### Build Data Stores #####
        # Instantiate the various GUI datastores and filters from the GTD() singleton tree
        # FIXME: filter name is overloaded, clarify model, store, and filter.
        #        keep all filter_new calls here in initialization (not below in model assignments...)
        # FIXME: better names for the filters
        self.hide_actions = ActionRowFilter(False)
        self.task_by_realm = TaskByRealmFilter()
        self.project_by_realm = ProjectByRealmFilter()
        self.area_by_realm = AreaByRealmFilter()
        self.completed_filter = CompletedFilter()

        self.realm_store = RealmStore()
        self.realm_store_action = self.realm_store.filter_new()

        self.realm_store_no_action = self.realm_store.filter_new()
        self.realm_store_no_action.append(self.hide_actions)

        self.realm_area_store = RealmAreaStore()

        self.area_store = AreaStore()
        self.area_store_filter_by_realm = self.area_store.filter_new()
        self.area_store_filter_by_realm.append(self.area_by_realm)
        self.area_store_filter_by_realm_no_action = self.area_store.filter_new()
        self.area_store_filter_by_realm_no_action.extend([self.area_by_realm, self.hide_actions])

        self.project_store = ProjectStore()
        self.project_store_filter_by_realm = self.project_store.filter_new()
        self.project_store_filter_by_realm_no_action = self.project_store.filter_new()

        self.project_store_date = ProjectStore()
        self.project_store_date.sort_by_due_date(True)
        self.project_store_filter_by_area = self.project_store_date.filter_new()

        self.task_store = TaskStore()
        self.task_store_filter = self.task_store.filter_new()

        self.context_store = ContextStore()
        self.context_store_filter_no_action = self.context_store.filter_new()
        self.context_store_filter_no_action.append(self.hide_actions)

        # Date filter store
        self.date_filter_store = gtk.ListStore(gobject.TYPE_PYOBJECT)
        self.date_filter_store.append([FilterItem("All Items", self.all_filter_callback)])
        self.date_filter_store.append([FilterItem("Due Items", self.due_filter_callback)])
        self.date_filter_store.append([FilterItem("Active Items", self.active_filter_callback)])
        self.date_filter_store.append([FilterItem("Future Items", self.future_filter_callback)])
        self.date_filter_store.append([FilterItem("Someday Items", self.someday_filter_callback)])


        ##### Connect GTD Signals #####
        GTD().connect("realm_modified", self.realm_store.on_gtd_modified)
        GTD().connect("realm_added", self.realm_store.on_gtd_added)
        GTD().connect("realm_removed", self.realm_store.on_gtd_removed)

        GTD().connect("realm_modified", self.realm_area_store.on_realm_modified)
        GTD().connect("realm_added", self.realm_area_store.on_realm_added)
        GTD().connect("realm_removed", self.realm_area_store.on_realm_removed)
        GTD().connect("area_modified", self.realm_area_store.on_area_modified)
        GTD().connect("area_added", self.realm_area_store.on_area_added)
        GTD().connect("area_removed", self.realm_area_store.on_area_removed)

        GTD().connect("realm_visible_changed", self.on_realm_visible_changed)

        GTD().connect("area_modified", self.area_store.on_gtd_modified)
        GTD().connect("area_added", self.area_store.on_gtd_added)
        GTD().connect("area_removed", self.area_store.on_gtd_removed)

        GTD().connect("project_modified", self.project_store.on_gtd_modified)
        GTD().connect("project_added", self.project_store.on_gtd_added)
        GTD().connect("project_removed", self.project_store.on_gtd_removed)

        GTD().connect("project_modified", self.project_store_date.on_gtd_modified)
        GTD().connect("project_added", self.project_store_date.on_gtd_added)
        GTD().connect("project_removed", self.project_store_date.on_gtd_removed)

        GTD().connect("task_modified", self.task_store.on_gtd_modified)
        GTD().connect("task_added", self.task_store.on_gtd_added)
        GTD().connect("task_removed", self.task_store.on_gtd_removed)

        GTD().connect("context_modified", self.context_store.on_gtd_modified)
        GTD().connect("context_added", self.context_store.on_gtd_added)
        GTD().connect("context_removed", self.context_store.on_gtd_removed)


        ##### Build the GUI #####
        # Menus, Toolbars, Popups
        self.realm_toggles = RealmToggles("realm_toggles")
        self.gtd_row_popup = GTDRowPopup("gtd_row_popup")

        # Date filter and search bar
        self.filter_by_state = GTDFilterCombo("filter_by_state", self.date_filter_store)
        self.search = SearchEntry("search")
        self.search.connect("changed", self.on_search_changed)

        # Fixup the work_with* radio buttons as the glade directives aren't taking affect
        self.work_with_tasks = GUI().get_widget("work_with_tasks")
        self.work_with_tasks.widget.set_property("draw-indicator", False)
        self.work_with_projects = GUI().get_widget("work_with_projects")
        self.work_with_projects.widget.set_property("draw-indicator", False)

        self.filters_sidebar = StackedFilters("filters", self.context_store.filter_new(),
            self.project_store_filter_by_realm_no_action,
            self.area_store_filter_by_realm_no_action)

        self.filters_sidebar.connect("changed", self.on_filters_sidebar_changed)

        self.gtd_list = GTDListView("gtd_list", self.task_store_filter, self.on_new_task,
                                    self.on_new_project,
                                    os.path.join(self.data_dir, "share/braindump/images"))
        self.gtd_list.widget.get_selection().connect("changed", self.on_gtd_list_selection_changed)

        self.details_form = Details("details_form",
                                    self.project_store_filter_by_realm_no_action,
                                    self.area_store_filter_by_realm_no_action)

        # New task default form
        self.default_project = GTDCombo("default_project",
                                         self.project_store_filter_by_realm_no_action, ProjectNone())
        self.default_context = GTDCombo("default_context", self.context_store_filter_no_action)

        # Dialog boxes
        self.realm_area_dialog = RealmAreaDialog("realm_area_dialog", self.realm_area_store)
        self.about_dialog = AboutDialog("about_dialog")

        # Now that everything is created, connect the signals
        GUI().signal_autoconnect(self)

        # Setup initial state
        # FIXME: store this in the config
        self.work_with_tasks.widget.set_active(0)
        self.filter_by_state.widget.set_active(0)
        self.default_project.set_active(-1)
        self.default_context.set_active(-1)

        # Build the filters and refilter them
        self.task_store_filter.append(self.task_by_realm)
        self.task_store_filter.append(self.filters_sidebar.filter)
        self.task_store_filter.append(Filter(self.search.search))
        self.task_store_filter.append(Filter(self.filter_by_state.filter))

        self.project_store_filter_by_area.append(self.project_by_realm)
        self.project_store_filter_by_area.append(Filter(lambda m,i:
                                                        not isinstance(m[i][0], gtd.BaseNone)))
        self.project_store_filter_by_area.append(self.filters_sidebar.filter)
        self.project_store_filter_by_area.append(Filter(self.search.search))
        self.project_store_filter_by_area.append(Filter(self.filter_by_state.filter))

        self.project_store_filter_by_realm.append(self.project_by_realm)
        self.project_store_filter_by_realm_no_action.extend([self.project_by_realm, self.hide_actions])

        # Load the settings
        self.__apply_config()

    def __apply_config(self):
        # FIXME: could be more robust
        debug("Applying settings from %s" % (self.config.filename))
        for key,val in self.config['view'].iteritems():
            debug("%s : %s" % (key, val == True))
            # Handle custom keys (non-widget-names)
            if key == "layout":
                if val == "Horizontal":
                    menuitem = GUI().get_widget("horizontal_layout").widget
                    menuitem.set_active(True)
                    self.on_horizontal_layout_toggled(menuitem)
                elif val == "Vertical":
                    menuitem = GUI().get_widget("vertical_layout").widget
                    menuitem.set_active(True)
                    self.on_vertical_layout_toggled(menuitem)

            # If not a custom key, try the toggle widget names
            else:
                widget = GUI().get_widget(key)
                if (widget):
                    widget.widget.set_active(val == "True")

        #if self.config['filters']['filter_by_state']:
        #    widget = GUI().get_widget("filter_by_state")

        # Ensure the callback is called, regardless of glade's initial state
        self.on_show_completed_toggled(GUI().get_widget("show_completed").widget)

    ##### Application logic follows #####
    # Menu-item callbacks
    def on_quit_activate(self, menuitem):
        gtk.main_quit()

    def on_show_completed_toggled(self, menuitem):
        debug("active: %s" % (menuitem.get_active()))
        if menuitem.get_active():
            self.task_store_filter.remove(self.completed_filter)
            self.project_store_filter_by_area.remove(self.completed_filter)
            self.project_store_filter_by_realm_no_action.remove(self.completed_filter)
            self.gtd_list.show_completed = True
        else:
            self.task_store_filter.append(self.completed_filter)
            self.project_store_filter_by_area.append(self.completed_filter)
            self.project_store_filter_by_realm_no_action.append(self.completed_filter)
            self.gtd_list.show_completed = False

        # This takes twice as long to update if the TreeView is visible
        self.gtd_list.widget.hide()
        self.task_store_filter.refilter()
        self.project_store_filter_by_area.refilter()
        self.project_store_filter_by_realm_no_action.refilter()
        self.gtd_list.widget.show()

        # FIXME: make this save automagically
        self.config['view']['show_completed'] = menuitem.get_active()
        self.config.write()

    def on_realms_and_areas_activate(self, menuitem):
        self.realm_area_dialog.widget.show()

    def on_show_new_task_defaults_toggled(self, menuitem):
        form = GUI().get_widget("new_task_defaults_form").widget
        if menuitem.active:
            self.default_project.widget.set_active(0)
            self.default_context.widget.set_active(0)
            form.show()
            self.gtd_list.follow_new = False
        else:
            form.hide()
            self.default_project.widget.set_active(-1)
            self.default_context.widget.set_active(-1)
            self.gtd_list.follow_new = True
        # FIXME: make this save automagically
        self.config['view']['show_new_task_defaults'] = menuitem.get_active()
        self.config.write()

    def on_show_realms_toggled(self, menuitem):
        # FIXME: consider removing the realm_filter on hide, and putting it back on show
        # rather than show_all on hide
        if menuitem.active:
            self.realm_toggles.widget.show()
        else:
            self.realm_toggles.widget.show_all()
            self.realm_toggles.widget.hide()
        # FIXME: make this save automagically
        self.config['view']['show_realms'] = menuitem.get_active()
        self.config.write()

    def on_show_filters_toggled(self, menuitem):
        filters = GUI().get_widget("filters").widget
        if menuitem.active:
            filters.show_all()
            # FIXME: how do we know if this will cause the main window to resize?
            # if it does we should resize on hide, but only then
        else:
            win = GUI().get_widget("braindump_window").widget
            wwidth,wheight = win.get_size()
            fwidth,fheight = filters.size_request()
            filters.hide()
            win.resize(wwidth-fwidth, wheight)
        # FIXME: make this save automagically
        self.config['view']['show_filters'] = menuitem.get_active()
        self.config.write()

    def on_show_details_toggled(self, menuitem):
        if menuitem.active:
            self.details_form.widget.show()
        else:
            self.details_form.widget.hide()
        # FIXME: make this save automagically
        self.config['view']['show_details'] = menuitem.get_active()
        self.config.write()

    def on_horizontal_layout_toggled(self, menuitem):
        active = menuitem.get_active()
        if active:
            self.details_form.widget.reparent(GUI().get_widget("details_hpanel").widget)
            # FIXME: make this save automagically
            self.config['view']['layout'] = "Horizontal"
            self.config.write()

    def on_vertical_layout_toggled(self, menuitem):
        active = menuitem.get_active()
        if active:
            self.details_form.widget.reparent(GUI().get_widget("details_vpanel").widget)
            # FIXME: make this save automagically
            self.config['view']['layout'] = "Vertical"
            self.config.write()

    def on_about_activate(self, menuitem):
        self.about_dialog.widget.show()

    # Widget callbacks
    def on_work_with_tasks_toggled(self, widget):
        if widget.get_active():
            self.gtd_list.widget.set_model(self.task_store_filter.model_filter)

    def on_work_with_projects_toggled(self, widget):
        if widget.get_active():
            self.gtd_list.widget.set_model(self.project_store_filter_by_area.model_filter)

    def on_new_task(self, title):
        '''Create a new task from the new task defaults, initiated from the gtd_list.'''
        project = self.default_project.get_active()
        contexts = [self.default_context.get_active()]
        # Don't store ContextNone in the task (we use an empty array to represent that)
        if isinstance(contexts[0], gtd.ContextNone):
            contexts = None
        task = gtd.Task.create(None, title, project, contexts)
        task.start_date = datetime.now()

    def on_new_project(self, title):
        '''Create a new project, initiated from the gtd_list.'''
        project = gtd.Project.create(None, title)
        project.start_date = datetime.now()

    def on_gtd_list_selection_changed(self, selection):
        iter = selection.get_selected()[1]
        tree = selection.get_tree_view()
        model = tree.get_model()
        subject = None
        if iter:
            subject = tree.get_model()[iter][0]
        self.details_form.set_subject(subject)

    # Task and project date filter callbacks
    # FIXME: gotta be a better place for these (they don't reference self, move them out of this file)
    # FIXME: consider just subclassing them?  Seems silly to subclass for only one instantiation...
    def all_filter_callback(self, model, iter):
        # FIXME: ewww...
        obj = model[iter][0]
        if not isinstance(obj, gtd.BaseNone) and isinstance(obj, gtd.Actionable):
            debug("%s %s %s" % (obj.title, obj.start_date, obj.due_date))
        return True

    def due_filter_callback(self, model, iter):
        obj = model[iter][0]
        if isinstance(obj, gtd.Actionable):
            debug("%s %s %s" % (obj.title, obj.start_date, obj.due_date))
            if obj.state == gtd.Actionable.DUE or obj.state == gtd.Actionable.OVERDUE:
                return True
            return False
        return True

    def active_filter_callback(self, model, iter):
        obj = model[iter][0]
        if isinstance(obj, gtd.Actionable):
            debug("%s %s %s" % (obj.title, obj.start_date, obj.due_date))
            if obj.state <= gtd.Actionable.UPCOMING: # includes OVERDUE, DUE, ACTIVE, and UPCOMING
                return True
            return False
        return True

    # There is one invalid state when start_date is future and due_date has past
    def future_filter_callback(self, model, iter):
        obj = model[iter][0]
        if isinstance(obj, gtd.Actionable):
            debug("%s %s %s" % (obj.title, obj.start_date, obj.due_date))
            if obj.state == gtd.Actionable.FUTURE:
                return True
            return False
        return True

    # There are 2 invalid states with start_date = None and due_date is future or passed.  If the due_date is
    # set, we expect start_date to also be set.
    def someday_filter_callback(self, model, iter):
        obj = model[iter][0]
        if isinstance(obj, gtd.Actionable):
            debug("%s %s %s" % (obj.title, obj.start_date, obj.due_date))
            if obj.state == gtd.Actionable.SOMEDAY:
                return True
            return False
        return True

    # FIXME: these three functions are identical!
    def on_filters_sidebar_changed(self, widget):
        self.gtd_list.widget.hide()
        self.task_store_filter.refilter()
        self.project_store_filter_by_area.refilter()
        self.gtd_list.widget.show()

    def on_filter_by_state_changed(self, widget):
        self.gtd_list.widget.hide()
        self.task_store_filter.refilter()
        self.project_store_filter_by_area.refilter()
        self.gtd_list.widget.show()

    def on_search_changed(self, widget):
        self.gtd_list.widget.hide()
        self.task_store_filter.refilter()
        self.project_store_filter_by_area.refilter()
        self.gtd_list.widget.show()

    def on_realm_visible_changed(self, tree, obj):
        # Note: the order here is critical, otherwise combo boxes will update
        # to hide objects from hidden realms, inadvertantly changing the gtd
        # object they represent... FIXME: pretty fragile...
        # FIXME: connect these during data_store construction if possible...
        self.gtd_list.widget.hide()
        self.task_store.refilter()
        self.project_store.refilter()
        self.project_store_date.refilter()
        self.area_store.refilter()
        self.gtd_list.widget.show()

    def on_filters_close_clicked(self, widget):
        GUI().get_widget("show_filters").widget.set_active(False)

    def on_details_close_clicked(self, widget):
        GUI().get_widget("show_details").widget.set_active(False)

    def on_task_defaults_close_clicked(self, widget):
        GUI().get_widget("show_new_task_defaults").widget.set_active(False)

    def on_window_destroy(self, widget):
        gtk.main_quit()
