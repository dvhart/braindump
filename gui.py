#    Filename: gui.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: gtd customized widgets and glade xml singleton
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

import time
import datetime
import re
import gtk, gtk.glade
import gnome, gnome.ui
import sexy
from singleton import *
import gtd
from gui_datastores import *
from gtd_action_rows import *
from logging import debug, info, warning, error, critical

class GUI(gtk.glade.XML):
    """Singleton wrapper to gtk.glade.XML"""

    __metaclass__ = GSingleton
    __widgets = {}

    def __init__(self, file="", widget=None):
        """Construct the GUI singleton.

        Keyword arguments:
        file   -- the glade file
        widget -- the widget to use for the top of the returned tree (default None)
        """
        self.file = file
        gtk.glade.XML.__init__(self, self.file, widget)

    def __get_widget(self, name):
        return _WidgetWrapperBase(name)

    def _get_gtk_widget(self, name):
        return gtk.glade.XML.get_widget(self, name)

    def register_widget(self, wrapped_widget):
        """Register a wrapped widget.

        To be called from WidgetWrapper derived classes in the __init__ routine
        so the WrappedWidget can be looked up by name later.
        """
        name = wrapped_widget.widget.get_name()
        if self.__widgets.has_key(name):
            # FIXME: throw a proper exception
            error('widgets{%s} already registered - OVERWRITING!' % (name))
        debug('Registering widgets{%s} as %s' % (name, wrapped_widget.__class__.__name__))
        self.__widgets[wrapped_widget.widget.get_name()] = wrapped_widget

    # Return the wrapped widget if it exists, create one for consistent usage if not
    def get_widget(self, name):
        """Return the wrapped widget keyed by name."""
        widget = None
        if self.__widgets.has_key(name):
            widget = self.__widgets[name]
            if widget == None:
                self.__widgets.remove(name)
                widget = self.__get_widget(name)
        else:
            widget = self.__get_widget(name)
        return widget


class _WidgetWrapperBase(object):
    """Base class for wrapped gtk widgets

    This is only used by the GUI class to return unregistered gtk widgets.
    """

    def __init__(self, name):
        self.widget = GUI()._get_gtk_widget(name)


class WidgetWrapper(_WidgetWrapperBase):
    """Wrapper for gtk widgets, automates signal connections."""

    def __init__(self, name):
        """Construct a wrapped widget and autoconnect signal handlers.

        Keyword arguments:
        widget -- a gtk.Widget
        """
        _WidgetWrapperBase.__init__(self, name)
        GUI().register_widget(self)
        # Note: this requires globally unique signal names
        #       move this into the GUI class and use a subtree
        #       xml object (from widget.name) if we want individual
        #       widget signal namespace
        GUI().signal_autoconnect(self)


# Elements for list stores (used in combo boxes)
class FilterItem(object):
    def __init__(self, name, filter):
        self.name = name
        self.filter = filter


class ModelItem(object):
    def __init__(self, name, model):
        self.name = name
        self.model = model


class RealmCheckToolButton(gtk.ToolItem):
    def __init__(self, realm, callback):
        gtk.ToolItem.__init__(self)
        self.__realm = realm
        self.__align = gtk.Alignment(0.5, 0.5, 0, 0)
        self.__align.set_padding(0, 0, 6, 6)
        self.__cb = gtk.CheckButton(realm.title)
        self.__cb.set_active(realm.visible)
        self.__cb.connect("toggled", callback, realm)
        self.__align.add(self.__cb)
        self.add(self.__align)
        self.show_all()

    def update(self):
        self.__cb.set_label(self.__realm.title)

    def show(self):
        self.__cb.set_active(True)


