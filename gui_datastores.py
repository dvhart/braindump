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
import logging
from filters import *

from logging import debug, info, warning, error, critical

class GTDStoreFilter(AndFilter):
    def __init__(self, model_filter):
        AndFilter.__init__(self)
        self.model_filter = model_filter
        self.model_filter.set_visible_func(self.visible)

    def visible(self, model, iter, data=None):
        obj = model[iter][0]
        debug("VISIBLE test of %s" % (obj.__class__.__name__))
        if obj is None:
            error("GTD Object is None")
            return False
        debug("checking filter for %s" % (obj.title))
        ret = self.filter(model, iter)
        debug("returning %s" % (ret))
        return ret

    def refilter(self):
        debug("refiltering: %s" % (self))
        self.model_filter.refilter()


# Filter objects
class TaskByRealmFilter(Filter):
    def __init__(self):
        Filter.__init__(self, self.filter_by_realm_visible)

    def filter_by_realm_visible(self, model, iter):
        task = model[iter][0]
        if isinstance(task, gtd.Task):
            return task.project.area.realm.visible
        return True


class ProjectByRealmFilter(Filter):
    def __init__(self):
        Filter.__init__(self, self.filter_by_realm_visible)

    def filter_by_realm_visible(self, model, iter):
        project = model[iter][0]
        if isinstance(project, gtd.Project):
            return project.area.realm.visible
        return True


class AreaByRealmFilter(Filter):
    def __init__(self):
        Filter.__init__(self, self.filter_by_realm_visible)

    def filter_by_realm_visible(self, model, iter):
        area = model[iter][0]
        if isinstance(area, gtd.Area):
            return area.realm.visible
        return True


class ActionRowFilter(Filter):
    def __init__(self, show_actions):
        Filter.__init__(self, self.filter_by_actions)
        self._show_actions = show_actions

    def filter_by_actions(self, model, iter):
        obj = model[iter][0]
        if isinstance(obj, GTDActionRow):
            return self._show_actions
        return True

class CompletedFilter(Filter):
    def __init__(self):
        Filter.__init__(self, self.filter_completed)

    def filter_completed(self, model, iter):
        obj = model[iter][0]
        if isinstance(obj, GTDActionRow):
            return True
        elif obj.complete and model[iter][1] == 0:
                return False
        return True

# Datastores (GTD model constructors basically)
# FIXME: consider making a factory, since all the derived objects are nothing
#        but constructors anyway...
class GTDStore(gobject.GObject):
    def __init__(self):
        #gobject.Gobject.__init__(self) # is something like this needed?
        #                          gtd domain object      countdown frame
        self.model = gtk.ListStore(gobject.TYPE_PYOBJECT, gobject.TYPE_INT)
        self.filters = []
        self.model.set_sort_func(1, self.__gtd_sort)
        self.model.set_sort_column_id(1, gtk.SORT_ASCENDING)
        self._by_due_date = False

    def __gtd_sort(self, model, iter1, iter2):
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
        # FIXME: this is rather hideous
        #        o consider a gtd.DateBased which always has a due date
        #        o or perhaps not check at all since by_due_date should only be used
        #          for projects and tasks anyway (maybe add assertions that the field exists)
        if self._by_due_date and ((isinstance(obj1, gtd.Task) and isinstance(obj2, gtd.Task)) or
            (isinstance(obj1, gtd.Project) and isinstance(obj2, gtd.Project))):
            if obj1.due_date and not obj2.due_date:
                return -1
            if obj2.due_date and not obj1.due_date:
                return 1
            if obj1.due_date and obj2.due_date:
                if obj1.due_date < obj2.due_date:
                    return -1
                if obj2.due_date < obj1.due_date:
                    return 1
        if obj1.title.lower() < obj2.title.lower():
            return -1
        if obj2.title.lower() < obj1.title.lower():
            return 1
        return 0

    def add(self, obj):
        # Abstract the model details and provide a simple interface to add a GTD
        # object to the store.
        self.model.append([obj, 0])

    def sort_by_due_date(self, by_due_date):
        self._by_due_date = by_due_date
        # force a resort
        self.model.set_sort_func(1, self.__gtd_sort)

    def filter_new(self):
        filter = GTDStoreFilter(self.model.filter_new())
        self.filters.append(filter)
        return filter

    # force all derivative filters to refresh
    def refilter(self):
        debug("%d filters to refilter in %s" % (len(self.filters), self))
        for f in self.filters:
            f.refilter()

    def gtd_iter(self, obj):
        iter = self.model.get_iter_first()
        while iter:
            if self.model[iter][0] == obj:
                return iter
            iter = self.model.iter_next(iter)
        return None

    # FIXME: this is getting called whenever the cursor changes...
    def on_gtd_modified(self, tree, obj):
        iter = self.gtd_iter(obj)
        if iter:
            self.model.row_changed(self.model.get_path(iter), iter)
            # FIXME: this seems to be the only way to force a resort...
            #        there has to be a better way...
            self.model.set_sort_func(1, self.__gtd_sort)

    def on_gtd_added(self, tree, obj):
        self.add(obj)

    def on_gtd_removed(self, tree, obj):
        iter = self.gtd_iter(obj)
        if iter:
            self.model.remove(iter)


