#    Filename: gtd.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: gtd classes (task, contexts, etc.)
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

from gobject import *
import datetime
from uuid import uuid4
import pickle
from singleton import *
from oproperty import *
from logging import debug, info, warning, error, critical

# FIXME: consider adding adding function pointers to the GTD() signals, then
# I wouldn't need to override so may functions (like set_title) they could
# could all just use the base implementation which would call self._sig_rename()

class Base(object):
    def __init__(self, id, title):
        if id is None:
            self.id = uuid4()
        else:
            self.id = id
        self.__title = title
        self.__tags = {}

    def __cmp__(self, obj):
        if not isinstance(obj, Base):
            return -1
        a = self.__title
        b = obj.title
        if a < b:
            return -1
        elif a == b:
            return 0
        return 1

    def set_title(self, title):
        self.__title = title

    def tag(self, label, val=None):
        if not label:
            error("label is None")
        elif val is not None:
            self.__tags[label] = val
        elif self.__tags.has_key(label):
            return self.__tags[label]
        else:
            debug("label (%s) not in tags" % (label))
            return None

    def remove_tag(self, label):
        ret = None
        if not label:
            error("label is None")
        elif self.__tags.has_key(label):
            ret = self.__tags[label]
            self.__tags.pop(label)
        else:
            debug("label (%s) not in tags" % (label))
        return ret

    title = OProperty(lambda s: s.__title, set_title)

class BaseNone(object):
    '''Abstract Base Class for all GTD None element singletons.'''
    pass


class Context(Base):
    def create(id=None, title=""):
        context = Context(id, title)
        GTD()._add_context(context)
        return context
    create = staticmethod(create)

    def __init__(self, id=None, title=""):
        Base.__init__(self, id, title)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().emit("context_modified", self)


class ContextNone(Context, BaseNone):
    __metaclass__ = Singleton

    def __init__(self):
        Base.__init__(self, None, "No Context")

    def set_title(self, title):
        debug('Oops, tried to set title on %s' % (self.__class__.__name__))


class Realm(Base):
    def create(id=None, title="", visible=True):
        realm = Realm(id, title, visible)
        GTD()._add_realm(realm)
        return realm
    create = staticmethod(create)

    def __init__(self, id, title, visible):
        self.areas = []
        self.visible = visible
        Base.__init__(self, id, title)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().emit("realm_modified", self)

    def get_tasks(self):
        tasks = []
        for a in self.areas:
            tasks.extend(a.get_tasks())
        return tasks

    def add_area(self, area):
        self.areas.append(area)

    def remove_area(self, area):
        self.areas.remove(area)

    def set_visible(self, visible):
        self.visible = visible
        GTD().emit("realm_visible_changed", self)


# FIXME: threse should really derive from Realm (or get rid of them all together and store
# instances of Realm as self.realm_none in the gtd tree
class RealmNone(Base, BaseNone):
    __metaclass__ =  Singleton

    def __init__(self):
        Base.__init__(self, None, "No Realm")
        self.visible = True
        self.areas = []

    def set_title(self, title):
        debug('Oops, tried to set title on %s' % (self.__class__.__name__))

    def add_area(self, area):
        self.areas.append(area)

    def remove_area(self, area):
        if area is not AreaNone():
            self.areas.remove(area)

    def get_tasks(self):
        tasks = []
        for a in self.areas:
            tasks.extend(a.get_tasks())
        return tasks


