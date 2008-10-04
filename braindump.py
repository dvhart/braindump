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

import sys
from inspect import currentframe
import getopt
import datetime

import logging
from logging import debug, info, warning, error, critical

import gtk, gtk.glade
import gnome, gnome.ui
import sexy

import gtd
from gtd import GTD
from gui import *
from gui_datastores import *
from filters import *

# FIXME: make this in a package, and import each module in a package
# (ie support multiple backing stores)
from xmlstore import *

class GTDSignalTest:
    def __init__(self):
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
        debug('on_realm_visible_changed: %s.visible = %s' % (realm.title, realm.visible))
    def on_realm_renamed(self, realm):
        debug('realm_renamed: %s' % (realm.title))
    def on_realm_added(self, realm):
        debug('realm_added: %s' % (realm.title))
    def on_realm_removed(self, realm):
        debug('realm_removed: %s' % (realm.title))
    def on_area_renamed(self, area):
        debug('area_renamed: %s' % (area.title))
    def on_area_added(self, area):
        debug('area_added: %s' % (area.title))
    def on_area_removed(self, area):
        debug('area_removed: %s' % (area.title))
    def on_project_renamed(self, project):
        debug('project_renamed: %s' % (project.title))
    def on_project_added(self, project):
        debug('project_added: %s' % (project.title))
    def on_project_removed(self, project):
        debug('project_removed: %s' % (project.title))
    def on_task_renamed(self, task):
        debug('task_renamed: %s' % (task.title))
    def on_task_added(self, task):
        debug('task_added: %s' % (task.title))
    def on_task_removed(self, task):
        debug('task_removed: %s' % (task.title))
    def on_context_renamed(self, context):
        debug('context_renamed: %s' % (context.title))
    def on_context_added(self, context):
        debug('context_added: %s' % (context.title))
    def on_context_removed(self, context):
        debug('context_removed: %s' % (context.title))


# GUI Classses and callbacks
class BrainDump(object):
    def __init__(self):
        # aggregate widgets, with member callbacks
        GUI("glade/braindump.glade")

        # load test data for now, later get the last filename from gconf
        #self.filename = "test.gtd"