class RealmToggles(WidgetWrapper):
    """A toolbar for toggling realm visibility"""

    def __init__(self, name):
        """Construct a toolbar for toggling realm visibility.

        Keyword arguments:
        widget -- an empty gtk.Toolbar
        """
        # FIXME: check for widget type: gtk.Toolbar and 0 children
        WidgetWrapper.__init__(self, name)
        self.__realm_buttons = {}
        ti = gtk.ToolItem()
        label = gtk.Label("Show Realms:")
        label.set_padding(6, 0)
        ti.add(label)
        self.widget.add(ti)
        ti.show_all()
        for r in GTD().realms:
            self.add_realm(r)
        GTD().sig_realm_added.connect(self.add_realm)
        GTD().sig_realm_renamed.connect(self.update_realm)
        GTD().sig_realm_removed.connect(self.remove_realm)

    def _on_toggled(self, widget, realm):
        realm.set_visible(widget.get_active())

    # FIXME: alpha order?
    def add_realm(self, realm):
        """Add a button for realm to the toolbar."""
        if self.__realm_buttons.has_key(realm):
            debug("realm already present")
            return
        # don't display the RealmNone, it is always visible
        if isinstance(realm, gtd.RealmNone):
            return
        cb = RealmCheckToolButton(realm, self._on_toggled)
        self.widget.add(cb)
        self.__realm_buttons[realm] = cb

    # FIXME: alpha reorder?
    def update_realm(self, realm):
        """Update the label of the button corresponding to realm."""
        if self.__realm_buttons.has_key(realm):
            self.__realm_buttons[realm].update()
        # FIXME: throw exception if not?

    def remove_realm(self, realm):
        """Remove the button corresponding to realm."""
        if self.__realm_buttons.has_key(realm):
            self.widget.remove(self.__realm_buttons[realm])
            del self.__realm_buttons[realm]

    def show_all(self):
        for realm in self.__realm_buttons.keys():
            self.__realm_buttons[realm].show()


class GTDTreeView(WidgetWrapper):
    def __init__(self, name):
        WidgetWrapper.__init__(self, name)

    def get_current(self):
        """Return the current gtd object"""
        path = self.widget.get_cursor()[0]
        if path:
            obj = self.widget.get_model()[path][0]
        else:
            return None
        return obj

    def on_button_press(self, widget, event, col):
        """Display the popup menu when the right mouse button is pressed.

        Keyword arguments:
        widget -- the gtk.Menu to display
        event  -- the gtk event that caused the signal to be emitted
        """

        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3 \
           and not isinstance(self.get_current(), GTDActionRow) \
           and not isinstance(self.get_current(), BaseNone):
            # FIXME: this is really not type safe, the widget isn't tested to be a GTDPopupMenu
            popup = GUI().get_widget(widget.get_name()) 
            popup.set_tree_and_col(self, self.widget.get_column(col))
            widget.popup(None, None, None, event.button, event.time)
            return True
        return False


# FIXME: consider renaming this to not use "Filter" as this class
# doesn't do the filtering, it's selection is used for that purpose
# by the application.
class TaskFilterListView(GTDTreeView):
    """A treeview to display contexts or projects."""

    def __init__(self, name):
        """Construct a treeview for contexts and projects.

        Keyword arguments:
        widget        -- the gtk.TreeView widget to wrap
        """
        GTDTreeView.__init__(self, name)

        # setup the column and cell renderer
        tvcolumn0 = gtk.TreeViewColumn()
        cell0 = gtk.CellRendererText()
        cell0.set_property('editable', True)
        # FIXME: consdider passing None as model, we don't need to pass it to ourselves...
        cell0.connect('edited', self._on_edited, lambda: self.widget.get_model(), 0)
        tvcolumn0.pack_start(cell0, False)
        tvcolumn0.set_cell_data_func(cell0, self._data_func)
        self.widget.append_column(tvcolumn0)

        # setup selection modes and callback
        self.widget.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.widget.set_rubber_banding(True)

    def _on_edited(self, cell, path, new_text, model_lambda, column):
        model_lambda()[path][column].title = new_text

    def _data_func(self, column, cell, model, iter):
        obj = model[iter][0]
        title = obj.title
        if isinstance(obj, GTDActionRow) or isinstance(obj, gtd.BaseNone):
            title = "<i>"+title+"</i>"
        cell.set_property("markup", title)

    def selection_match(self, task):
        if isinstance(task, GTDActionRow):
            return True

        selection = self.widget.get_selection()
        selmodel, paths = selection.get_selected_rows()

        # FIXME: is this still relevant
        if task is None:
            debug('FIXME: why are we comparing a none task?')
            return False

        if task.project.area.realm.visible:
            for path in paths:
                comp = selmodel[path][0] # either a project or a context
                if isinstance(comp, gtd.Context):
                    if task.contexts.count(comp):
                        return True
                    if len(task.contexts) is 0 and isinstance(comp, gtd.ContextNone):
                        return True
                elif isinstance(comp, gtd.Project):
                    if task.project is comp:
                        return True
                elif isinstance(comp, GTDActionRow):
                    continue
                else:
                    error('cannot filter Task on %s' % (comp.__class__.__name__))
            return False

    # FIXME: we could connect this ourselves in __init__, but we don't have
    # access to the menu here... glade does this via the xml...... ew.....
    def on_task_filter_list_button_press(self, widget, event):
        return GTDTreeView.on_button_press(self, widget, event, 0)