class Area(Base):
    def create(id=None, title="", realm=RealmNone()):
        area = Area(id, title, realm)
        GTD().emit("area_added", area)
        return area
    create = staticmethod(create)

    def __init__(self, id, title, realm):
        self.projects = []
        Base.__init__(self, id, title)
        self.__realm = realm
        self.__realm.add_area(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().emit("area_modified", self)

    def set_realm(self, realm):
        if not realm:
            error("realm is None")
            self.__realm = RealmNone()
        else:
            self.__realm = realm
        GTD().emit("area_modified", self)

    def get_tasks(self):
        tasks = []
        for p in self.projects:
            tasks.extend(p.tasks)
        return tasks

    def add_project(self, project):
        self.projects.append(project)

    def remove_project(self, project):
        self.projects.remove(project)

    realm = OProperty(lambda s: s.__realm, set_realm)


class AreaNone(Base, BaseNone):
    __metaclass__ =  Singleton

    def __init__(self):
        Base.__init__(self, None, "No Area")
        self.projects = []
        self.realm = RealmNone()
        self.realm.add_area(self)
    
    def set_title(self, title):
        debug('Oops, tried to set title on %s' % (self.__class__.__name__))

    def add_project(self, project):
        self.projects.append(project)

    def remove_project(self, project):
        if project is not ProjectNone():
            self.projects.remove(project)

    def get_tasks(self):
        tasks = []
        for p in self.projects:
            tasks.extend(p.tasks)
        return tasks


class Actionable(Base):
    '''Base Class for Project and Task'''
    def __init__(self, id, title, notes):
        Base.__init__(self, id, title)
        self.__notes = notes
        self.__start_date = None
        self.__due_date = None
        self.__complete = None

    def set_complete(self, complete):
        if complete == True:
            complete = datetime.datetime.now()
        elif complete == False:
            complete = None
        elif complete is not None:
            assert isinstance(complete, datetime.datetime)
        self.__complete = complete

    def set_notes(self, notes):
        self.__notes = notes

    def set_start_date(self, start_date):
        self.__start_date = start_date

    def set_due_date(self, due_date):
        self.__due_date = due_date

    notes = OProperty(lambda s: s.__notes, set_notes)
    start_date = OProperty(lambda s: s.__start_date, set_start_date)
    due_date = OProperty(lambda s: s.__due_date, set_due_date)
    complete = OProperty(lambda s: s.__complete, set_complete)


class Project(Actionable):
    def create(id=None, title="", notes="", area=None):
        project = Project(id, title, notes, area)
        GTD().emit("project_added", project)
        return project
    create = staticmethod(create)

    def __init__(self, id, title, notes, area):
        self.tasks = []
        Actionable.__init__(self, id, title, notes)
        if area:
            self.__area = area
        else:
            self.__area = AreaNone()
        self.area.add_project(self)
    
    # Base methods
    # FIXME: find a way to not have to implement these here at all!
    def set_title(self, title):
        Base.set_title(self, title)
        GTD().emit("project_modified", self)

    # Actionable methods
    # FIXME: find a way to not have to implement these here at all!
    def set_complete(self, complete):
        Actionable.set_complete(self, complete)
        GTD().emit("project_modified", self)

    def set_notes(self, notes):
        Actionable.set_notes(self, notes)
        GTD().emit("project_modified", self)

    def set_start_date(self, start_date):
        Actionable.set_start_date(self, start_date)
        GTD().emit("project_modified", self)

    def set_due_date(self, due_date):
        Actionable.set_due_date(self, due_date)
        GTD().emit("project_modified", self)

    # Project methods
    def set_area(self, area):
        self.__area = area
        GTD().emit("project_modified", self)

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, task):
        self.tasks.remove(task)

    area = OProperty(lambda s: s.__area, set_area)


class ProjectNone(Base, BaseNone):
    __metaclass__ = Singleton

    def __init__(self):
        Base.__init__(self, None, "No Project")
        self.tasks = []
        self.area = AreaNone()
        self.area.add_project(self)
        self.notes = ""
        self.start_date = False
        self.due_date = False
        self.complete = False

    def set_title(self, title):
        debug('Oops, tried to set title on %s' % (self.__class__.__name__))

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, task):
        self.tasks.remove(task)


