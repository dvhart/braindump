#    Filename: gtd_action_rows.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: Actionable gtd objects for use in datastores
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
# Copyright (C) Darren Hart, 2008
#
# 2008-Mar-30:	Initial version by Darren Hart <darren@dvhart.com>

from gtd import *

class NewContext(Context):
    def __init__(self, title):
        Context.__init__(self, title)

    # When our title is changed by the user, we just create a new context and emit the signal
    def set_title(self, title):
        if not title == self.title:
            context = Context(title)


class NewRealm(Realm):
    def __init__(self, title):
        Realm.__init__(self, title, False)

    def set_title(self, title):
        if not title == self.title:
            realm = Realm(title)

    def add_area(self, area):
        print "Oops, trying to add area to a", self.__class__

    def set_visible(self, visible):
        print "Oops, trying to change visibility of a", self.__class__


class NewArea(Area):
    def __init__(self, title):
        Area.__init__(self, title) # FIXME: hrm... should realm be None... or a special "VisibleRealm" ?

    def set_title(self, title):
        if not title == self.title:
            area = Area(title)

    def add_project(self, project):
        print "Oops, trying to add project to a", self.__class__


class NewProject(Project):
    def __init__(self, title):
        Project.__init__(self, title)

    def set_title(self, title):
        if not title == self.title:
            project = Project(title)

    def add_task(self, task):
        print "Oops, trying to add task to a", self.__class__

    def remove_task(self, task):
        self.tasks.remove(task)


class NewTask(Task):
    def __init__(self, title):
        Task.__init__(self, title)

    def set_title(self, title):
        if not title == self.title:
            task = Task(title)

    def add_context(self, context):
        print "Oops, trying to add context to a", self.__class__


