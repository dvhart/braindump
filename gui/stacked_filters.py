#    Filename: stacked_treeview.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: A treeview with multiple models, and button to select each one
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
# 2008-Oct-07:	Initial version by Darren Hart <darren@dvhart.com>

from gobject import *
import gtk, gtk.glade
from widgets import *
from logging import debug, info, warning, error, critical

class ExpanderButton(WidgetWrapper):
    def __init__(self, name, child, expanded=False):
        # FIXME: verify the type of widget, should be a button with an
        # arrow as the 0th child
        WidgetWrapper.__init__(self, name)
        self._child = child
        self._arrow = self.widget.get_child().get_children()[0]
        self.set_expanded(expanded)
        self.widget.connect("clicked", self._on_clicked)

    def _on_clicked(self, widget):
        self.set_expanded(not self._expanded)

    def get_expanded(self):
        return self._expanded

    def set_expanded(self, expanded):
        self._expanded = expanded
        if self._expanded:
            self._child.show()
            self._arrow.set(gtk.ARROW_DOWN, gtk.SHADOW_NONE)
        else:
            self._child.hide()
            self._arrow.set(gtk.ARROW_RIGHT, gtk.SHADOW_NONE)


class StackedFilters(WidgetWrapper):
    """ A TreeView with multiple models, and a button to select each one

    We're basically a Mediator for all the widgets that comprise the stacked
    filters sidebar.
    """
    __gsignals__ = {'changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, ())}

    def __init__(self, name, context_model, project_model, area_model):
        WidgetWrapper.__init__(self, name)

        cfw = GUI().get_widget("context_filter_window").widget
        self.__context_button = ExpanderButton("context_filter", cfw, False)
        self.__context_filter_clear = GUI().get_widget("context_filter_clear")
        self.__context_filter_list = FilterListView("context_filter_list")
        self.__context_filter_list.widget.set_model(context_model.model_filter)
        self.__context_filter_list.widget.get_selection().connect("changed",
            self._on_selection_changed, self.__context_filter_clear)
        self.__context_filter_clear.widget.connect("clicked", self._on_filter_clear_clicked,
            self.__context_filter_list)

        pfw = GUI().get_widget("project_filter_window").widget
        self.__project_button = ExpanderButton("project_filter", pfw, False)
        self.__project_filter_clear = GUI().get_widget("project_filter_clear")
        self.__project_filter_list = FilterListView("project_filter_list")
        self.__project_filter_list.widget.set_model(project_model.model_filter)
        self.__project_filter_list.widget.get_selection().connect("changed",
            self._on_selection_changed, self.__project_filter_clear)
        self.__project_filter_clear.widget.connect("clicked", self._on_filter_clear_clicked,
            self.__project_filter_list)

        afw = GUI().get_widget("area_filter_window").widget
        self.__area_button = ExpanderButton("area_filter", afw, False)
        self.__area_filter_clear = GUI().get_widget("area_filter_clear")
        self.__area_filter_list = FilterListView("area_filter_list")
        self.__area_filter_list.widget.set_model(area_model.model_filter)
        self.__area_filter_list.widget.get_selection().connect("changed",
            self._on_selection_changed, self.__area_filter_clear)
        self.__area_filter_clear.widget.connect("clicked", self._on_filter_clear_clicked,
            self.__area_filter_list)

        # FIXME: there is one global selection_match function, but we can be smarter about it now
        # that we have separate filter lists for contexts, projects, and areas
        self.filter = AndFilter()
        self.filter.append(Filter(self.__context_filter_list.selection_match))
        self.filter.append(Filter(self.__project_filter_list.selection_match))
        self.filter.append(Filter(self.__area_filter_list.selection_match))

    def _on_selection_changed(self, selection, clear_button):
        if selection.count_selected_rows() > 0:
            clear_button.widget.set_sensitive(True)
        else:
            clear_button.widget.set_sensitive(False)
        self.emit("changed")

    def _on_filter_clear_clicked(self, button, list):
        list.widget.get_selection().unselect_all()
        button.set_sensitive(False)
