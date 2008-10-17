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
        GTD().connect("realm_renamed", self.on_realm_renamed)
        GTD().connect("realm_added", self.on_realm_added)
        GTD().connect("realm_removed", self.on_realm_removed)
        GTD().connect("area_renamed", self.on_area_renamed)
        GTD().connect("area_added", self.on_area_added)
        GTD().connect("area_removed", self.on_area_removed)
        GTD().connect("project_renamed", self.on_project_renamed)
        GTD().connect("project_added", self.on_project_added)
        GTD().connect("project_removed", self.on_project_removed)
        GTD().connect("task_renamed", self.on_task_renamed)
        GTD().connect("task_added", self.on_task_added)
        GTD().connect("task_removed", self.on_task_removed)
        GTD().connect("context_renamed", self.on_context_renamed)
        GTD().connect("context_added", self.on_context_added)
        GTD().connect("context_removed", self.on_context_removed)

    def on_realm_visible_changed(self, tree, realm):
        debug('on_realm_visible_changed: %s.visible = %s' % (realm.title, realm.visible))
    def on_realm_renamed(self, tree, realm):
        debug('realm_renamed: %s' % (realm.title))
    def on_realm_added(self, tree, realm):
        debug('realm_added: %s' % (realm.title))
    def on_realm_removed(self, tree, realm):
        debug('realm_removed: %s' % (realm.title))
    def on_area_renamed(self, tree, area):
        debug('area_renamed: %s' % (area.title))
    def on_area_added(self, tree, area):
        debug('area_added: %s' % (area.title))
    def on_area_removed(self, tree, area):
        debug('area_removed: %s' % (area.title))
    def on_project_renamed(self, tree, project):
        debug('project_renamed: %s' % (project.title))
    def on_project_added(self, tree, project):
        debug('project_added: %s' % (project.title))
    def on_project_removed(self, tree, project):
        debug('project_removed: %s' % (project.title))
    def on_task_renamed(self, tree, task):
        debug('task_renamed: %s' % (task.title))
    def on_task_added(self, tree, task):
        debug('task_added: %s' % (task.title))
    def on_task_removed(self, tree, task):
        debug('task_removed: %s' % (task.title))
    def on_context_renamed(self, tree, context):
        debug('context_renamed: %s' % (context.title))
    def on_context_added(self, tree, context):
        debug('context_added: %s' % (context.title))
    def on_context_removed(self, tree, context):
        debug('context_removed: %s' % (context.title))