class TaskListView(GTDTreeView):
    """A treeview to display tasks.
    
    Public members variables:
    follow_new -- whether or not to jump to a newly created task
    """
    
    def __init__(self, name, task_store, new_task_handler):
        """Construct a treeview for tasks.

        Keyword arguments:
        widget     -- the gtk.TreeView widget to wrap
        task_store -- the TaskStore for gtd.Tasks
        """
        GTDTreeView.__init__(self, name)
        self.follow_new = True

        self.__new_task_handler = new_task_handler
        self.widget.set_model(task_store.model_filter)
        task_store.model_filter.connect("row_inserted", self._on_row_inserted)
        task_store.model_filter.connect("row_deleted", self._on_row_deleted)

        # create the TreeViewColumns to display the data
        tvcolumn0 = gtk.TreeViewColumn("Done")
        tvcolumn1 = gtk.TreeViewColumn("Title")

        # append the columns to the view
        self.widget.append_column(tvcolumn0)
        self.widget.append_column(tvcolumn1)

        # create the CellRenderers
        cell0 = gtk.CellRendererToggle()
        cell0.connect('toggled', self._on_toggled, self.widget.get_model(), 0)
        cell1 = gtk.CellRendererText()
        cell1.set_property('editable', True)
        cell1.connect('edited', self._on_edited, lambda: self.widget.get_model(), 1)

        # attach the CellRenderers to each column
        tvcolumn0.pack_start(cell0) # expand True by default
        tvcolumn1.pack_start(cell1)

        # display data directly from the gtd object, rather than setting attributes
        tvcolumn0.set_cell_data_func(cell0, self._data_func, "complete")
        tvcolumn1.set_cell_data_func(cell1, self._data_func, "title")

        # make it searchable
        self.widget.set_search_column(1)

    def _on_toggled(self, cell, path, model, column):
        complete = model[path][column]
        task = model[path][0]
        if isinstance(task, gtd.Task):
            task.complete = not task.complete

    def _on_edited(self, cell, path, new_text, model_lambda, column):
        task = model_lambda()[path][0]
        if isinstance(task, NewTask):
            if not task.title == new_text:
                self.__new_task_handler(new_text)
        else:
            task.title = new_text

    def _on_row_inserted(self, model, path, iter):
        if (self.follow_new):
            self.widget.set_cursor(path, None, True)

    def _on_row_deleted(self, model, path):
        if self.widget.get_cursor()[0] is None:
            self.widget.set_cursor((0)) # FIXME: ideally we would just emit the cursor-changed
                                        # signal when the current row was deleted... but for some
                                        # reason this doesn't happen...

    def _data_func(self, column, cell, model, iter, data):
        task = model[iter][0]
        if data is "complete":
            if isinstance(task, GTDActionRow):
                cell.set_property("inconsistent", True)
            else:
                cell.set_property("active", task.complete)
                cell.set_property("inconsistent", False)
        elif data is "title":
            title = task.title
            if isinstance(task, GTDActionRow):
                title = "<i>"+title+"</i>"
            cell.set_property("markup", title)
        else:
            # FIXME: throw an exception
            error('ERROR: didn\'t set %s property for %s' % (data, obj.title))

    # gtk signal callbacks (defined in and connected via Glade)
    # FIXME: can't do this in _init_ since glade is passing in the menu
    # to  display (widget)
    def on_task_list_button_press(self, widget, event):
        return GTDTreeView.on_button_press(self, widget, event, 1)


