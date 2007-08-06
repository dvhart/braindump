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

class Base(object):
    def __init__(self, title):
        self.title = title


class Context(Base):
    def __init__(self, title):
        self.tasks = []
        Base.__init__(self, title)

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, task):
        self.tasks.remove(task)


class Realm(Base):
    def __init__(self, title, visible=True):
        self.areas = []
        self.visible = visible
        Base.__init__(self, title)

    def add_area(self, area):
        self.areas.append(area)

    def remove_area(self, area):
        self.areas.remove(area)

    def set_visible(self, visible):
        self.visible = visible
        print self.title + " visibility = " + str(visible)


class Area(Base):
    def __init__(self, title, realm):
        self.projects = []
        Base.__init__(self, title)
        self.realm = realm
        self.realm.add_area(self)

    def add_project(self, project):
        self.projects.append(project)

    def remove_project(self, project):
        self.projects.remove(project)


class Project(Base):
    def __init__(self, title, notes, area, state):
        self.tasks = []
        Base.__init__(self, title)
        self.notes = notes
        self.area = area
        self.state = state # ie: complete, someday
        self.area.add_project(self)

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, task):
        self.tasks.remove(task)


class Task(Base):
    def __init__(self, title, project, contexts, notes, state):
        Base.__init__(self, title)
        self.project = project
        self.contexts = contexts
        self.notes = notes
        self.state = state # ie: next, waiting, complete
        self.project.add_task(self)
        for context in contexts:
            context.add_task(self)


class Tree(object):
    def __init__(self):
        self.contexts = []
        self.realms = []

        # load test data
        self.contexts = [
            Context("Evening"),
            Context("Weekend"),
            Context("Errands"),
            Context("Online"),
            Context("Computer"),
            Context("Calls")]
        self.realms = [Realm("Personal"), Realm("Professional")]
        staffdev = Area("Remodel", self.realms[0])
        staffdev = Area("Staff Development", self.realms[1])
        pydo = Project("pydo", "", staffdev, 0)
        deck = Project("front deck", "", staffdev, 0)
        Task("research gnome list_item", pydo, [self.contexts[3]], "notes A", 0),
        Task("extend gnome list_item", deck, [self.contexts[3]], "notes B", 0),
        Task("lay deck boards", deck, [self.contexts[1]], "use stained boards first", 0)
    
    # FIXME: the datastructure should be revisited after a usage analysis and these functions
    # can then be optimized
    def context_tasks(self, context):
        tasks = []
        for t in self.tasks:
            if t.contexts.count(context):
                tasks.append(t)
        return tasks

    def project_tasks(self, project):
        tasks = []
        for t in self.tasks:
            if t.project == project:
                tasks.append(t)
        return tasks
        return self.tasks


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

