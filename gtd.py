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
import pickle
from singleton import *
from notify.all import *
from oproperty import *
from logging import debug, info, warning, error, critical

class Base(object):
    def __init__(self, title):
        self.__title = title

    def set_title(self, title):
        self.__title = title

    title = OProperty(lambda s: s.__title, set_title)

class BaseNone(object):
    '''Abstract Base Class for all GTD None element singletons.'''
    pass


class Context(Base):
    def __init__(self, title):
        Base.__init__(self, title)
        GTD()._add_context(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().sig_context_renamed(self)


class ContextNone(Context, BaseNone):
    __metaclass__ = Singleton

    def __init__(self):
        Base.__init__(self, "No Context")

    def set_title(self, title):
        debug('Oops, tried to set title on %s' % (self.__class__.__name__))


class Realm(Base):
    def __init__(self, title, visible=True):
        self.areas = []
        self.visible = visible
        Base.__init__(self, title)
        GTD()._add_realm(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().sig_realm_renamed(self)

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
        Base.__init__(self, "No Realm")
        self.visible = True
        self.areas = []

    def set_title(self, title):
        debug('Oops, tried to set title on %s' % (self.__class__.__name__))

    def remove_area(self, area):
        if area is not AreaNone():
            Realm.remove_area(self, area)


class Area(Base):
    def __init__(self, title, realm=RealmNone()):
        self.projects = []
        Base.__init__(self, title)
        self.realm = realm
        self.realm.add_area(self)
        GTD().sig_area_added(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().sig_area_renamed(self)

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


class AreaNone(Area, BaseNone):
    __metaclass__ =  Singleton

    def __init__(self):
        Base.__init__(self, "No Area")
        self.projects = []
        self.realm = RealmNone()
        self.realm.add_area(self)
    
    def set_title(self, title):
        debug('Oops, tried to set title on %s' % (self.__class__.__name__))

    def remove_project(self, project):
        if project is not ProjectNone():
            Area.remove_project(self, project)


class Project(Base):
    def __init__(self, title, notes="", area=AreaNone(), complete=False):
        self.tasks = []
        Base.__init__(self, title)
        self.area = area
        self.notes = notes
        self.startdate = None # these will be datetime objects
        self.duedate = None
        if self.area:
            debug('project area is %s' % (self.area))
            self.area.add_project(self)
        self.complete = complete
        GTD().sig_project_added(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().sig_project_renamed(self)

    def add_task(self, task):
        self.tasks.append(task)
        task.project = self

    def remove_task(self, task):
        self.tasks.remove(task)
        task.project = None


class ProjectNone(Project, BaseNone):
    __metaclass__ = Singleton

    def __init__(self):
        Base.__init__(self, "No Project")
        self.tasks = []
        self.area = AreaNone()
        self.area.add_project(self)
        self.notes = ""
        self.complete = False

    def set_title(self, title):
        debug('Oops, tried to set title on %s' % (self.__class__.__name__))


class Task(Base):
    def __init__(self, title, project=ProjectNone(), contexts=[], notes="", waiting=False, complete=False):
        Base.__init__(self, title)
        self.project = project
        self.contexts = contexts
        self.notes = notes
        self.startdate = None # these will be datetime objects
        self.duedate = None
        self.waiting = waiting
        self.complete = complete
        # FIXME: how do we connect this to the "NoneProject"
        if self.project:
            debug('task project is: %s' % (self.project))
            self.project.add_task(self)
        GTD().sig_task_added(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().sig_task_renamed(self)

    def add_context(self, context):
        if self.contexts.count(context) == 0:
            self.contexts.append(context)

    def remove_context(self, context):
        if self.contexts.count(context):
            self.contexts.remove(context)


# The top-level GTD tree
class GTD(object):
    __metaclass__ = Singleton

    def __init__(self, filename):
        self.contexts = []
        self.realms = []
        RealmNone()

        # PyNotify Signals
        self.sig_realm_visible_changed = Signal()
        self.sig_realm_renamed = Signal()
        self.sig_realm_added = Signal()
        self.sig_realm_removed = Signal()
        self.sig_area_renamed = Signal()
        self.sig_area_added = Signal()
        self.sig_area_removed = Signal()
        self.sig_project_renamed = Signal()
        self.sig_project_added = Signal()
        self.sig_project_removed = Signal()
        self.sig_task_renamed = Signal()
        self.sig_task_added = Signal()
        self.sig_task_removed = Signal()
        self.sig_context_renamed = Signal()
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
        Context("Evening")
        Context("Weekend")
        Context("Errands")
        Context("Online")
        Context("Computer")
        Context("Calls")
        Realm("Personal")
        Realm("Professional")
        remodel = Area("Remodel", self.realms[0])
        staffdev = Area("Staff Development", self.realms[1])

        braindump = Project("BrainDump", "", staffdev, False)
        braindump.startdate = datetime.datetime.today()
        braindump.duedate = datetime.datetime.today() + datetime.timedelta(days=7)
        deck = Project("front deck", "", remodel, False)
        deck.startdate = datetime.datetime.today() + datetime.timedelta(days=7)
        deck.duedate = datetime.datetime.today() + datetime.timedelta(days=14)
        landscape = Project("landscape", "", remodel, False)
        # no dates for landscape - it's a someday project

        taska = Task("research gnome list_item", braindump, [self.contexts[3]], "notes A", False, False)
	taska.startdate = datetime.datetime.today()
	taska.duedate = datetime.datetime.today() + datetime.timedelta(days=1)
        taskb = Task("extend gnome list_item", braindump, [self.contexts[3]], "notes B", False, False)
	taskb.startdate = datetime.datetime.today() + datetime.timedelta(days=7)
	taskb.startdate = datetime.datetime.today() + datetime.timedelta(days=14)
        taskc = Task("lay deck boards", deck, [self.contexts[1]], "use stained boards first", False, False)
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


# Named constructor to avoid recursive calls to __init__ due to tree elements calling GTD() for signal emission
# FIXME: freakishly ugly hack, was supposed to be a named constructor of GTD class... not sur ehow python would do that
def save(tree, filename):
    info('saving tree to %s' % (filename))
    f = open(filename, 'w')
    pickle.dump(tree, f)
    f.close()


def load(filename):
    info('opening tree from %s' % (filename))
    f = open(filename, 'r')
    tree = pickle.load(f)
    f.close()
    return tree