class AreaFilterListView(GTDTreeView):
    def __init__(self, name, area_store):
        GTDTreeView.__init__(self, name)
        self.widget.set_model(area_store.model_filter)

        # setup the column and cell renderer
        tvcolumn0 = gtk.TreeViewColumn()
        cell0 = gtk.CellRendererText()
        cell0.set_property('editable', True)
        cell0.connect('edited', self._on_edited, lambda: self.widget.get_model(), 0)
        tvcolumn0.pack_start(cell0, False)
        tvcolumn0.set_cell_data_func(cell0, self._data_func, "data")
        self.widget.append_column(tvcolumn0)

        # setup selection modes and callback
        self.widget.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.widget.set_rubber_banding(True)

    def _on_edited(self, cell, path, new_text, model_lambda, column):
        model_lambda()[path][column].title = new_text

    def _data_func(self, column, cell, model, iter, data):
        area = model[iter][0]
        title = area.title
        if isinstance(area, GTDActionRow) or isinstance(area, gtd.BaseNone):
            title = "<i>"+title+"</i>"
        cell.set_property("markup", title)

    # signal callbacks
    def on_area_filter_list_button_press(self, widget, event):
        return GTDTreeView.on_button_press(self, widget, event, 0)

    def selection_match(self, project):
        selection = self.widget.get_selection()
        selmodel, paths = selection.get_selected_rows()
        if project == None:
            return True

        if isinstance(project, GTDActionRow):
            return True

        for path in paths:
            if project.area is selmodel[path][0]:
                return True

        return False


class ProjectListView(GTDTreeView):
    def __init__(self, name, project_store):
        GTDTreeView.__init__(self, name)
        self.widget.set_model(project_store.model_filter)
        project_store.model_filter.connect("row_inserted", self._on_row_inserted)
        project_store.model_filter.connect("row_deleted", self._on_row_deleted)

        # create the TreeViewColumns to display the data
        tvcolumn0 = gtk.TreeViewColumn("Done")
        tvcolumn1 = gtk.TreeViewColumn("Title")
        tvcolumn2 = gtk.TreeViewColumn("Tasks")

        # append the columns to the view
        self.widget.append_column(tvcolumn0)
        self.widget.append_column(tvcolumn1)
        self.widget.append_column(tvcolumn2)

        # create the CellRenderers
        cell0 = gtk.CellRendererToggle()
        cell0.connect('toggled', self._on_toggled, self.widget.get_model(), 0)
        cell1 = gtk.CellRendererText()
        cell1.set_property('editable', True)
        cell1.connect('edited', self._on_edited, lambda: self.widget.get_model(), 1)
        cell2 = gtk.CellRendererText()

        # attach the CellRenderers to each column
        tvcolumn0.pack_start(cell0, False)
        tvcolumn1.pack_start(cell1) # expand True by default
        tvcolumn2.pack_start(cell2, False)

        # display data directly from the gtd object, rather than setting attributes
        tvcolumn0.set_cell_data_func(cell0, self._data_func, "complete")
        tvcolumn1.set_cell_data_func(cell1, self._data_func, "title")
        tvcolumn2.set_cell_data_func(cell2, self._data_func, "tasks")

        # make it searchable
        self.widget.set_search_column(1)

    def _on_toggled(self, cell, path, model, column):
        complete = model[path][column]
        project = model[path][0]
        if isinstance(project, gtd.Project):
            project.complete = not project.complete

    def _on_edited(self, cell, path, new_text, model_lambda, column):
        project = model_lambda()[path][0]
        if project.title == new_text:
            return
        if isinstance(project, NewProject):
            # FIXME: NewProject can do this itself...
            Project(None, new_text)
        else:
            project.title = new_text

    def _on_row_inserted(self, model, path, iter):
        self.widget.set_cursor(path, None, False)

    def _on_row_deleted(self, model, path):
        if self.widget.get_cursor()[0] is None:
            self.widget.set_cursor((0)) # FIXME: ideally we would just emit the cursor-changed
                                        # signal when the current row was deleted... but for some
                                        # reason this doesn't happen...

    def _data_func(self, column, cell, model, iter, data):
        project = model[iter][0]
        if data is "complete":
            if isinstance(project, gtd.Project):
                cell.set_property("active", project.complete)
                cell.set_property("inconsistent", False)
            else:
                cell.set_property("inconsistent", True)
        elif data is "title":
            title = project.title
            if isinstance(project, GTDActionRow):
                title = "<i>"+title+"</i>"
            cell.set_property("markup", title)
        elif data is "tasks":
            if isinstance(project, gtd.Project):
                cell.set_property("markup", len(project.tasks))
            else:
                cell.set_property("markup", "")
        else:
            # FIXME: throw an exception
            error('ERROR: didn\'t set %s property for %s' % (data, obj.title))

    # gtk signal callbacks (defined in and connected via Glade)
    def on_project_list_button_press(self, widget, event):
        return GTDTreeView.on_button_press(self, widget, event, 1)


