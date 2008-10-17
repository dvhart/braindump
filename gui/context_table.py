#    Filename: context_table.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: Resizable table of context checkboxes
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
# Copyright (C) Darren Hart, 2007-2008
#
# 2007-Jun-30:	Initial version by Darren Hart <darren@dvhart.com>

from gobject import *
import gtk
from widgets import *
import gtd
from logging import debug, info, warning, error, critical

# FIXME: find a way to use Shrink=No on the hbox in the hpaned
#        now this widget won't shrink (reduce cols) once they get added
#        so it basically ratchets wider with now way of shrinking.  But
#        if Shrink=Yes, then we can get widget clipping which looks bad.
# FIXME: use names like "add_context()" rather than signal names

class ContextTable(WidgetWrapper):
    """ Resizable table of context checkboxes """

    # send the context and a boolean representing its checked state
    __gsignals__ = {'changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT, TYPE_PYOBJECT))}

    def __init__(self, name):
        WidgetWrapper.__init__(self, name)
        self.__table = gtk.Table()
        self.__table.set_homogeneous(False)
        self.__context_cbs = {}
        self.__max_width = 0
        self.__last_allocation = None

        self.widget.add(self.__table)
        self.__table.show()
        for c in GTD().contexts:
            if not isinstance(c, gtd.ContextNone):
                self.add_context(c)
        # FIXME: decide if this should be connected outside of the widget...
        GTD().connect("context_added", lambda g,o: self.add_context(o))
        GTD().connect("context_renamed", lambda g,o: self.update_context(o))
        GTD().connect("context_removed", lambda g,o: self.remove_context(o))

    def __rebuild(self, allocation, force=False):
        cols = max(1, min(allocation.width / (self.__max_width+5), len(self.__context_cbs)))
        rows = max(1, len(self.__context_cbs)/cols)
        if len(self.__context_cbs) % cols:
            rows = rows + 1

        if (force or self.__table.get_property("n-columns") != cols or
            self.__table.get_property("n-rows") != rows):
            self.__table.set_size_request(cols*(self.__max_width+5), -1)
            for cb in self.__table.get_children():
                self.__table.remove(cb)
            self.__table.resize(rows, cols)
            i=0
            for c, cb in self.__context_cbs.iteritems():
                x = i % cols
                y = i / cols
                self.__table.attach(cb, x, x+1, y, y+1)
                cb.show()
                i = i + 1

    def on_size_allocate(self, widget, allocation):
        if self.__last_allocation and allocation.width == self.__last_allocation.width:
            return
        self.__last_allocation = allocation
        self.__rebuild(allocation)
        self.widget.get_parent().queue_draw()

    def set_active_contexts(self, contexts):
        for c, cb in self.__context_cbs.iteritems():
            cb.set_property("active", c in contexts)

    def uncheck_all(self):
        for c, cb in self.__context_cbs.iteritems():
            cb.set_property("active", False)

    # FIXME: this doesn't appear to be adequate
    def update_context(self, context):
        if self.__context_cbs.has_key(context):
            self.__context_cbs[context].set_label(context.title)
        self.__rebuild(self.widget.allocation)

    def add_context(self, context):
        cb = gtk.CheckButton(context.title)
        cb.connect("toggled", lambda w: self.emit("changed", context, w.get_active()))
        self.__context_cbs[context] = cb
        self.__max_width = max(self.__max_width, cb.size_request()[0])
        self.__rebuild(self.widget.allocation, True)

    def remove_context(self, context):
        if self.__context_cbs.has_key(context):
            del self.__context_cbs[context]
        self.__rebuild(self.widget.allocation, True)


