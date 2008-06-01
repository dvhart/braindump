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
        # FIXME: why am I using GObject?  Should I call GObject.__init__(self) here?
        self.model = gtk.ListStore(gobject.TYPE_PYOBJECT)
        self.filters = []
        self.model.set_sort_func(1, self.__gtd_sort)
        self.model.set_sort_column_id(1, gtk.SORT_ASCENDING)

    def __gtd_sort(self, model, iter1, iter2, user_data=None):
        obj1 = self.model[iter1][0]
        obj2 = self.model[iter2][0]
        # Display action rows before non ActionRows
        if isinstance(obj1, GTDActionRow) and not isinstance(obj2, GTDActionRow):
            return -1
        if isinstance(obj2, GTDActionRow) and not isinstance(obj1, GTDActionRow):
            return 1
        # Display the none path before non other items
        if isinstance(obj1, gtd.BaseNone) and not isinstance(obj2, gtd.BaseNone):
            return -1
        if isinstance(obj2, gtd.BaseNone) and not isinstance(obj1, gtd.BaseNone):
            return 1
        if obj1.title.lower() < obj2.title.lower():
            return -1
        if obj2.title.lower() < obj1.title.lower():
            return 1
        return 0

    def filter_new(self):
        filter = self.model.filter_new()
        self.filters.append(filter)
        return filter

    # force all derivative filters to refresh
    def refilter(self, data):
        for f in self.filters:
            f.refilter()

    def gtd_iter(self, obj):
        iter = self.model.get_iter_first()
        while iter:
            if self.model[iter][0] == obj:
                return iter
            iter = self.model.iter_next(iter)
        return None

    def on_gtd_renamed(self, obj):
        iter = self.gtd_iter(obj)
        if iter:
            self.model.row_changed(self.model.get_path(iter), iter)

    def on_gtd_added(self, obj):
        self.model.append([obj])

    def on_gtd_removed(self, obj):
        iter = self.gtd_iter(obj)
        if iter:
            self.model.remove(iter)


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
        if isinstance(model[iter][0], GTDActionRow):
            return show_actions
        return True


class ContextStore(GTDStoreFilter):
    def __init__(self):
        GTDStoreFilter.__init__(self)
        self.model.append([NewContext("Create new context...")])
        self.model.append([ContextNone()])
        for c in GTD().contexts:
            self.model.append([c])
    
    def filter_actions(self, show_actions):
        filter = self.filter_new()
        filter.set_visible_func(self.filter_actions_visible, show_actions)
        return filter
        
    def filter_actions_visible(self, model, iter, data):
        show_actions = data
        if isinstance(model[iter][0], GTDActionRow):
            return show_actions
        return True


# Area gtd datastore
class AreaStore(GTDStoreRealmFilter):
    def __init__(self): # could pass a gtd instance, but it's a singleton, so no need
        GTDStoreRealmFilter.__init__(self)
        self.model.append([NewArea("Create new area...")])
        self.model.append([AreaNone()])
        for r in GTD().realms:
            for a in r.areas:
                self.model.append([a])

    # Filter visibility methods
    def filter_by_realm_visible(self, model, iter, data):
        show_actions = data
        area = model[iter][0]
        if area is None:
            print "FIXME: WHY ARE WE COMPARING A NONE AREA?"
            return False
        if isinstance(area, GTDActionRow):
            return show_actions
        else:
            return area.realm.visible