class RealmAreaTreeView(GTDTreeView):
    def __init__(self, name, realm_area_store):
        GTDTreeView.__init__(self, name)
        self.widget.set_model(realm_area_store)

        tvcolumn = gtk.TreeViewColumn("Title")
        cell = gtk.CellRendererText()
        cell.set_property('editable', True)
        cell.connect('edited', self._on_edited, lambda: self.widget.get_model(), 1)
        tvcolumn.pack_start(cell)
        tvcolumn.set_cell_data_func(cell, self._data_func, "title")
        self.widget.append_column(tvcolumn)

        self.widget.expand_all()
        self.widget.get_model().connect('row_inserted', self._on_row_inserted)

    def _on_edited(self, cell, path, new_text, model_lambda, column):
        obj = model_lambda()[path][0]
        if obj:
            obj.title = new_text

    def _on_row_inserted(self, model, path, iter):
        # We have to wait for a child to be added, otherwise there
        # is nothing to expand, so here we are expanding the path
        # of the Area (or the CreateArea) under the new Realm
        if (len(path) >= 2):
            ret = self.widget.expand_to_path(path)

    def _data_func(self, column, cell, model, iter, data):
        obj = model[iter][0]
        if data is "title":
            title = obj.title
            if isinstance(obj, GTDActionRow) or isinstance(obj, gtd.BaseNone):
                title = "<i>"+title+"</i>"
            cell.set_property("markup", title)
        else:
            # FIXME: throw an exception
            error('ERROR: didn\'t set %s property for %s' % (data, obj.title))

    def on_realms_and_areas_button_press(self, widget, event):
        return GTDTreeView.on_button_press(self, widget, event, 0)


# Class aggregrating GtkTable to list contexts for tasks
# FIXME: find a way to use Shrink=No on the hbox in the hpaned
#        now this widget won't shrink (reduce cols) once they get added
#        so it basically ratchets wider with now way of shrinking.  But
#        if Shrink=Yes, then we can get widget clipping which looks bad.
# FIXME: use names like "add_context()" rather than signal names
class ContextTable(WidgetWrapper):

    def __init__(self, name, toggle_handler):
        WidgetWrapper.__init__(self, name)
        self.__on_toggled = toggle_handler
        self.__table = gtk.Table()
        self.__context_cbs = {}
        self.__max_width = 0
        self.__last_allocation = None

        self.widget.add(self.__table)
        self.__table.show()
        for c in GTD().contexts:
            if not isinstance(c, gtd.ContextNone):
                self.on_context_added(c)
        # FIXME: decide if this should be connected outside of the widget...
        GTD().sig_context_added.connect(self.on_context_added)
        GTD().sig_context_renamed.connect(self.on_context_renamed)
        GTD().sig_context_removed.connect(self.on_context_removed)

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

    def set_active_contexts(self, contexts):
        for c, cb in self.__context_cbs.iteritems():
            cb.set_property("active", c in contexts)

    def uncheck_all(self):
        for c, cb in self.__context_cbs.iteritems():
            cb.set_property("active", False)

    # FIXME: this doesn't appear to be adequate
    def on_context_renamed(self, context):
        if self.__context_cbs.has_key(context):
            self.__context_cbs[context].set_label(context.title)
        self.__rebuild(self.widget.allocation)

    def on_context_added(self, context):
        cb = gtk.CheckButton(context.title)
        cb.connect("toggled", self.__on_toggled, context)
        self.__context_cbs[context] = cb
        self.__max_width = max(self.__max_width, cb.size_request()[0])
        self.__rebuild(self.widget.allocation, True)

    def on_context_removed(self, context):
        if self.__context_cbs.has_key(context):
            del self.__context_cbs[context]
        self.__rebuild(self.widget.allocation, True)
 

