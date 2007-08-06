#    Filename: gtd_tree.py
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

class base(object):
    def __init__(self, title):
        self.title = title

    def set_visible(visible):
        self.visible = visible


class context(base):
    def __init__(self, title):
        self.tasks = []
        base.__init__(self, title)

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, task):
        self.tasks.remove(task)


class realm(base):
    def __init__(self, title):
        self.areas = []
        self.visible = True
        base.__init__(self, title)

    def add_area(self, area):
        self.areas.append(area)

    def remove_area(self, area):
        self.areas.remove(area)

    def set_visible(self, visible):
        self.visible = visible
        print self.title + " visibility = " + str(visible)


class area(base):
    def __init__(self, title, realm):
        self.projects = []
        base.__init__(self, title)
        self.realm = realm
        self.realm.add_area(self)

    def add_project(self, project):
        self.projects.append(project)

    def remove_project(self, project):
        self.projects.remove(project)


class project(base):
    def __init__(self, title, notes, area, state):
        self.tasks = []
        base.__init__(self, title)
        self.notes = notes
        self.area = area
        self.state = state # ie: complete, someday
        self.area.add_project(self)

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, task):
        self.tasks.remove(task)


class task(base):
    def __init__(self, title, project, contexts, notes, state):
        base.__init__(self, title)
        self.project = project
        self.contexts = contexts
        self.notes = notes
        self.state = state # ie: next, waiting, complete
        self.project.add_task(self)
        for context in contexts:
            context.add_task(self)


class gtd_tree(object):
    def __init__(self):
        self.contexts = []
        self.realms = []

        # load test data
        self.contexts = [
            context("Evening"),
            context("Weekend"),
            context("Errands"),
            context("Online"),
            context("Computer"),
            context("Calls")]
        self.realms = [realm("Personal"), realm("Professional")]
        staffdev = area("Remodel", self.realms[0])
        staffdev = area("Staff Development", self.realms[1])
        pydo = project("pydo", "", staffdev, 0)
        deck = project("front deck", "", staffdev, 0)
        task("research gnome list_item", pydo, [self.contexts[3]], "notes A", 0),
        task("extend gnome list_item", deck, [self.contexts[3]], "notes B", 0),
        task("lay deck boards", deck, [self.contexts[1]], "use stained boards first", 0)
    
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


