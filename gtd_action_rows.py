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
from logging import debug, info, warning, error, critical

# Abstract base class for simple type comparison in Tree|List View code
class GTDActionRow(object):
    def __init__(self, title):
        self.__title = title

    def set_title(self, title):
        pass

    title = OProperty(lambda s: s.__title, set_title)


class NewContext(GTDActionRow):
    def __init__(self, title):
        GTDActionRow.__init__(self, title)

    # When our title is changed by the user, we just create a new context and emit the signal
    def set_title(self, title):
        if not title == self.title:
            context = Context(title)


class NewRealm(GTDActionRow):
    def __init__(self, title):
        GTDActionRow.__init__(self, title)

    def set_title(self, title):
        if not title == self.title:
            realm = Realm(title)


class NewArea(GTDActionRow):
    def __init__(self, title, realm=RealmNone()):
        GTDActionRow.__init__(self, title)
        self.realm = realm

    def set_title(self, title):
        if not title == self.title:
            area = Area(title, self.realm)


class NewProject(GTDActionRow):
    def __init__(self, title):
        GTDActionRow.__init__(self, title)

    def set_title(self, title):
        if not title == self.title:
            project = Project(title)


class NewTask(GTDActionRow):
    def __init__(self, title):
        GTDActionRow.__init__(self, title)

    def set_title(self, title):
        if not title == self.title:
            task = Task(title)