class Task(Actionable):
    def create(id=None, title="", project=None, contexts=None, notes="", waiting=False):
        task = Task(id, title, project, contexts, notes, waiting)
        GTD().emit("task_added", task)
        return task
    create = staticmethod(create)

    def __init__(self, id, title, project, contexts, notes, waiting):
        Actionable.__init__(self, id, title, notes)
        if project:
            self.__project = project
        else:
            self.__project = ProjectNone()
        self.__project.add_task(self)
        # FIXME: if we have contexts=[] in the signature, it will have 3 items in it, even if
        # called without that parameter... weird...
        if not contexts:
            contexts = []
        self.__contexts = contexts
        self.__waiting = waiting

    # Base methods
    # FIXME: find a way to not have to implement these here at all!
    def set_title(self, title):
        Base.set_title(self, title)
        GTD().emit("task_modified", self)

    # Actionable methods
    # FIXME: find a way to not have to implement these here at all!
    def set_complete(self, complete):
        Actionable.set_complete(self, complete)
        GTD().emit("task_modified", self)

    def set_notes(self, notes):
        Actionable.set_notes(self, notes)
        GTD().emit("task_modified", self)

    def set_start_date(self, start_date):
        Actionable.set_start_date(self, start_date)
        GTD().emit("task_modified", self)

    def set_due_date(self, due_date):
        Actionable.set_due_date(self, due_date)
        GTD().emit("task_modified", self)

    # Task methods
    def set_project(self, project):
        # FIXME: I think this is a hack, this should never be None
        # maybe just throw an exception here ? or an assert?
        if project:
            self.__project = project
        else:
            self.__project = ProjectNone()
        GTD().emit("task_modified", self)

    def add_context(self, context):
        if self.__contexts.count(context) == 0:
            self.__contexts.append(context)
            GTD().emit("task_modified", self)

    def remove_context(self, context):
        if self.__contexts.count(context):
            self.__contexts.remove(context)
            GTD().emit("task_modified", self)

    contexts = OProperty(lambda s: frozenset(s.__contexts), None)
    project = OProperty(lambda s: s.__project, set_project)


# The top-level GTD tree
class GTD(gobject.GObject):
    __metaclass__ = GSingleton

    __gsignals__ = {'realm_visible_changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'realm_modified'        : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'realm_added'           : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'realm_removed'         : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'area_modified'         : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'area_added'            : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'area_removed'          : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'project_modified'      : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'project_added'         : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'project_removed'       : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'task_modified'         : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'task_added'            : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'task_removed'          : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'context_modified'      : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'context_added'         : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'context_removed'       : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,))
                   }

    def __init__(self):
        gobject.GObject.__init__(self)
        self.contexts = [ContextNone()]
        self.realms = [RealmNone()]
        AreaNone()
        ProjectNone()

    def _add_context(self, context):
        self.contexts.append(context)
        self.emit("context_added", context)

    def _add_realm(self, realm):
        self.realms.append(realm)
        self.emit("realm_added", realm)

    def context_tasks(self, context):
        tasks = []
        for r in self.realms:
            if r.visible:
                for t in r.get_tasks():
                    if context in t.contexts:
                        tasks.append(t)
        return tasks

    def remove_context(self, context):
        for r in self.realms:
            for t in r.get_tasks():
                t.remove_context(context)
        self.contexts.remove(context)
        self.emit("context_removed", context)

    def remove_realm(self, realm, recurse=False):
        # FIXME: throw exception for input errors?
        if not realm == RealmNone():
            for a in realm.areas:
                if recurse:
                    self.remove_area(a, recurse)
                else:
                    a.realm.remove_area(a)
                    self.emit("area_removed", a)
                    RealmNone().add_area(a)
                    self.emit("area_added", a)
            self.realms.remove(realm)
            self.emit("realm_removed", realm)

    def remove_area(self, area, recurse=False):
        # FIXME: throw exception for input errors?
        if area.realm and not area == AreaNone():
            for p in area.projects:
                if recurse:
                    self.remove_project(p, recurse)
                else:
                    p.area.remove_project(p)
                    self.emit("project_removed", p)
                    AreaNone().add_project(p)
                    self.emit("project_added", p)
            area.realm.remove_area(area)
            self.emit("area_removed", area)

    def remove_project(self, project, recurse=False):
        # FIXME: throw exception for input errors?
        if project.area and not project == ProjectNone():
            for t in project.tasks:
                if recurse:
                    self.remove_task(t, recurse)
                else:
                    t.project.remove_task(t)
                    # FIXME: maybe task_changed is adequate here...
                    self.emit("task_removed", t)
                    ProjectNone().add_task(t)
                    self.emit("task_added", t)
            project.area.remove_project(project)
            self.emit("project_removed", project)

    def remove_task(self, task):
        if task.project:
            task.project.remove_task(task)
            self.emit("task_removed", task)

    def print_tree(self):
        print "***** THE CURRENT GTD TREE *****"
        for r in self.realms:
            print r.title
            for a in r.areas:
                print "\t'", a.title, "'"
                for p in a.projects:
                    print "\t\t'", p.title, "'"
                    for t in p.tasks:
                        print "\t\t\t'", t.title, "'"
                        for c in t.contexts:
                            print "\t\t\t\t'", c.title, "'"
        print "*******************************"