# GUI Classses and callbacks
class BrainDump(object):
    def __init__(self):
        # aggregate widgets, with member callbacks
        GUI("glade/braindump.glade")

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
        self.project_store_filter_by_area = self.project_store.filter_new()

        self.task_store = TaskStore()
        self.task_store_filter = self.task_store.filter_new()

        self.context_store = ContextStore()
        self.context_store_filter_no_action = self.context_store.filter_new()
        self.context_store_filter_no_action.append(self.hide_actions)

        # Date filter store
        self.date_filter_store = gtk.ListStore(gobject.TYPE_PYOBJECT)
        self.date_filter_store.append([FilterItem("All Items", self.all_filter_callback)])
        self.date_filter_store.append([FilterItem("Active Items", self.active_filter_callback)])
        self.date_filter_store.append([FilterItem("Future Items", self.future_filter_callback)])
        self.date_filter_store.append([FilterItem("Someday Items", self.someday_filter_callback)])


        ##### Connect GTD Signals #####
        GTD().connect("realm_renamed", self.realm_store.on_gtd_renamed)
        GTD().connect("realm_added", self.realm_store.on_gtd_added)
        GTD().connect("realm_removed", self.realm_store.on_gtd_removed)

        GTD().connect("realm_renamed", self.realm_area_store.on_realm_renamed)
        GTD().connect("realm_added", self.realm_area_store.on_realm_added)
        GTD().connect("realm_removed", self.realm_area_store.on_realm_removed)
        GTD().connect("area_renamed", self.realm_area_store.on_area_renamed)
        GTD().connect("area_added", self.realm_area_store.on_area_added)
        GTD().connect("area_removed", self.realm_area_store.on_area_removed)

        # Note: the order here is critical, otherwise combo boxes will update
        # to hide objects from hidden realms, inadvertantly changing the gtd
        # object they represent... FIXME: pretty fragile...
        GTD().connect("realm_visible_changed", lambda g,o: self.task_store.refilter())
        GTD().connect("realm_visible_changed", lambda g,o: self.project_store.refilter())
        GTD().connect("realm_visible_changed", lambda g,o: self.area_store.refilter())

        GTD().connect("area_renamed", self.area_store.on_gtd_renamed)
        GTD().connect("area_added", self.area_store.on_gtd_added)
        GTD().connect("area_removed", self.area_store.on_gtd_removed)

        GTD().connect("project_renamed", self.project_store.on_gtd_renamed)
        GTD().connect("project_added", self.project_store.on_gtd_added)
        GTD().connect("project_removed", self.project_store.on_gtd_removed)

        GTD().connect("task_renamed", self.task_store.on_gtd_renamed)
        GTD().connect("task_added", self.task_store.on_gtd_added)
        GTD().connect("task_removed", self.task_store.on_gtd_removed)

        GTD().connect("context_renamed", self.context_store.on_gtd_renamed)
        GTD().connect("context_added", self.context_store.on_gtd_added)
        GTD().connect("context_removed", self.context_store.on_gtd_removed)


        ##### Build the GUI #####
        # Menus, Toolbars, Popups
        self.realm_toggles = RealmToggles("realm_toggles")
        self.gtd_row_popup = GTDRowPopup("gtd_row_popup")

        # Date filter and search bar
        self.filter_by_date = GTDFilterCombo("filter_by_date", self.date_filter_store)
        self.search = SearchEntry("search")
        self.search.connect("changed", self.on_search_changed)

        # The working mode, currently tasks and projects
        # FIXME: come up with a better naming scheme
        self.work_with = ComboMenu()
        self.work_with.set_markup("<b>", "</b>")
        self.work_with.set_data_func(lambda i: i[0])
        self.work_with.add_item(("Tasks", self.task_store_filter))
        self.work_with.add_item(("Projects", self.project_store_filter_by_area))
        self.work_with.connect("changed", self.on_work_with_changed)
        GUI().get_widget("work_with_placeholder").widget.add(self.work_with)
        self.work_with.show_all()

        self.filters_sidebar = StackedFilters("filters", self.context_store.filter_new(),
            self.project_store_filter_by_realm_no_action,
            self.area_store_filter_by_realm_no_action)

        # FIXME: this passes a widget to refilter, and not GTD()... which we don't use anyway
        self.filters_sidebar.connect("changed", lambda w: self.task_store.refilter())
        self.filters_sidebar.connect("changed", lambda w: self.project_store.refilter())

        self.gtd_list = GTDListView("gtd_list", self.task_store_filter, self.on_new_task)
        self.gtd_list.widget.get_selection().connect("changed", self.on_gtd_list_selection_changed)

        # FIXME: we need to get gobject signals working

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
        # FIXME: store this in gconf?
        self.work_with.set_active(0)
        self.filter_by_date.widget.set_active(0)
        self.default_project.set_active(-1)
        self.default_context.set_active(-1)

        # Build the filters and refilter them
        self.task_store_filter.append(self.task_by_realm)
        self.task_store_filter.append(self.filters_sidebar.filter)
        self.task_store_filter.append(Filter(self.search.search))
        self.task_store_filter.append(Filter(self.filter_by_date.filter))

        self.project_store_filter_by_area.append(self.project_by_realm)
        self.project_store_filter_by_area.append(Filter(lambda p: not isinstance(p, gtd.BaseNone)))
        self.project_store_filter_by_area.append(self.filters_sidebar.filter)
        self.project_store_filter_by_area.append(Filter(self.search.search))
        self.project_store_filter_by_area.append(Filter(self.filter_by_date.filter))

        self.project_store_filter_by_realm.append(self.project_by_realm)
        self.project_store_filter_by_realm_no_action.extend([self.project_by_realm, self.hide_actions])

        # Filter out complete tasks if not explicitly checked
        print "SHOW_COMPLETED: ", GUI().get_widget("show_completed").widget.get_active()
        if not GUI().get_widget("show_completed").widget.get_active():
            self.task_store_filter.append(self.completed_filter)
            self.project_store_filter_by_area.append(self.completed_filter)

        self.task_store_filter.refilter()
        self.project_store_filter_by_area.refilter()
        self.project_store_filter_by_realm_no_action.refilter()

    # Application logic follows
    # Menu-item callbacks
    def on_quit_activate(self, menuitem):
        gtk.main_quit()

    def on_work_with_tasks_toggled(self, menuitem):
        if menuitem.get_active():
            index = self.work_with.get_active()
            if index == 1:
                self.work_with.set_active(0)

    def on_work_with_projects_toggled(self, menuitem):
        if menuitem.get_active():
            index = self.work_with.get_active()
            if index == 0:
                self.work_with.set_active(1)

    def on_show_completed_toggled(self, menuitem):
        if menuitem.get_active():
            self.task_store_filter.remove(self.completed_filter)
            self.project_store_filter_by_area.remove(self.completed_filter)
        else:
            self.task_store_filter.append(self.completed_filter)
            self.project_store_filter_by_area.append(self.completed_filter)
        self.task_store_filter.refilter()
        self.project_store_filter_by_area.refilter()

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

    def on_show_realms_toggled(self, menuitem):
        # FIXME: consider removing the realm_filter on hide, and putting it back on show
        # rather than show_all on hide
        if menuitem.active:
            self.realm_toggles.widget.show()
        else:
            self.realm_toggles.widget.show_all()
            self.realm_toggles.widget.hide()

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

    def on_show_details_toggled(self, menuitem):
        if menuitem.active:
            self.details_form.widget.show()
            # FIXME: how do we know if this will cause the main window to resize?
            # if it does we should resize on hide, but only then
        else:
            win = GUI().get_widget("braindump_window").widget
            wwidth,wheight = win.get_size()
            dwidth,dheight = self.details_form.widget.size_request()
            self.details_form.widget.hide()
            win.resize(wwidth-dwidth, wheight)

    def on_about_activate(self, menuitem):
        self.about_dialog.widget.show()

    # Widget callbacks
    def on_new_task(self, title):
        '''Create a new task from the new task defaults, initiated from the gtd_list.'''
        project = self.default_project.get_active()
        context = self.default_context.get_active()
        gtd.Task.create(None, title, project, [context])

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

    def on_work_with_changed(self, widget, index):
        if index != 0 and index != 1:
            error("work_with index out of range")
            index = 0
        #GUI().get_widget("notebook").widget.set_current_page(index)
        # update the gtd_list model
        model = self.work_with.get_active_item()[1]
        self.gtd_list.widget.set_model(model.model_filter)

        # update the menu radio items accordingly
        if index == 0:
            GUI().get_widget("work_with_tasks").widget.set_active(True)
        elif index == 1:
            GUI().get_widget("work_with_projects").widget.set_active(True)

    def on_filter_by_date_changed(self, widget):
        self.task_store_filter.refilter()
        self.project_store_filter_by_area.refilter()

    def on_search_changed(self, widget):
        self.task_store_filter.refilter()
        self.project_store_filter_by_area.refilter()

    def on_filters_close_clicked(self, widget):
        GUI().get_widget("show_filters").widget.set_active(False)

    def on_details_close_clicked(self, widget):
        GUI().get_widget("show_details").widget.set_active(False)

    def on_task_defaults_close_clicked(self, widget):
        GUI().get_widget("show_new_task_defaults").widget.set_active(False)

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

    app = BrainDump()
    gtk.main()

# test to see if we were run directly
if __name__ == "__main__":
    main()
