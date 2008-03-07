#    Filename: gui_datastores.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: gtd customized datastores for combos and lists
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
# 2007-Sep-02:	Initial version by Darren Hart <darren@dvhart.com>

import gobject
import gtd
import gtk, gtk.glade


# Context gtd datastore and tree listener, should be a good start towards
# separated application logic from the widgets...
# FIXME: add a NewContext like Project and Task stores
class ContextListStore(gtk.ListStore, gtd.TreeListener):
    def __init__(self, gtd_tree):
        gtk.ListStore.__init__(self, gobject.TYPE_PYOBJECT)
        self.gtd_tree = gtd_tree
        self.reload()

    def reload(self):
        self.clear()
        for c in self.gtd_tree.contexts:
            self.append([c])

    # gtd.TreeListener interface
    def on_context_renamed(self, context):
        print context.title, " renamed"

    def on_context_added(self, context):
        print "context ", context.title, " added"

    def on_context_removed(self, context):
        print "context ", context.title, " removed"


# Area gtd datastore and tree listener, should be a good start towards
# separated application logic from the widgets...
class AreaListStore(gtk.ListStore, gtd.TreeListener):
    def __init__(self, gtd_tree):
        # FIXME: use super() properly here
        gtk.ListStore.__init__(self, gobject.TYPE_PYOBJECT)
        self.gtd_tree = gtd_tree
        self.reload()

    def reload(self):
        self.clear()
        for r in self.gtd_tree.realms:
            if r.visible:
                for a in r.areas:
                    self.append([a])

    # return the iter, or None, corresponding to "area"
    # consider a more consistent function name (with gtk names)
    # like get_iter_from_area
    def area_iter(self, area):
        iter = self.get_iter_first()
        while iter:
            if self.get_value(iter, 0) == area:
                return iter
            iter = self.iter_next(iter)
        return None

    # gtd.TreeListener interface
    def on_realm_visible_changed(self, realm):
        print realm.title, " visibility: ", realm.visible

    def on_area_renamed(self, area):
        print area.title, " renamed"

    def on_area_added(self, area):
        print "area ", area.title, " added"

    def on_area_removed(self, area):
        print "area ", area.title, " removed"


# Project gtd datastore and tree listener, should be a good start towards
# separated application logic from the widgets...
class ProjectListStore(gtk.ListStore, gtd.TreeListener):
    def __init__(self, gtd_tree, new_project=False):
        # FIXME: use super() properly here
        gtk.ListStore.__init__(self, gobject.TYPE_PYOBJECT)
        self.gtd_tree = gtd_tree
        if new_project:
            self.new_project = gtd.NewProject("<i>Create new project...</i>")
            self.append([self.new_project])
        else:
            self.new_project = None
        self.reload()

    def clear(self):
        gtk.ListStore.clear(self)
        if self.new_project:
            self.append([self.new_project])

    # FIXME: why do we have a reload() and TaskListStore doesn't?
    # (I know why... but seems inconsistent)
    def reload(self):
        self.clear()
        for r in self.gtd_tree.realms:
            if r.visible:
                for a in r.areas:
                    for p in a.projects:
                        self.append([p])

    # return the iter, or None, corresponding to "project"
    # consider a more consistent function name (with gtk names)
    # like get_iter_from_project
    def project_iter(self, project):
        iter = self.get_iter_first()
        while iter:
            if self.get_value(iter, 0) == project:
                return iter
            iter = self.iter_next(iter)
        return None

    def filter_by_selection(self, selection):
        self.clear()
        selmodel, paths = selection.get_selected_rows()
        for path in paths:
            area = selmodel[path][0]
            for p in area.projects:
                self.append([p])

    # gtd.TreeListener interface
    def on_realm_visible_changed(self, realm):
        print realm.title, " visibility: ", realm.visible

    def on_project_renamed(self, project):
        print project.title, " renamed"

    def on_project_added(self, project):
        print "project ", project.title, " added"

    def on_project_removed(self, project):
        print "project ", project.title, " removed"


class TaskListStore(gtk.ListStore, gtd.TreeListener):
    def __init__(self, gtd_tree):
        # FIXME: use super() properly here
        gtk.ListStore.__init__(self, gobject.TYPE_PYOBJECT)
        self.gtd_tree = gtd_tree
        self.new_task = gtd.NewTask("<i>Create new task...</i>")

    def clear(self):
        gtk.ListStore.clear(self)
        self.append([self.new_task])

    def filter_by_selection(self, selection):
        # FIXME: I'm sure this set testing is horribly inefficient, optimize later
        self.clear()
        tasks = []
        selmodel, paths = selection.get_selected_rows()
        for p in paths:
            obj = selmodel[p][0]
            if isinstance(obj, gtd.Context):
                # FIXME: obj.get_tasks() (or map the property tasks to a method?)
                for t in self.gtd_tree.context_tasks(obj):
                    if not t in set(tasks):
                        tasks.append(t)
                        self.append([t])
            elif isinstance(obj, gtd.Project):
                # FIXME: make for a consistent API? obj.get_tasks()
                for t in obj.tasks:
                    if not t in set(tasks):
                        tasks.append(t)
                        self.append([t])
            else:
                # FIXME: throw an exception
                print "ERROR: unknown filter object"