#        self.filename = None
#        GTD(self.filename)
#        if self.filename == None:
#            GTD().load_test_data()
        self.gst = GTDSignalTest() # DELETEME.... later :)

        # FIXME: testing xml backing store, we need a full routine to get
        # the correct backing store module, the right path to open, etc
        # either stored in gconf or maybe in a "config" module type file...
        GTD(None)
        self.backing_store = XMLStore()
        self.backing_store.load("xml/")
        self.backing_store.connect(GTD())

        #GTD().print_tree()

        ##### Build Data Stores #####
        # Instantiate the various GUI datastores and filters from the GTD() singleton tree
        # FIXME: filter name is overloaded, clarify model, store, and filter.
        #        keep all filter_new calls here in initialization (not below in model assignments...)
        self.hide_actions = ActionRowFilter(False)
        self.task_by_realm = TaskByRealmFilter()
        self.project_by_realm = ProjectByRealmFilter()
        self.area_by_realm = AreaByRealmFilter()

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
        self.project_store_filter_by_area = self.project_store.filter_new()

        self.task_store = TaskStore()
        self.task_store_filter = self.task_store.filter_new()

        self.context_store = ContextStore()
        self.context_store_filter_no_action = self.context_store.filter_new()
        self.context_store_filter_no_action.append(self.hide_actions)

        # Task selection filter store
        self.task_selection_filter_store = gtk.ListStore(gobject.TYPE_PYOBJECT)
        self.task_selection_filter_store.append([gui.ModelItem("By Context",
            self.context_store.filter_new())])
        self.task_selection_filter_store.append([gui.ModelItem("By Project",
            self.project_store_filter_by_realm_no_action)])

        # Date filter store
        self.date_filter_store = gtk.ListStore(gobject.TYPE_PYOBJECT)
        self.date_filter_store.append([gui.FilterItem("All Items", self.all_filter_callback)])
        self.date_filter_store.append([gui.FilterItem("Active Items", self.active_filter_callback)])
        self.date_filter_store.append([gui.FilterItem("Future Items", self.future_filter_callback)])
        self.date_filter_store.append([gui.FilterItem("Someday Items", self.someday_filter_callback)])


        ##### Connect GTD Signals #####
        GTD().sig_realm_renamed.connect(self.realm_store.on_gtd_renamed)
        GTD().sig_realm_added.connect(self.realm_store.on_gtd_added)
        GTD().sig_realm_removed.connect(self.realm_store.on_gtd_removed)

        GTD().sig_realm_renamed.connect(self.realm_area_store.on_realm_renamed)
        GTD().sig_realm_added.connect(self.realm_area_store.on_realm_added)
        GTD().sig_realm_removed.connect(self.realm_area_store.on_realm_removed)
        GTD().sig_area_renamed.connect(self.realm_area_store.on_area_renamed)
        GTD().sig_area_added.connect(self.realm_area_store.on_area_added)
        GTD().sig_area_removed.connect(self.realm_area_store.on_area_removed)

        # Note: the order here is critical, otherwise combo boxes will update
        # to hide objects from hidden realms, inadvertantly changing the gtd
        # object they represent... FIXME: pretty fragile...
        GTD().sig_realm_visible_changed.connect(self.task_store.refilter)
        GTD().sig_realm_visible_changed.connect(self.project_store.refilter)
        GTD().sig_realm_visible_changed.connect(self.area_store.refilter)

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


        ##### Build the GUI #####
        # Menus, Toolbars, Popups
        self.realm_toggles = RealmToggles("realm_toggles")
        self.gtd_row_popup = GTDRowPopup("gtd_row_popup")

        # Date filter and search bar
        self.filter_by_date = GTDFilterCombo("filter_by_date", self.date_filter_store)
        self.search = SearchEntry("search")
        self.search.connect("changed", self.on_search_changed)

        # Task Tab
        self.task_filter_list = TaskFilterListView("task_filter_list")

        # Select all the rows in the view
        # FIXME: Error checking, may need a member callback here
        self.task_filter_all = GUI().get_widget("task_filter_all")
        self.task_filter_all.widget.connect("clicked", lambda w: self.task_filter_list.widget.get_selection().select_all())

        # Select none of the rows in the view
        # FIXME: Error checking, may need a member callback here
        # FIXME: should select (No Context) or (No Project)
        # never allow viewing no tasks at all (will cause problems creating
        # new tasks as they will just vanish from the view)
        self.task_filter_none = GUI().get_widget("task_filter_none")
        self.task_filter_none.widget.connect("clicked", lambda w: self.task_filter_list.widget.get_selection().unselect_all())

        self.task_filter_by = ModelCombo("task_filter_by", self.task_selection_filter_store)
        self.task_filter_by.widget.connect("changed", lambda w: self.task_filter_list.widget.set_model(self.task_filter_by.get_active().model.model_filter))

        self.task_list = TaskListView("task_list", self.task_store_filter, self.on_new_task)
        self.task_filter_list.widget.get_selection().connect("changed", self.task_store.refilter)

        self.task_details_form = TaskDetailsForm("task_details_form",
                                                 self.project_store_filter_by_realm_no_action)

        # New task default form
        self.default_project = GTDCombo("default_project",
                                         self.project_store_filter_by_realm_no_action, ProjectNone())
        self.default_context = GTDCombo("default_context", self.context_store_filter_no_action)


        # Project Tab
        self.area_filter_list = AreaFilterListView("area_filter_list", self.area_store_filter_by_realm_no_action)

        # Select all the rows in the view
        # FIXME: Error checking, may need a member callback here
        self.area_filter_all = GUI().get_widget("area_filter_all")
        self.area_filter_all.widget.connect("clicked", lambda w: self.area_filter_list.widget.get_selection().select_all())

        # Select none of the rows in the view
        # FIXME: Error checking, may need a member callback here
        self.area_filter_none = GUI().get_widget("area_filter_none")
        self.area_filter_none.widget.connect("clicked", lambda w: self.area_filter_list.widget.get_selection().unselect_all())

        self.area_filter_list.widget.get_selection().connect("changed", self.project_store.refilter)
        self.project_list = ProjectListView("project_list", self.project_store_filter_by_area)

        self.project_details_form = ProjectDetailsForm("project_details_form",
                                                       self.area_store_filter_by_realm_no_action)


        # Dialog boxes
        self.realm_area_dialog = RealmAreaDialog("realm_area_dialog", self.realm_area_store)
        self.about_dialog = AboutDialog("about_dialog")

        # Now that everything is created, connect the signals
        GUI().signal_autoconnect(self)

        # Setup initial state
        # FIXME: store this in gconf?
        GUI().get_widget("work_with").widget.set_active(0)
        self.filter_by_date.widget.set_active(0)
        self.task_filter_by.widget.set_active(0)
        self.task_filter_list.widget.get_selection().select_all()
        self.area_filter_list.widget.get_selection().select_all()
        self.default_project.set_active(-1)
        self.default_context.set_active(-1)

        # Build the filters and refilter them
        self.task_store_filter.append(self.task_by_realm)
        self.task_store_filter.append(Filter(self.task_filter_list.selection_match))
        self.task_store_filter.append(Filter(self.search.search))
        self.task_store_filter.append(Filter(self.filter_by_date.filter))
        self.task_store_filter.refilter()

        self.project_store_filter_by_area.append(self.project_by_realm)
        self.project_store_filter_by_area.append(Filter(lambda p: not isinstance(p, gtd.BaseNone))) # FIXME: bit of a hack...
        self.project_store_filter_by_area.append(Filter(self.area_filter_list.selection_match))
        self.project_store_filter_by_area.append(Filter(self.search.search))
        self.project_store_filter_by_area.append(Filter(self.filter_by_date.filter))
        self.project_store_filter_by_area.refilter()

        self.project_store_filter_by_realm.append(self.project_by_realm)
        self.project_store_filter_by_realm_no_action.extend([self.project_by_realm, self.hide_actions])
        self.project_store_filter_by_realm_no_action.refilter()

    # Application logic follows
    # Menu-item callbacks
    def on_quit_activate(self, menuitem):
        gtk.main_quit()

    def on_work_with_tasks_toggled(self, menuitem):
        if menuitem.get_active():
            work_with = GUI().get_widget("work_with").widget
            index = work_with.get_active()
            if index == 1:
                work_with.set_active(0)

    def on_work_with_projects_toggled(self, menuitem):
        if menuitem.get_active():
            work_with = GUI().get_widget("work_with").widget
            index = work_with.get_active()
            if index == 0:
                work_with.set_active(1)

    def on_realms_and_areas_activate(self, menuitem):
        self.realm_area_dialog.widget.show()

    def on_new_task_defaults_activate(self, menuitem):
        form = GUI().get_widget("new_task_defaults_form").widget
        if menuitem.active:
            self.default_project.widget.set_active(0)
            self.default_context.widget.set_active(0)
            form.show()
            self.task_list.follow_new = False
        else:
            form.hide()
            self.default_project.widget.set_active(-1)
            self.default_context.widget.set_active(-1)
            self.task_list.follow_new = True

    def on_show_realms_toggled(self, menuitem):
        # FIXME: consider removing the realm_filter on hide, and putting it back on show
        # rather than show_all on hide
        if menuitem.active:
            self.realm_toggles.widget.show()
        else:
            self.realm_toggles.widget.show_all()
            self.realm_toggles.widget.hide()

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

    # Widget callbacks
    def on_new_task(self, title):
        '''Create a new task from the new task defaults, initiated from the task list.'''
        project = self.default_project.get_active()
        context = self.default_context.get_active()
        gtd.Task.create(None, title, project, [context])

    def on_task_list_cursor_changed(self, tree):
        path = tree.get_cursor()[0]
        task = None
        if path:
            task = tree.get_model()[path][0]
        self.task_details_form.set_task(task)

    def on_project_list_cursor_changed(self, tree):
        path = tree.get_cursor()[0]
        project = None
        if path:
            project = tree.get_model()[path][0]
        self.project_details_form.set_project(project)

    # Task and project date filter callbacks
    # FIXME: gotta be a better place for these!
    # FIXME: consider just subclassing them?  Seems silly to subclass for only one instantiation...
    def all_filter_callback(self, obj):
        # FIXME: ewww...
        if not isinstance(obj, gtd.BaseNone) and (isinstance(obj, gtd.Task) or isinstance(obj, gtd.Project)):
            debug("%s %s %s" % (obj.title, obj.start_date, obj.due_date))
        return True

    def active_filter_callback(self, obj):
        if not isinstance(obj, gtd.BaseNone) and (isinstance(obj, gtd.Task) or isinstance(obj, gtd.Project)):
            debug("%s %s %s" % (obj.title, obj.start_date, obj.due_date))
        if isinstance(obj, gtd.Task) or isinstance(obj, gtd.Project):
            today = datetime.today()
            # FIXME: ewwwwww
            if not (obj.start_date is None and obj.due_date) and not (obj.start_date and obj.start_date <= today):
                return False
        return True

    def future_filter_callback(self, obj):
        if not isinstance(obj, gtd.BaseNone) and (isinstance(obj, gtd.Task) or isinstance(obj, gtd.Project)):
            debug("%s %s %s" % (obj.title, obj.start_date, obj.due_date))
        if isinstance(obj, gtd.Task) or isinstance(obj, gtd.Project):
            today = datetime.today()
            if obj.start_date and obj.start_date <= today:
                return False
            if not obj.start_date and not obj.due_date:
                return False
        return True

    def someday_filter_callback(self, obj):
        if not isinstance(obj, gtd.BaseNone) and (isinstance(obj, gtd.Task) or isinstance(obj, gtd.Project)):
            debug("%s %s %s" % (obj.title, obj.start_date, obj.due_date))
        if isinstance(obj, gtd.Task) or isinstance(obj, gtd.Project):
            today = datetime.today()
            if obj.start_date or obj.due_date:
                return False
        return True

    def on_work_with_changed(self, widget):
        index = widget.get_active()
        if index != 0 and index != 1:
            error("work_with index out of range")
            index = 0
        GUI().get_widget("notebook").widget.set_current_page(index)
        if index == 0:
            GUI().get_widget("work_with_tasks").widget.set_active(True)
        elif index == 1:
            GUI().get_widget("work_with_projects").widget.set_active(True)

    def on_filter_by_date_changed(self, widget):
        self.task_store_filter.refilter()
        self.project_store_filter_by_area.refilter()

    def on_search_changed(self, widget):
        # FIXME: only do one or the other, depending on which we're working with
        self.task_store_filter.refilter()
        self.project_store_filter_by_area.refilter()

    def on_details_close_clicked(self, widget):
        GUI().get_widget("details").widget.set_active(False)

    def on_task_defaults_close_clicked(self, widget):
        GUI().get_widget("new_task_defaults").widget.set_active(False)

    def on_window_destroy(self, widget):
        gtk.main_quit()