class ModelCombo(WidgetWrapper):
    def __init__(self, name, model, none=None):
        WidgetWrapper.__init__(self, name)
        self.__none = none
        debug('%s model is %s' % (name, model.__class__.__name__))
        self.widget.set_model(model)
        renderer = gtk.CellRendererText()
        self.widget.pack_start(renderer)
        self.widget.set_cell_data_func(renderer, self._data_func)

    def _data_func(self, column, cell, model, iter):
        mi = model[iter][0]
        cell.set_property("text", mi.name)

    def get_active(self):
        iter = self.widget.get_active_iter()
        if iter:
            return self.widget.get_model()[iter][0]
        else:
            return None


# FIXME: bad name... I think...
class GTDFilterCombo(WidgetWrapper):
    def __init__(self, name, model):
        WidgetWrapper.__init__(self, name)
        debug('%s model is %s' % (name, model.__class__.__name__))
        self.widget.set_model(model)
        renderer = gtk.CellRendererText()
        self.widget.pack_start(renderer)
        self.widget.set_cell_data_func(renderer, self._data_func)

    def _data_func(self, column, cell, model, iter):
        filter_item = model[iter][0]
        cell.set_property("text", filter_item.name)

    def get_active(self):
        iter = self.widget.get_active_iter()
        if iter:
            return self.widget.get_model()[iter][0]
        else:
            return FilterItem("", lambda x: True)

    # FIXME: oh come on, isn't there a better name?!?! filter is WAY overloaded!
    def filter(self, obj):
        filter_item = self.get_active()
        return filter_item.filter(obj)


class GTDCombo(WidgetWrapper):

    def __init__(self, name, model, none=None):
        WidgetWrapper.__init__(self, name)
        self.__none = none
        debug('%s model is %s' % (name, model.__class__.__name__))
        self.widget.set_model(model.model_filter)
        model.model_filter.connect("row_changed", lambda m,p,i: self.widget.queue_draw)
        renderer = gtk.CellRendererText()
        self.widget.pack_start(renderer)
        self.widget.set_cell_data_func(renderer, self._data_func)

    def _data_func(self, column, cell, model, iter):
        obj = model[iter][0]
        if isinstance(obj, gtd.Base) or isinstance(obj, GTDActionRow):
            cell.set_property("text", obj.title)
        else:
            # FIXME: throw an exception
            error('obj is not a gtd.Base: %s' % (obj.__class__.__name__))
            
    def get_active(self):
        iter = self.widget.get_active_iter()
        if iter:
            return self.widget.get_model()[iter][0]
        else:
            return self.__none

    def set_active(self, obj):
        iter = self.gtd_iter(obj)
         # FIXME: this feels like a hack... but not sure how to deal with the combo not having
         # been updated yet...
        if not iter:
            debug("***obj.title not found, refiltering model in case it hasn't been updated yet...")
            self.widget.get_model().refilter()
            iter = self.gtd_iter(obj)
        if iter:
            return self.widget.set_active_iter(iter)
        else:
            return self.widget.set_active(0)

    def gtd_iter(self, obj):
        model = self.widget.get_model()
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == obj:
                return iter
            iter = model.iter_next(iter)
        return None


class GTDRowPopup(WidgetWrapper):

    def __init__(self, name):
        WidgetWrapper.__init__(self, name)
        self.__tree_view = None
        self.__edit_col = 0
    
    # gtk signal callbacks (defined in and connected via Glade)
    def on_gtd_row_popup_rename(self, widget):
        obj = self.__tree_view.get_current()
        path,col = self.__tree_view.widget.get_cursor()
        self.__tree_view.widget.set_cursor(path, self.__edit_col, True)

    def on_gtd_row_popup_delete(self, widget):
        # FIXME: implement the remove path in the GTD tree
        obj = self.__tree_view.get_current()
        recurse = False # FIXME: need a dialog?
        if isinstance(obj, Context):
            GTD().remove_context(obj)
        elif isinstance(obj, Realm):
            GTD().remove_realm(obj, recurse)
        elif isinstance(obj, Area):
            GTD().remove_area(obj, recurse)
        elif isinstance(obj, Project):
            GTD().remove_project(obj, recurse)
        elif isinstance(obj, Task):
            GTD().remove_task(obj)
        else:
            error('unknown object for gtd_row_popup: %s' % (obj.__class__.__name___))

    def set_tree_and_col(self, tree_view, column):
        self.__tree_view = tree_view
        self.__edit_col = column
        obj = self.__tree_view.get_current()
        show_delete = not ((isinstance(obj, Area) and obj.realm == RealmNone()) or \
           (isinstance(obj, Project) and obj.area == AreaNone()) or \
           (isinstance(obj, Task) and obj.project == ProjectNone()))
        GUI().get_widget("gtd_row_popup_delete").widget.set_sensitive(show_delete)


