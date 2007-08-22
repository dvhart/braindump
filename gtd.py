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
        Base.__init__(self, title)


class Realm(Base):
    def __init__(self, title, visible=True):
        self.areas = []
        self.visible = visible
        Base.__init__(self, title)

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
        print self.title + " visibility = " + str(visible)


class Area(Base):
    def __init__(self, title, realm):
        self.projects = []
        Base.__init__(self, title)
        self.realm = realm
        self.realm.add_area(self)

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
    def __init__(self, title, project=None, contexts=[], notes="", waiting=False, complete=False):
        Base.__init__(self, title)
        self.project = project
        self.contexts = contexts
        self.notes = notes
        self.waiting = waiting
        self.complete = complete
        # FIXME: how do we connect this to the "NoneProject"
        if project:
            self.project.add_task(self)

    def add_context(self, context):
        if self.contexts.count(context) == 0:
            self.contexts.append(context)

    def remove_context(self, context):
        if self.contexts.count(context):
            self.contexts.remove(context)


class Tree(object):
    def __init__(self):
        self.contexts = []
        self.realms = []
        self.event_listeners = {
            "realm_visible_changed":[],
            "project_renamed":[],
            "project_added":[],
            "project_removed":[]
        }

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
        Task("research gnome list_item", pydo, [self.contexts[3]], "notes A", False, False),
        Task("extend gnome list_item", deck, [self.contexts[3]], "notes B", False, False),
        Task("lay deck boards", deck, [self.contexts[1]], "use stained boards first", False, False)
    
    def context_tasks(self, context):
        tasks = []
        for r in self.realms:
            if r.visible:
                for t in r.get_tasks():
                    if t.contexts.count(context):
                        tasks.append(t)
        return tasks

    def notify(self, event):
        for listener in self.event_listeners[event]:
            if event == "realm_visible_changed":
                listener.event()


# TreeListener Interface
# FIXME: throw an exception rather than pass
class TreeListener(object):
    def __init__(self):
        pass
    def on_realm_visible_changed(self, realm):
        pass
    def on_project_renamed(self, project):
        pass
    def on_project_added(self, project):
        pass
    def on_project_remove(self, project):
        pass


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


