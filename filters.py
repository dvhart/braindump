#    Filename: filters.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: boolean filter logic for filtered gtk datastores
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
# 2008-Sep-18:	Initial version by Darren Hart <darren@dvhart.com>

import logging

from logging import debug, info, warning, error, critical


class Filter(object):

    def __init__(self, callback):
        self.__callback = callback # FIXME: is this valid? or do I need self?

    def filter(self, model, iter):
        debug("__callback: %s" % (self.__callback))
        return self.__callback(model, iter)


# FIXME: how do we create abstract base classes?
class AggregateFilter(Filter):
    def __init__(self):
        self._filters = []

    def append(self, filter):
        self._filters.append(filter)


    def extend(self, filter_list):
        self._filters.extend(filter_list)

    def remove(self, filter):
        if self._filters.count(filter):
            self._filters.remove(filter)
        else:
            debug("filter not in _filters: %s" % (filter))

    def clear(self):
        self._filters = []

    def filter(self, model, iter):
        critical("this is an abstract base class")


class OrFilter(AggregateFilter):
    def __init__(self):
        AggregateFilter.__init__(self)

    def filter(self, model, iter):
        if len(self._filters) == 0:
            return True

        for f in self._filters:
            if f.filter(model, iter):
                return True
        return False


class AndFilter(AggregateFilter):
    def __init__(self):
        AggregateFilter.__init__(self)

    def filter(self, model, iter):
        debug("len(filters): %d" % (len(self._filters)))
        if len(self._filters) == 0:
            return True

        for f in self._filters:
            debug("%s" % (f))
            if not f.filter(model, iter):
                return False
        return True