class AboutDialog(WidgetWrapper):
    def __init__(self, name):
        WidgetWrapper.__init__(self, name)

    def on_about_dialog_delete(self, dialog, event):
        self.widget.hide()
        return True

    def on_about_dialog_response(self, dialog, response):
        if response == gtk.RESPONSE_CANCEL:
            self.widget.hide()


class RealmAreaDialog(WidgetWrapper):
    def __init__(self, name, realm_area_store):
        WidgetWrapper.__init__(self, name)
        self.realm_area_store = realm_area_store
        # FIXME: too much knowledge of other widgets... sort of.  Without glade we would be creating these
        #        but this implementation ties this new widget to a specific glade file.... hmmmm
        self.realm_area_tree = RealmAreaTreeView("realm_area_tree", self.realm_area_store.model)

    def on_realm_area_dialog_delete(self, dialog, event):
        self.widget.hide()
        return True

    def on_realm_area_dialog_response(self, dialog, response):
        if response == gtk.RESPONSE_OK:
            self.widget.hide()


# FIXME: too much application knowledge embedded here (GTD signals and other widgets) ?
class TaskDetailsForm(WidgetWrapper):

    def __init__(self, name, project_store):
        WidgetWrapper.__init__(self, name)
        self.__task_notes = GUI().get_widget("task_notes")
        self.__start = GUI().get_widget("task_start")
        self.__due = GUI().get_widget("task_due")
        self.__task_project = GTDCombo("task_project", project_store, ProjectNone())
        self.__task_contexts = ContextTable("task_contexts_table", self.on_context_toggled)
        self.__task = None

        self.__task_notes.widget.get_buffer().connect("changed", self.on_task_notes_changed)

    def set_task(self, task):
        self.__task = task
        notes = ""
        start_date = 0 # FIXME: this sets it to today()... we really want blank... (3 others like this)
        due_date = 0
        project = None
        contexts = []

        if isinstance(task, gtd.Task):
            self.widget.set_sensitive(True)
            notes = self.__task.notes
            # FIXME: might be better to wrap the widget so we can simply use datetime objects here
            if self.__task.start_date:
                start_date = int(time.mktime(self.__task.start_date.timetuple()))
            if self.__task.due_date:
                due_date = int(time.mktime(self.__task.due_date.timetuple()))
            project = self.__task.project
            contexts = self.__task.contexts
        else:
            self.widget.set_sensitive(False)

        self.__task_notes.widget.get_buffer().set_text(notes)
        self.__start.widget.set_time(start_date)
        self.__due.widget.set_time(due_date)
        self.__task_project.set_active(project)
        self.__task_contexts.set_active_contexts(contexts)

    def refresh(self):
        self.set_task(self.__task)

    def get_project(self):
        return self.__task_project.get_active()

    def on_task_notes_changed(self, buffer):
        if isinstance(self.__task, gtd.Task):
            self.__task.notes = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())

    def on_task_start_date_changed(self, dateedit):
        d = datetime.datetime.fromtimestamp(dateedit.get_time())
        self.__task.start_date = d
        debug(d)

    def on_task_due_date_changed(self, dateedit):
        d = datetime.datetime.fromtimestamp(dateedit.get_time())
        self.__task.due_date = d
        debug(d)

    def on_task_project_changed(self, project_combo):
        project = self.get_project()
        if isinstance(self.__task, gtd.Task) and not self.__task.project == project :
            self.__task.project.remove_task(self.__task)
            if isinstance(project, gtd.Project):
                project.add_task(self.__task)
            self.__task.project = project

    def on_context_toggled(self, context_checkbox, context):
        if isinstance(self.__task, gtd.Task):
            if context_checkbox.get_active():
                self.__task.add_context(context)
            else:
                self.__task.remove_context(context)


