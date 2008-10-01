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

import datetime
from uuid import uuid4
import pickle
from singleton import *
from notify.all import *
from oproperty import *
from logging import debug, info, warning, error, critical

# FIXME: consider adding adding function pointers to the GTD() signals, then
# I wouldn't need to override so may functions (like set_title) they could
# could all just use the base implementation which would call self._sig_rename()

class Base(object):
    def __init__(self, id, title): # FIXME: make id something that gets past in or generated
        if id is None:
            self.id = uuid4()
        else:
            self.id = id
        self.__title = title

    def set_title(self, title):
        self.__title = title

    title = OProperty(lambda s: s.__title, set_title)

class BaseNone(object):
    '''Abstract Base Class for all GTD None element singletons.'''
    pass


class Context(Base):
    def __init__(self, id=None, title=""):
        Base.__init__(self, id, title)
        GTD()._add_context(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().sig_context_renamed(self)
        GTD().sig_context_modified(self)


class ContextNone(Context, BaseNone):
    __metaclass__ = Singleton

    def __init__(self):
        Base.__init__(self, None, "No Context")

    def set_title(self, title):
        debug('Oops, tried to set title on %s' % (self.__class__.__name__))


class Realm(Base):
    def __init__(self, id=None, title="", visible=True):
        self.areas = []
        self.visible = visible
        Base.__init__(self, id, title)
        GTD()._add_realm(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().sig_realm_renamed(self)
        GTD().sig_realm_modified(self)

    def get_tasks(self):
        tasks = []
        for a in self.areas:
            tasks.extend(a.get_tasks())
        return tasks

    def add_area(self, area):
        self.areas.append(area)
        area.realm = self

    def remove_area(self, area):
        self.areas.remove(area)
        area.realm = None

    def set_visible(self, visible):
        self.visible = visible
        GTD().sig_realm_visible_changed(self)


class RealmNone(Realm, BaseNone):
    __metaclass__ =  Singleton

    def __init__(self):
        Base.__init__(self, None, "No Realm")
        self.visible = True
        self.areas = []

    def set_title(self, title):
        debug('Oops, tried to set title on %s' % (self.__class__.__name__))

    def remove_area(self, area):
        if area is not AreaNone():
            Realm.remove_area(self, area)


class Area(Base):
    def __init__(self, id=None, title="", realm=RealmNone()):
        self.projects = []
        Base.__init__(self, id, title)
        self.__realm = realm
        self.__realm.add_area(self)
        GTD().sig_area_added(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().sig_area_renamed(self)
        GTD().sig_area_modified(self)

    def set_realm(self, realm):
        self.__realm = realm
        GTD().sig_area_modified(self)

    def get_tasks(self):
        tasks = []
        for p in self.projects:
            tasks.extend(p.tasks)
        return tasks

    def add_project(self, project):
        self.projects.append(project)
        project.area = self

    def remove_project(self, project):
        self.projects.remove(project)
        project.area = None

    realm = OProperty(lambda s: s.__realm, set_realm)


class AreaNone(Area, BaseNone):
    __metaclass__ =  Singleton

    def __init__(self):
        Base.__init__(self, None, "No Area")
        self.projects = []
        self.realm = RealmNone()
        self.realm.add_area(self)
    
    def set_title(self, title):
        debug('Oops, tried to set title on %s' % (self.__class__.__name__))

    def remove_project(self, project):
        if project is not ProjectNone():
            Area.remove_project(self, project)


class Project(Base):
    __notes = ""
    __start_date = None
    __due_date = None
    __complete = False

    def __init__(self, id=None, title="", notes="", area=None, complete=False):
        self.tasks = []
        Base.__init__(self, id, title)
        if area:
            self.__area = area
        else:
            self.__area = AreaNone()
        self.area.add_project(self)

        self.__notes = notes
        self.__start_date = None
        self.__due_date = None
        self.__complete = complete
        GTD().sig_project_added(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().sig_project_renamed(self)
        GTD().sig_project_modified(self)

    def set_area(self, area):
        self.__area = area
        GTD().sig_project_modified(self)

    def set_complete(self, complete):
        self.__complete = complete
        GTD().sig_project_modified(self)

    def set_notes(self, notes):
        self.__notes = notes
        GTD().sig_project_modified(self)

    def set_start_date(self, start_date):
        self.__start_date = start_date
        GTD().sig_project_modified(self)

    def set_due_date(self, due_date):
        self.__due_date = due_date
        GTD().sig_project_modified(self)

    def add_task(self, task):
        self.tasks.append(task)
        task.project = self

    def remove_task(self, task):
        self.tasks.remove(task)
        task.project = None

    area = OProperty(lambda s: s.__area, set_area)
    notes = OProperty(lambda s: s.__notes, set_notes)
    start_date = OProperty(lambda s: s.__start_date, set_start_date)
    due_date = OProperty(lambda s: s.__due_date, set_due_date)
    complete = OProperty(lambda s: s.__complete, set_complete)

class ProjectNone(Project, BaseNone):
    __metaclass__ = Singleton

    def __init__(self):
        Base.__init__(self, None, "No Project")
        self.tasks = []
        self.area = AreaNone()
        self.area.add_project(self)
        self.notes = ""
        self.complete = False

    def set_title(self, title):
        debug('Oops, tried to set title on %s' % (self.__class__.__name__))


class Task(Base):
    contexts = []
    __notes = ""
    __start_date = None
    __due_date = None
    __waiting = False
    __complete = False

    def __init__(self, id=None, title="", project=None, contexts=[], notes="", waiting=False, complete=False):
        Base.__init__(self, id, title)
        if project:
            self.project = project
        else:
            self.project = ProjectNone()
        self.project.add_task(self)
        # FIXME: public contexts breaks data hiding, should implement
        # an iterator (otherwise someone could do
        #      mytask.contexts.append(mycontext)
        # and it wouldn't get written back to disk as the _modified signal
        # won't be emitted.
        self.contexts = contexts
        self.__notes = notes
        self.__start_date = None # these will be datetime objects
        self.__due_date = None
        self.__waiting = waiting
        self.__complete = complete
        GTD().sig_task_added(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().sig_task_renamed(self)

    def set_project(self, project):
        # FIXME: I think this is a hack, this should never be None
        # maybe just throw an exception here ? or an assert?
        if project:
            self.__project = project
        else:
            self.__project = ProjectNone()
        GTD().sig_task_modified(self)

    def set_complete(self, complete):
        self.__complete = complete
        GTD().sig_task_modified(self)

    def set_notes(self, notes):
        self.__notes = notes
        GTD().sig_task_modified(self)

    def set_start_date(self, start_date):
        self.__start_date = start_date
        GTD().sig_task_modified(self)

    def set_due_date(self, due_date):
        self.__due_date = due_date
        GTD().sig_task_modified(self)

    def add_context(self, context):
        if self.contexts.count(context) == 0:
            self.contexts.append(context)
            GTD().sig_task_modified(self)

    def remove_context(self, context):
        if self.contexts.count(context):
            self.contexts.remove(context)
            GTD().sig_task_modified(self)

    project = OProperty(lambda s: s.__project, set_project)
    notes = OProperty(lambda s: s.__notes, set_notes)
    start_date = OProperty(lambda s: s.__start_date, set_start_date)
    due_date = OProperty(lambda s: s.__due_date, set_due_date)
    complete = OProperty(lambda s: s.__complete, set_complete)


# The top-level GTD tree
class GTD(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.contexts = [ContextNone()]
        self.realms = [RealmNone()]

        # PyNotify Signals
        self.sig_realm_visible_changed = Signal()
        self.sig_realm_renamed = Signal()
        self.sig_realm_modified = Signal()
        self.sig_realm_added = Signal()
        self.sig_realm_removed = Signal()
        self.sig_area_renamed = Signal()
        self.sig_area_modified = Signal()
        self.sig_area_added = Signal()
        self.sig_area_removed = Signal()
        self.sig_project_renamed = Signal()
        self.sig_project_modified = Signal()
        self.sig_project_added = Signal()
        self.sig_project_removed = Signal()
        self.sig_task_renamed = Signal()
        self.sig_task_modified = Signal()
        self.sig_task_added = Signal()
        self.sig_task_removed = Signal()
        self.sig_context_renamed = Signal()
        self.sig_context_modified = Signal()
        self.sig_context_added = Signal()
        self.sig_context_removed = Signal()

    def _add_context(self, context):
        self.contexts.append(context)
        GTD().sig_context_added(context)

    def _add_realm(self, realm):
        self.realms.append(realm)
        GTD().sig_realm_added(realm)

    def load_test_data(self):
        # load test data
        Context(None, "Evening")
        Context(None, "Weekend")
        Context(None, "Errands")
        Context(None, "Online")
        Context(None, "Computer")
        Context(None, "Calls")
        Realm(None, "Personal")
        Realm(None, "Professional")
        remodel = Area(None, "Remodel", self.realms[0])
        staffdev = Area(None, "Staff Development", self.realms[1])

        braindump = Project(None, "BrainDump", "", staffdev, False)
        braindump.start_date = datetime.datetime.today()
        braindump.due_date = datetime.datetime.today() + datetime.timedelta(days=7)
        deck = Project(None, "front deck", "", remodel, False)
        deck.start_date = datetime.datetime.today() + datetime.timedelta(days=7)
        deck.due_date = datetime.datetime.today() + datetime.timedelta(days=14)
        landscape = Project(None, "landscape", "", remodel, False)
        # no dates for landscape - it's a someday project

        taska = Task(None, "research gnome list_item", braindump, [self.contexts[3]], "notes A", False, False)
	taska.start_date = datetime.datetime.today()
	taska.due_date = datetime.datetime.today() + datetime.timedelta(days=1)
        taskb = Task(None, "extend gnome list_item", braindump, [self.contexts[3]], "notes B", False, False)
	taskb.start_date = datetime.datetime.today() + datetime.timedelta(days=7)
	taskb.start_date = datetime.datetime.today() + datetime.timedelta(days=14)
        taskc = Task(None, "lay deck boards", deck, [self.contexts[1]], "use stained boards first", False, False)
	# no dates for taskc - it's a someday task
    
    def context_tasks(self, context):
        tasks = []
        for r in self.realms:
            if r.visible:
                for t in r.get_tasks():
                    if t.contexts.count(context):
                        tasks.append(t)
        return tasks

    def remove_context(self, context):
        for r in self.realms:
            for t in r.get_tasks():
                if t.contexts.count(context):
                    t.contexts.remove(context)
        self.contexts.remove(context)
        self.sig_context_removed(context)

    def remove_realm(self, realm, recurse=False):
        # FIXME: throw exception for input errors?
        if not realm == RealmNone():
            for a in realm.areas:
                if recurse:
                    self.remove_area(a, recurse)
                else:
                    a.realm.remove_area(a)
                    self.sig_area_removed(a)
                    RealmNone().add_area(a)
                    self.sig_area_added(a)
            self.realms.remove(realm)
            self.sig_realm_removed(realm)

    def remove_area(self, area, recurse=False):
        # FIXME: throw exception for input errors?
        if area.realm and not area == AreaNone():
            for p in area.projects:
                if recurse:
                    self.remove_project(p, recurse)
                else:
                    p.area.remove_project(p)
                    self.sig_project_removed(p)
                    AreaNone().add_project(p)
                    self.sig_project_added(p)
            area.realm.remove_area(area)
            self.sig_area_removed(area)

    def remove_project(self, project, recurse=False):
        # FIXME: throw exception for input errors?
        if project.area and not project == ProjectNone():
            for t in project.tasks:
                if recurse:
                    self.remove_task(t, recurse)
                else:
                    t.project.remove_task(t)
                    self.sig_task_removed(t)
                    ProjectNone().add_task(t)
                    self.sig_task_added(t)
            project.area.remove_project(project)
            self.sig_project_removed(project)

    def remove_task(self, task):
        if task.project:
            task.project.remove_task(task)
            self.sig_task_removed(task)