def usage():
    basename = currentframe().f_code.co_filename
    print 'Usage: %s [OPTION]...' % (basename) # FIXME: what is the right way to get the filename...
                                               # do I really have to use currentframe().f_code.co_filename ??
    print '  -h, --help               display this help and exit'
    print '  -l, --loglevel=LEVEL     set the logging level: DEBUG (default), WARNING,'
    print '                           INFO, ERROR, CRITICAL'

def main():
    # FIXME: why the try block here? What are the props for?
    #try:
    #    props = { gnome.PARAM_APP_DATADIR : '/usr/share'}
    #    prog = gnome.program_init('braindump', '0.01', properties=props)
    #except:
    #    prog = gnome.program_init('braindump', '0.01')
    #    prog.set_property('app-datadir', '/usr/share')
    logging.basicConfig(level=logging.ERROR,
                        format='%(levelname)s:%(filename)s:%(lineno)d:%(funcName)s:%(message)s')

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hl:", ["help", "loglevel="])
    except getopt.GetoptError, err:
        # print help information and exit:
        error(str(err))
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-l", "--loglevel"):
            if a == "DEBUG": logging.getLogger().setLevel(level=logging.DEBUG)
            elif a == "WARNING": logging.getLogger().setLevel(level=logging.WARNING)
            elif a == "INFO": logging.getLogger().setLevel(level=logging.INFO)
            elif a == "ERROR": logging.getLogger().setLevel(level=logging.ERROR)
            elif a == "CRITICAL": logging.getLogger().setLevel(level=logging.CRITICAL)
            else:
                error('unrecognized log level: %s' % (a))
                usage()
                sys.exit(2)
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    gnome.init("braindump", "0.01") # simpler alternative to the props/prog bits above
    app = BrainDump()
    gtk.main()

# test to see if we were run directly
if __name__ == "__main__":
    main()