class GTDStoreRealmFilter(GTDStore):
    def __init__(self):
        GTDStore.__init__(self)

    def filter_by_realm(self, show_actions):
        filter = self.filter_new()
        filter.set_visible_func(self.filter_by_realm_visible, show_actions)
        return filter

    def filter_by_realm_visible(self, realm):
        error('%s is an abstract base class' % (self.__class__.__name__)) # FIXME: how do I really make it an ABC ?
        return False
        

class RealmStore(GTDStore):
    def __init__(self):
        GTDStore.__init__(self)
        self.add(NewRealm("Create new realm..."))
        for r in GTD().realms:
            self.add(r)


class ContextStore(GTDStore):
    def __init__(self):
        GTDStore.__init__(self)
        self.add(NewContext("Create new context..."))
        for c in GTD().contexts:
            self.add(c)


# Area gtd datastore
class AreaStore(GTDStoreRealmFilter):
    def __init__(self): # could pass a gtd instance, but it's a singleton, so no need
        GTDStoreRealmFilter.__init__(self)
        self.add(NewArea("Create new area..."))
        for r in GTD().realms:
            for a in r.areas:
                self.add(a)


# Realm and Area 2 level datastore
class RealmAreaStore(gobject.GObject):
    def __init__(self):
        gobject.GObject.__init__(self)
        self.model = gtk.TreeStore(gobject.TYPE_PYOBJECT)
        self.model.set_sort_func(1, self.__gtd_sort)
        self.model.set_sort_column_id(1, gtk.SORT_ASCENDING)
        self.model.append(None, [NewRealm("Create new realm...")])
        for r in GTD().realms:
            # the None path isn't editable, no point in showing it
            if isinstance(r, gtd.RealmNone):
                continue
            iter = self.model.append(None, [r])
            self.model.append(iter, [NewArea("Create new area...", r)])
            for a in r.areas:
                self.model.append(iter, [a])

    # Note: this is an exact copy of the gtd sort function used in GTDTree
    #       think of a way to reuse this code.  Possibly a module level function?
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
    def on_realm_modified(self, tree, realm):
        iter = self.__realm_iter(realm)
        if iter:
            self.model.row_changed(self.model.get_path(iter), iter)
        else:
            error('%s not found in RealmAreaStore' % (area.title))

    def on_realm_added(self, tree, realm):
        iter = self.model.append(None, [realm, 0])
        self.model.append(iter, [NewArea("Create new area...", realm), 0])

    def on_realm_removed(self, tree, realm):
        # FIXME: what about children (including NewArea) ?
        iter = self.__realm_iter(realm)
        if iter:
                self.model.remove(iter)
        else:
            error('%s not found in RealmAreaStore' % (realm.title))

    def on_area_modified(self, tree, area):
        iter = self.__area_iter(area)
        if iter:
            self.model.row_changed(self.model.get_path(iter), iter)
        else:
            error('%s not found in RealmAreaStore' % (area.title))

    def on_area_added(self, tree, area):
        realm_iter = self.__realm_iter(area.realm)
        self.model.append(realm_iter, [area, 0])

    def on_area_removed(self, tree, area):
        iter = self.__area_iter(area)
        if iter:
            self.model.remove(iter)
        else:
            error('%s not found in RealmAreaStore' % (area.title))

# Project gtd datastore
class ProjectStore(GTDStoreRealmFilter):
    def __init__(self): # could pass a gtd instance, but it's a singleton, so no need
        GTDStoreRealmFilter.__init__(self)
        self.add(NewProject("Create new project..."))
        for r in GTD().realms:
            for a in r.areas:
                for p in a.projects:
                    self.add(p)


class TaskStore(GTDStore):
    def __init__(self):
        debug("building TaskStore")
        GTDStore.__init__(self)
        self.sort_by_due_date(True)
        self.add(NewTask("Create new task..."))
        for r in GTD().realms:
            debug("from realm: %s (%d areas)" % (r.title, len(r.areas)))
            for a in r.areas:
                debug("from area: %s (%d projects)" % (a.title, len(a.projects)))
                for p in a.projects:
                    debug("from project: %s (%d tasks)" % (p.title, len(p.tasks)))
                    for t in p.tasks:
                        debug("adding task: %s" % (t.title))
                        for c in t.contexts:
                            debug("\t%s" % (c.title))
                        self.add(t)