# FIXME: too much application knowledge embedded here (GTD signals and other widgets) ?
class ProjectDetailsForm(WidgetWrapper):

    def __init__(self, name, area_store):
        WidgetWrapper.__init__(self, name)
        self.__project_notes = GUI().get_widget("project_notes")
        self.__start = GUI().get_widget("project_start")
        self.__due = GUI().get_widget("project_due")
        self.__project_area = GTDCombo("project_area", area_store, AreaNone())
        self.__project = None

        self.__project_notes.widget.get_buffer().connect("changed", self.on_project_notes_changed)

    def set_project(self, project): # FIXME: consider just using an attribute?
        self.__project = project
        notes = ""
        start_date = 0
        due_date = 0
        area = None

        if isinstance(self.__project, gtd.Project):
            self.widget.set_sensitive(True)
            notes = self.__project.notes
            # FIXME: might be better to wrap the widget so we can simply use datetime objects here
            if self.__project.start_date:
                start_date = int(time.mktime(self.__project.start_date.timetuple()))
            if self.__project.due_date:
                due_date = int(time.mktime(self.__project.due_date.timetuple()))
            area = self.__project.area
        else:
            self.widget.set_sensitive(False)

        self.__project_notes.widget.get_buffer().set_text(notes)
        self.__start.widget.set_time(start_date)
        self.__due.widget.set_time(due_date)
        self.__project_area.set_active(area)

    def refresh(self):
        self.set_project(self.__project)

    def get_area(self):
        return self.__project_area.get_active()

    def on_project_notes_changed(self, buffer):
        if isinstance(self.__project, gtd.Project):
            self.__project.notes = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())

    def on_project_start_date_changed(self, dateedit):
        d = datetime.datetime.fromtimestamp(dateedit.get_time())
        self.__project.start_date = d
        debug(d)

    def on_project_due_date_changed(self, dateedit):
        d = datetime.datetime.fromtimestamp(dateedit.get_time())
        self.__project.due_date = d
        debug(d)

    def on_project_area_changed(self, area_combo):
        area = self.get_area()
        debug("%s" % (area.title))
        if isinstance(self.__project, gtd.Project) and not self.__project.area == area:
            self.__project.area.remove_project(self.__project)
            if isinstance(area, gtd.Area):
                area.add_project(self.__project)
            self.__project.area = area

class SearchEntry(WidgetWrapper):

    def __init__(self, name):
        WidgetWrapper.__init__(self, name)
        self.__alignment = GUI().get_widget(name)
        self.__entry = sexy.IconEntry()
        self.__active = False # FIXME: we could just have search_string... either a string or none... same detail, more useful...
        self.__focused = False # we should be able to check this right?
        self.__hint = "Search..."

        self.__entry.add_clear_button()
        self.__entry.connect("icon-released", self.clear)
        self.__entry.connect("focus-in-event", self._focus_in)
        self.__entry.connect("focus-out-event", self._focus_out)
        self.__entry.connect("changed", self._changed)
        self.__entry.show()
        self.__alignment.widget.add(self.__entry)
        self._focus_out(self.__entry, None)

    def _focus_in(self, widget, event):
        debug("focused")
        self.__focused = True
        if not self.__active:
            self.__entry.set_text("")
            self.__entry.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))

    def _focus_out(self, widget, event):
        debug("unfocused")
        self.__focused = False
        if self.__entry.get_text() is "":
            self.clear(widget)

    def _changed(self, widget):
        search_string = self.__entry.get_text()
        debug("changed '%s'" % (search_string))
        if search_string == "" or search_string == self.__hint:
            self.__active = False
        else:
            self.__active = True

    def connect(self, signal, handler):
        self.__entry.connect(signal, handler)

    def clear(self, widget, x=1, y=1):
        debug("cleared")
        if self.__focused is False:
            self.__entry.set_text(self.__hint)
            self.__entry.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse("gray"))

    def search(self, obj):
        if isinstance(obj, GTDActionRow):
            return True

        if not isinstance(obj, gtd.Base):
            return False

        if self.__active:
            return re.compile(self.__entry.get_text(), re.I).search(obj.title)

        return True

