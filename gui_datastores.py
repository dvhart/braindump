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
from gtd import GTD
import gtk, gtk.glade
import gui
from gtd_action_rows import *


class GTDStoreFilter(gobject.GObject):
    def __init__(self):
        self.model = gtk.ListStore(gobject.TYPE_PYOBJECT)
        self.filters = []

    def filter_new(self):
        filter = self.model.filter_new()
        self.filters.append(filter)
        return filter

    # force all derivative filters to refresh
    def refilter(self, data):
        for f in self.filters:
            f.refilter()


class GTDStoreRealmFilter(GTDStoreFilter):
    def __init__(self):
        GTDStoreFilter.__init__(self)

    def filter_by_realm(self, show_actions):
        filter = self.filter_new()
        filter.set_visible_func(self.filter_by_realm_visible, show_actions)
        return filter

    def filter_by_realm_visible(self, realm):
        print "ERROR: this is an abstract base class" # FIXME: how do I really make it an ABC ?
        return False
        

class RealmStore(GTDStoreFilter):
    def __init__(self):
        GTDStoreFilter.__init__(self)
        self.model.append([NewRealm("Create new realm...")])
        for r in GTD().realms:
            self.model.append([r])

    def filter_actions(self, show_actions):
        filter = self.filter_new()
        filter.set_visible_func(self.filter_actions_visible, show_actions)
        return filter

    def filter_actions_visible(self, model, iter, data):
        show_actions = data
        if isinstance(model[iter][0], NewRealm):
            return show_actions
        return True

    # FIXME: update the store in response to these signals
    def on_realm_renamed(self, context):
        print "FIXME: realm ", realm.title, " renamed"

    def on_realm_added(self, realm):
        self.model.append([realm])

    def on_realm_removed(self, realm):
        print "FIXME: realm ", realm.title, " removed"


# Context gtd datastore
class ContextStore(GTDStoreFilter):
    def __init__(self):
        GTDStoreFilter.__init__(self)
        self.model.append([NewContext("Create new context...")]) # FIXME: ActionRow classes maybe?
        for c in GTD().contexts:
            self.model.append([c])
    
    def filter_actions(self, show_actions):
        filter = self.filter_new()
        filter.set_visible_func(self.filter_actions_visible, show_actions)
        return filter
        
    def filter_actions_visible(self, model, iter, data):
        show_actions = data
        if isinstance(model[iter][0], NewContext):
            return show_actions
        return True

    # FIXME: update the store in response to these signals
    def on_context_renamed(self, context):
        print "FIXME: context ", context.title, " renamed"

    def on_context_added(self, context):
        self.model.append([context])

    def on_context_removed(self, context):
        print "FIXME: context ", context.title, " removed"


# Area gtd datastore
class AreaStore(GTDStoreRealmFilter):
    def __init__(self): # could pass a gtd instance, but it's a singleton, so no need
        GTDStoreRealmFilter.__init__(self)
        self.model.append([NewArea("Create new area...")]) # FIXME: ActionRow classes maybe?
        for r in GTD().realms:
            for a in r.areas:
                self.model.append([a])

    # Filter visibility methods
    def filter_by_realm_visible(self, model, iter, data):
        show_actions = data
        area = model[iter][0]
        if not isinstance(area, NewArea):
            return area.realm.visible
        else:
            return show_actions

    # GTD signal handlers
    def on_area_renamed(self, area):
        # FIXME: should I just use the foreach() routine?
        iter = self.model.get_iter_first()
        while iter:
            if self.model[iter][0] == area:
                self.model.row_changed(self.model.get_path(iter), iter)
                return
            iter = self.model.iter_next(iter)
        print "ERROR: ", area.title, " not found in AreaStore"

    def on_area_added(self, area):
        self.model.append([area])

    def on_area_removed(self, area):
        # FIXME: should I just use the foreach() routine?
        iter = self.model.get_iter_first()
        while iter:
            if self.model[iter][0] == area:
                self.model.remove(iter)
                return
            iter = self.model.iter_next(iter)


# Project gtd datastore
class ProjectStore(GTDStoreRealmFilter):
    def __init__(self): # could pass a gtd instance, but it's a singleton, so no need
        GTDStoreRealmFilter.__init__(self)
        self.model.append([NewProject("Create new project...")]) # FIXME: ActionRow classes maybe?
        for r in GTD().realms:
            for a in r.areas:
                for p in a.projects:
                    self.model.append([p])

    def filter_by_area(self, selection, show_actions):
        filter = self.filter_new()
        filter.set_visible_func(self.filter_by_area_visible, [selection, show_actions])
        return filter

    # Filter visibility methods
    def filter_by_realm_visible(self, model, iter, data):
        show_actions = data
        project = model[iter][0]
        if not isinstance(project, NewProject):
            return project.area.realm.visible
        else:
            return show_actions

    def filter_by_area_visible(self, model, iter, data):
        selection, show_actions = data
        selmodel, paths = selection.get_selected_rows()
        value = model[iter][0]
        if not isinstance(value, NewProject):
            for path in paths:
                if value.area is selmodel[path][0]:
                    return True
            return False
        else:
            return show_actions

    # FIXME: update the store in response to these signals
    def on_project_renamed(self, project):
        print "FIXME: project ", project.title, " renamed"

    def on_project_added(self, project):
        self.model.append([project])

    def on_project_removed(self, project):
        print "FIXME: project ", project.title, " removed"


class TaskStore(GTDStoreRealmFilter):
    def __init__(self):
        GTDStoreRealmFilter.__init__(self)
        self.model.append([NewTask("Create new task...")])
        for r in GTD().realms:
            for a in r.areas:
                for p in a.projects:
                    for t in p.tasks:
                        self.model.append([t])

    def filter_by_selection(self, selection, show_actions):
        filter = self.filter_new()
        filter.set_visible_func(self.filter_by_selection_visible, [selection, show_actions])
        return filter

    def filter_by_selection_visible(self, model, iter, data):
        selection, show_actions = data
        selmodel, paths = selection.get_selected_rows()
        task = model[iter][0]
        if not isinstance(task, NewTask):
            if task.project.area.realm.visible:
                for path in paths:
                    comp = selmodel[path][0] # either a project or a context
                    if isinstance(comp, gtd.Context):
                        if task.contexts.count(comp):
                            return True
                    elif isinstance(comp, gtd.Project):
                        if task.project is comp:
                            return True
                    else:
                        print "ERROR: cannot filter Task on", comp.__class__
            return False
        else:
            return show_actions


    # FIXME: update the store in response to these signals
    def on_task_renamed(self, task):
        print "FIXME: task ", task.title, " renamed"

    def on_task_added(self, task):
        self.model.append([task])

    def on_task_removed(self, task):
        print "FIXME: task ", task.title, " removed"
