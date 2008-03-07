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

import pickle
from singleton import *
from notify.all import *
from oproperty import *

__realm_none = None
__area_none = None
__project_none = None


class Base(object):
    def __init__(self, title):
        self.__title = title

    def set_title(self, title):
        self.__title = title

    title = OProperty(lambda s: s.__title, set_title)


class Context(Base):
    def __init__(self, title):
        Base.__init__(self, title)
        GTD().sig_context_added(self)

    def set_title(self, title):
        Base.set_title(self, title)
        # FIXME: alternatively we could just have a renamed_signal that we assign and call from the base class,
        # rather than using the special OProperty derived set_title calls... Need to give this some thought, both
        # have pros/cons, but OProprety seems generally useful...
        GTD().sig_context_renamed(self)


class Realm(Base):
    def __init__(self, title, visible=True):
        self.areas = []
        self.visible = visible
        Base.__init__(self, title)

        GTD().sig_realm_added(self)

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

    def remove_area(self, area):
        self.areas.remove(area)

    def set_visible(self, visible):
        self.visible = visible
        GTD().sig_realm_visible_changed(self)


class Area(Base):
    def __init__(self, title, realm=__realm_none):
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

    def remove_project(self, project):
        self.projects.remove(project)


class Project(Base):
    def __init__(self, title, notes="", area=__area_none, complete=False):
        self.tasks = []
        Base.__init__(self, title)
        self.area = area
        self.notes = notes
        if self.area:
            print "Project area is: ", self.area
            self.area.add_project(self)
        self.complete = complete
        GTD().sig_project_added(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().sig_project_renamed(self)

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, task):
        self.tasks.remove(task)


# Placeholder class for "Click to create new project..." type items in lists
# Perhaps this is better placed in the gui code, rather than here...
class NewProject(object):
    def __init__(self, title_str):
        self.__title = title_str

    def create_new_project(self, title):
        # FIXME: pick an appropriate area from the active filters
        new_project = Project(title)

    title = property(lambda s: s.__title, create_new_project)
    area = property(lambda s: None)
    tasks = property(lambda s: [])
    project = property(lambda s: None)
    contexts = property(lambda s: [])
    notes = property(lambda s: "")
    waiting = property(lambda s: False)
    complete = property(lambda s: False)


class Task(Base):
    def __init__(self, title, project=__project_none, contexts=[], notes="", waiting=False, complete=False):
        Base.__init__(self, title)
        self.project = project
        self.contexts = contexts
        self.notes = notes
        self.waiting = waiting
        self.complete = complete
        # FIXME: how do we connect this to the "NoneProject"
        if self.project:
            print "Task project is: ", self.project
            self.project.add_task(self)
        GTD().sig_project_added(self)

    def set_title(self, title):
        Base.set_title(self, title)
        GTD().sig_task_renamed(self)

    def add_context(self, context):
        if self.contexts.count(context) == 0:
            self.contexts.append(context)

    def remove_context(self, context):
        if self.contexts.count(context):
            self.contexts.remove(context)

# Placeholder class for "Click to create new task..." type items in lists
# Perhaps this is better placed in the gui code, rather than here...
class NewTask(object):
    def __init__(self, title_str):
        self.__title = title_str

    def create_new_task(self, title):
        new_task = Task(title)

    title = property(lambda s: s.__title, create_new_task)
    project = property(lambda s: None)
    contexts = property(lambda s: [])
    notes = property(lambda s: "")
    waiting = property(lambda s: False)
    complete = property(lambda s: False)


# The top-level GTD tree
class GTD(object):
    __metaclass__ = Singleton

    def __init__(self, filename):
        __realm_none = Realm("None", True)
        __area_none = Area("None", self.realm_none)
        __project_none = Project("None", "", self.area_project)
        self.contexts = []
        self.realms = [__realm_none]

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

    def load_test_data(self):
        # load test data
        self.contexts = [
            Context("Evening"),
            Context("Weekend"),
            Context("Errands"),
            Context("Online"),
            Context("Computer"),
            Context("Calls")]
        self.realms = [Realm("Personal"), Realm("Professional")]
        remodel = Area("Remodel", self.realms[0])
        staffdev = Area("Staff Development", self.realms[1])
        braindump = Project("BrainDump", "", staffdev, False)
        deck = Project("front deck", "", remodel, False)
        Task("research gnome list_item", braindump, [self.contexts[3]], "notes A", False, False),
        Task("extend gnome list_item", braindump, [self.contexts[3]], "notes B", False, False),
        Task("lay deck boards", deck, [self.contexts[1]], "use stained boards first", False, False)
    
    def context_tasks(self, context):
        tasks = []
        for r in self.realms:
            if r.visible:
                for t in r.get_tasks():
                    if t.contexts.count(context):
                        tasks.append(t)
        return tasks


def save(tree, filename):
    print "saving tree to %s\n" % filename
    f = open(filename, 'w')
    pickle.dump(tree, f)
    f.close()


def load(filename):
    print "opening tree from %s\n" % filename
    f = open(filename, 'r')
    tree = pickle.load(f)
    f.close()
    return tree