# Realm and Area 2 level datastore
class RealmAreaStore(gobject.GObject):
    def __init__(self):
        gobject.GObject.__init__(self)
        self.model = gtk.TreeStore(gobject.TYPE_PYOBJECT)
        # A bit irregular to add RealmNone() her directly, but the simplest solution
        # as we don't create filters and have only one view of this model.
        self.model.append(None, [NewRealm("Create new realm...")])
        self.model.append(None, [RealmNone()])
        for r in GTD().realms:
            iter = self.model.append(None, [r])
            self.model.append(iter, [NewArea("Create new area...", r)])
            for a in r.areas:
                self.model.append(iter, [a])

    def __area_iter(self, area):
        realm_iter = self.model.get_iter_first()
        while realm_iter:
            area_iter = self.model.iter_children(realm_iter)
            while area_iter:
                if self.model[area_iter][0] == area:
                    return area_iter
                area_iter = self.model.iter_next(area_iter)
            realm_iter = self.model.iter_next(realm_iter)
        return None

    def __realm_iter(self, realm):
        iter = self.model.get_iter_first()
        while iter:
            if self.model[iter][0] == realm:
                return iter
            iter = self.model.iter_next(iter)
        return None

    # GTD signal handlers
    # FIXME: can we derive from RealmStore and AreaStore
    def on_realm_renamed(self, realm):
        iter = self.__realm_iter(realm)
        if iter:
            self.model.row_changed(self.model.get_path(iter), iter)
        else:
            print "ERROR: ", area.title, " not found in RealmAreaStore"

    def on_realm_added(self, realm):
        iter = self.model.append(None, [realm])
        self.model.append(iter, [NewArea("Create new area...", realm)])

    def on_realm_removed(self, realm):
        # FIXME: what about children (including NewArea) ?
        iter = self.__realm_iter(realm)
        if iter:
                self.model.remove(iter)
        else:
            print "ERROR: ", realm.title, " not found in RealmAreaStore"

    def on_area_renamed(self, area):
        iter = self.__area_iter(area)
        if iter:
            self.model.row_changed(self.model.get_path(iter), iter)
        else:
            print "ERROR: ", area.title, " not found in RealmAreaStore"

    def on_area_added(self, area):
        realm_iter = self.__realm_iter(area.realm)
        self.model.append(realm_iter, [area])

    def on_area_removed(self, area):
        iter = self.__area_iter(area)
        if iter:
            self.model.remove(iter)
        else:
            print "ERROR: ", area.title, " not found in RealmAreaStore"

# Project gtd datastore
class ProjectStore(GTDStoreRealmFilter):
    def __init__(self): # could pass a gtd instance, but it's a singleton, so no need
        GTDStoreRealmFilter.__init__(self)
        self.model.append([NewProject("Create new project...")])
        self.model.append([ProjectNone()])
        for r in GTD().realms:
            for a in r.areas:
                for p in a.projects:
                    self.model.append([p])

    def filter_by_area(self, selection, show_actions):
        filter = self.filter_new()
        filter.set_visible_func(self.filter_by_area_visible, [selection, show_actions])
        return filter

    # Filter visibility methods
    # FIXME: model these visibility methods after those in TaskStore
    def filter_by_realm_visible(self, model, iter, data):
        show_actions = data
        project = model[iter][0]
        if project == None:
            return False
        if isinstance(project, GTDActionRow):
            return show_actions
        else:
            return project.area.realm.visible

    def filter_by_area_visible(self, model, iter, data):
        selection, show_actions = data
        selmodel, paths = selection.get_selected_rows()
        project = model[iter][0]
        if project == None:
            return False
        # FIXME: consider making the omission of basenone types configurable,
        # but right now there is only on user of this filter, and we don't want to see
        # them there (the actual project listing on the project tab)
        if isinstance(project, gtd.BaseNone):
            return False
        if not isinstance(project, GTDActionRow):
            for path in paths:
                if project.area is selmodel[path][0]:
                    return True
            return False
        else:
            return show_actions


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
        filter.set_visible_func(self.__filter_by_selection_visible, [selection, show_actions])
        return filter

    def __filter_by_selection_visible(self, model, iter, data):
        selection, show_actions = data
        selmodel, paths = selection.get_selected_rows()
        task = model[iter][0]
        if isinstance(task, GTDActionRow):
            return show_actions
        if task is None:
            print "FIXME: WHY ARE WE COMPARING A NONE TASK?"
            return False
        #if isinstance(task.project, BaseNone) or isinstance(task.project.area, BaseNone) \
        #   or isinstance(task.project.area.realm, BaseNone):
        #    return True
        else:
            if task.project.area.realm.visible:
                for path in paths:
                    comp = selmodel[path][0] # either a project or a context
                    if isinstance(comp, gtd.Context):
                        if task.contexts.count(comp):
                            return True
                        if len(task.contexts) is 0 and isinstance(comp, gtd.ContextNone):
                            return True
                    elif isinstance(comp, gtd.Project):
                        if task.project is comp:
                            return True
                    elif isinstance(comp, GTDActionRow):
                        continue
                    else:
                        print "ERROR: cannot filter Task on", comp.__class__
            return False
