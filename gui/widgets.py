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

import os, sys
from fnmatch import fnmatch
from string import *
import time
import datetime
import re
from gobject import *
import gtk, gtk.glade
import gnome, gnome.ui
import webbrowser
from braindump.singleton import *
import braindump.gtd
from braindump.gui_datastores import *
from braindump.gtd_action_rows import *
from friendly_date import *
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

        # Setup the about url handler before the widgets are created
        gtk.about_dialog_set_url_hook(lambda dia,url: (webbrowser.open(url)))

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


class _WidgetWrapperBase(gobject.GObject):
    """Base class for wrapped gtk widgets

    This is only used by the GUI class to return unregistered gtk widgets.
    """

    def __init__(self, name):
        gobject.GObject.__init__(self)
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
        GTD().connect("realm_added", lambda g,o: self.add_realm(o))
        GTD().connect("realm_modified", lambda g,o: self.update_realm(o))
        GTD().connect("realm_removed", lambda g,o: self.remove_realm(o))

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


# FIXME: I believe we can eliminate this class eventually...
class GTDTreeViewBase(WidgetWrapper):
    def __init__(self, name, title_column=0):
        WidgetWrapper.__init__(self, name)
        self.__title_column = title_column

        menu = GUI().get_widget("gtd_row_popup")
        self.widget.connect_object_after("event-after", self._on_button_press, menu)

        # setup the title column and cell renderer
        title_col = gtk.TreeViewColumn()
        title_cell = gtk.CellRendererText()
        title_cell.set_property('editable', True)
        # FIXME: consdider passing None as model, we don't need to pass it to ourselves...
        title_cell.connect('edited', self._on_title_edited)
        title_col.pack_start(title_cell, False)
        title_col.set_cell_data_func(title_cell, self._data_func, "title")
        self.widget.append_column(title_col)

    def _data_func(self, column, cell, model, iter, data):
        if data == "title":
            obj = model.get_value(iter, 0)
            title = markup_escape_text(obj.title)
            if isinstance(obj, gtd.Actionable) and obj.complete:
                title = "<s>"+title+"</s>"
            elif isinstance(obj, GTDActionRow) or isinstance(obj, gtd.BaseNone):
                title = "<i>"+title+"</i>"
            cell.set_property("markup", title)
            return True
        return False

    def _on_button_press(self, popup, event):
        """Display the popup menu when the right mouse button is pressed.

        Keyword arguments:
        widget -- the gtk.Menu to display
        event  -- the gtk event that caused the signal to be emitted
        """
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3 \
           and not isinstance(self.get_current(), GTDActionRow) \
           and not isinstance(self.get_current(), BaseNone):
            # FIXME: this is really not type safe, the widget isn't tested to be a GTDPopupMenu
            #popup = GUI().get_widget(widget.get_name())
            popup.set_tree_and_col(self, self.widget.get_column(self.__title_column))
            popup.widget.popup(None, None, None, event.button, event.time)
            return True
        return False

    def _on_title_edited(self, cell, path, new_text):
        self.widget.get_model()[path][0].title = new_text

    def get_current(self):
        """Return the current gtd object"""
        path = self.widget.get_cursor()[0]
        if path:
            obj = self.widget.get_model()[path][0]
        else:
            return None
        return obj

    def get_gtd_from_path(self, path):
        """Return the gtd object at path"""
        model = self.widget.get_model()
        obj = model.get_value(model.get_iter(path), 0)
        return obj

    def get_gtd_from_iter(self, iter):
        """Return the gtd object at path"""
        model = self.widget.get_model()
        obj = model.get_value(iter, 0)
        return obj


# FIXME: consider renaming this to not use "Filter" as this class
# doesn't do the filtering, it's selection is used for that purpose
# by the application.
class FilterListView(GTDTreeViewBase):
    """A treeview to display contexts, projects, or areas."""

    def __init__(self, name):
        """Construct a treeview for contexts and projects.

        Keyword arguments:
        widget        -- the gtk.TreeView widget to wrap
        """
        GTDTreeViewBase.__init__(self, name)

        # setup selection modes and callback
        self.widget.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.widget.set_rubber_banding(True)

    def selection_match(self, model, iter):
        obj = model[iter][0]
        if isinstance(obj, GTDActionRow):
            return True

        selection = self.widget.get_selection()
        selmodel, paths = selection.get_selected_rows()

        # Don't filter if nothing is selected or if the "Create new context..." item is selected
        if len(paths) == 0:
            return True
        elif len(paths) == 1:
            if isinstance(selmodel[paths[0]][0], GTDActionRow):
                return True

        if isinstance(obj, gtd.Task):
            for path in paths:
                comp = selmodel[path][0] # project, context, or area

                if isinstance(comp, gtd.ContextNone):
                    if len(obj.contexts) is 0:
                        return True
                elif isinstance(comp, gtd.Context):
                    if comp in obj.contexts:
                        return True
                elif isinstance(comp, gtd.Project) or isinstance(comp, gtd.ProjectNone):
                    if obj.project is comp:
                        return True
                elif isinstance(comp, gtd.Area) or isinstance(comp, gtd.AreaNone):
                    if obj.project.area is comp:
                        return True
                elif isinstance(comp, GTDActionRow):
                    continue
                else:
                    info('cannot filter Task on %s' % (comp.__class__.__name__))
                    return True
        elif isinstance(obj, gtd.Project):
            for path in paths:
                comp = selmodel[path][0] # either a project or a context
                if isinstance(comp, gtd.Area) or isinstance(comp, gtd.AreaNone):
                    if obj.area is selmodel[path][0]:
                        return True
                else:
                    info('cannot filter Project on %s' % (comp.__class__.__name__))
                    return True

        return False


class GTDListView(GTDTreeViewBase):
    """A treeview to display tasks and projects.

    Public members variables:
    follow_new -- whether or not to jump to a newly created gtd object
    """

    # FIXME: we should get this from settings
    __countdown_timeout = 2

    # FIXME: should be ables to remove the store from the constructor
    # as we will use several for this tree throughout the use of the program
    # setup the callbacks from the caller
    def __init__(self, name, task_store, new_task_handler, new_project_handler,
                 img_path):
        """Construct a treeview for tasks and projects.

        Keyword arguments:
        widget     -- the gtk.TreeView widget to wrap
        task_store -- the TaskStore for gtd.Tasks
        """
        GTDTreeViewBase.__init__(self, name, 1)
        self.follow_new = True
        self.show_completed = False

        self.colors = {}
        self.colors[None]                         = "#FFFFFF"
        self.colors[gtd.Actionable.INITIAL] = "#FFFFFF"
        self.colors[gtd.Actionable.OVERDUE] = "#E0B6AF"
        self.colors[gtd.Actionable.DUE]     = "#E0B6AF"
        self.colors[gtd.Actionable.ACTIVE]  = "#FFFFFF"
        #self.colors[gtd.Actionable.UPCOMING] = "#EED680"
        #self.colors[gtd.Actionable.UPCOMING] = "#FFEDAE"
        self.colors[gtd.Actionable.UPCOMING] = "#FFF3C7"
        self.colors[gtd.Actionable.FUTURE]   = "#FFFFFF"
        self.colors[gtd.Actionable.SOMEDAY]  = "#FFFFFF"
        self.colors[gtd.Actionable.COMPLETE] = "#FFFFFF"

        self.img_path = img_path
        self.__countdown_pixbufs = {}
        self._load_countdown_pixbufs()

        self.__new_task_handler = new_task_handler
        self.__new_project_handler = new_project_handler
        self.widget.set_model(task_store.model_filter)
        task_store.model_filter.connect("row_inserted", lambda m,p,i: self._on_row_inserted(p, i))
        task_store.model_filter.connect("row_deleted", lambda m,p: self._on_row_deleted(p))

        # create the TreeViewColumns to display the data
        tvcolumn0 = gtk.TreeViewColumn("Done")
        tvcolumn2 = gtk.TreeViewColumn("Due")
        tvcolumn3 = gtk.TreeViewColumn("")

        # append the columns to the view
        self.widget.insert_column(tvcolumn0, 0)
        self.widget.append_column(tvcolumn2)
        self.widget.append_column(tvcolumn3)

        # create the CellRenderers
        cell0 = gtk.CellRendererToggle()
        cell0.connect('toggled', self._on_toggled)
        cell2 = gtk.CellRendererCombo()
        cell2.connect("edited", self._on_due_date_edited)
        date_model = gtk.ListStore(gobject.TYPE_STRING)
        date_model.append(["None"])
        date_model.append(["Today"])
        date_model.append(["Tomorrow"])
        date_model.append(["This Friday"])
        date_model.append(["Next Week"])
        date_model.append(["Other..."])
        cell2.set_property("model", date_model)
        cell2.set_property('editable', True)
        cell2.set_property('has-entry', False)
        cell2.set_property('text-column', 0)
        cell3 = gtk.CellRendererPixbuf()

        # attach the CellRenderers to each column
        tvcolumn0.pack_start(cell0)
        tvcolumn2.pack_start(cell2)
        tvcolumn3.pack_start(cell3)

        # display data directly from the gtd object, rather than setting attributes
        tvcolumn0.set_cell_data_func(cell0, self._data_func, "complete")
        tvcolumn2.set_cell_data_func(cell2, self._data_func, "due_date")
        tvcolumn3.set_cell_data_func(cell3, self._data_func, "countdown")

        # make it searchable
        self.widget.set_search_column(1)

    def _on_due_date_edited(self, cell, path, friendly_str):
        if friendly_str == "Other...":
            print "FIXME: Popup calendar and select date..."
        else:
            due_date = friendly_to_datetime(friendly_str)
            obj = self.get_gtd_from_path(path)
            obj.due_date = due_date

    def _load_countdown_pixbufs(self):
        for file in os.listdir(self.img_path):
            if fnmatch(file, "countdown-*.png"):
                index = atoi(file.replace("countdown-", "").replace(".png", ""))
                self.__countdown_pixbufs[index] = gtk.gdk.pixbuf_new_from_file(
                    os.path.join(self.img_path, file))

    def _on_toggled(self, cell, path):
        model = self.widget.get_model()
        obj = model[path][0]
        if isinstance(obj, gtd.Task) or isinstance(obj, gtd.Project):
            if obj.complete:
                obj.complete = None
            else:
                # note: we don't track the timeouts, so should we ever need to cancel one
                #       we'll have add something to that effect
                if not self.show_completed:
                    store = model.get_model()
                    store_path = model.convert_path_to_child_path(path)
                    store[store_path][1] = 1
                    gobject.timeout_add(self.__countdown_timeout * 1000 /
                        len(self.__countdown_pixbufs),
                        self._complete_timeout, store, store_path, obj)
                obj.complete = True

    # FIXME: if a row is added or deleted, our path may become invalid
    # we need to determine this (maybe using TreeModelGeneric models)
    # and find our path via the obj instead... yuk...
    def _complete_timeout(self, store, path, obj):
        if not obj.complete:
            return False

        frame = store[path][1]
        if frame > 0:
            store[path][1] = (frame + 1) % (len(self.__countdown_pixbufs) + 1)
            iter = store.get_iter(path)
            store.row_changed(path, iter)
            return True

        return False

    # override tree_view_base
    def _on_title_edited(self, cell, path, new_text):
        obj = self.widget.get_model()[path][0]
        if isinstance(obj, NewTask):
            if not obj.title == new_text:
                self.__new_task_handler(new_text)
        elif isinstance(obj, NewProject):
            if not obj.title == new_text:
                self.__new_project_handler(new_text)
        else:
            obj.title = new_text

    def _on_row_inserted(self, path, iter):
        if (self.follow_new):
            self.widget.set_cursor(path, None, True)

    def _on_row_deleted(self, path):
        if self.widget.get_cursor()[0] is None:
            self.widget.set_cursor((0)) # FIXME: ideally we would just emit the cursor-changed
                                        # signal when the current row was deleted... but for some
                                        # reason this doesn't happen...

    def _data_func(self, column, cell, model, iter, data):
        obj = model.get_value(iter, 0)

        # common cell formatting
        if isinstance(obj, GTDActionRow):
            cell.set_property("cell-background", self.colors[None])
        else:
            cell.set_property("cell-background", self.colors[obj.state])
            # FIXME setup the markup (bold or otherwise here as well)

        # column specific formatting
        if data is "complete":
            if isinstance(obj, GTDActionRow):
                cell.set_property("inconsistent", True)
            else:
                active = False
                if obj.complete:
                    active = True
                cell.set_property("active", active)
                cell.set_property("inconsistent", False)
        elif data is "title":
            title = markup_escape_text(obj.title)
            if isinstance(obj, GTDActionRow):
                title = "<i>"+title+"</i>"
            elif obj.complete:
                title = "<s>"+title+"</s>"
            cell.set_property("markup", title)
        elif data is "due_date":
            if isinstance(obj, gtd.Actionable) and obj.due_date:
                due_date = markup_escape_text(datetime_to_friendly(obj.due_date))
                if obj.complete:
                    due_date = "<s>"+due_date+"</s>"
            else:
                due_date = "-"
            cell.set_property("markup", due_date)
        elif data is "countdown":
            pixbuf = None
            if not self.show_completed and not isinstance(obj, GTDActionRow) and obj.complete:
                frame = model[iter][1]
                if frame > 0 and frame <= len(self.__countdown_pixbufs):
                    pixbuf = self.__countdown_pixbufs[frame - 1]
            cell.set_property("pixbuf", pixbuf)
        else:
            # FIXME: throw an exception
            error('ERROR: didn\'t set %s property for %s' % (data, obj.title))
            return False
        return True


class RealmAreaTreeView(GTDTreeViewBase):
    def __init__(self, name, realm_area_store):
        GTDTreeViewBase.__init__(self, name)
        self.widget.set_model(realm_area_store)

        self.widget.expand_all()
        self.widget.get_model().connect('row_inserted', self._on_row_inserted)

    def _on_row_inserted(self, model, path, iter):
        # We have to wait for a child to be added, otherwise there
        # is nothing to expand, so here we are expanding the path
        # of the Area (or the CreateArea) under the new Realm
        if (len(path) >= 2):
            ret = self.widget.expand_to_path(path)


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

        # Glade apparently does some setup, and binds attribute text to col 0
        # this throws gobject errors trying to convert a PyObject to a
        # chararray.
        self.widget.clear()

        self.widget.set_model(model)
        renderer = gtk.CellRendererText()
        self.widget.pack_start(renderer)
        self.widget.set_cell_data_func(renderer, self._data_func)

    def _data_func(self, column, cell, model, iter):
        filter_item = model[iter][0]
        cell.set_property("markup", markup_escape_text(filter_item.name))

    def get_active(self):
        iter = self.widget.get_active_iter()
        if iter:
            return self.widget.get_model()[iter][0]
        else:
            return FilterItem("", lambda x: True)

    # FIXME: oh come on, isn't there a better name?!?! filter is WAY overloaded!
    def filter(self, model, iter):
        filter_item = self.get_active()
        return filter_item.filter(model, iter)


class GTDCombo(WidgetWrapper):

    def __init__(self, name, model, none=None):
        WidgetWrapper.__init__(self, name)
        self.__none = none
        debug('%s model is %s' % (name, model.__class__.__name__))

        # Glade apparently does some setup, and binds attribute text to col 0
        # this throws gobject errors trying to convert a PyObject to a
        # chararray.
        self.widget.clear()

        self.widget.set_model(model.model_filter)
        model.model_filter.connect("row_changed", lambda m,p,i: self.widget.queue_draw)
        renderer = gtk.CellRendererText()
        self.widget.pack_start(renderer)
        self.widget.set_cell_data_func(renderer, self._data_func)

    def _data_func(self, column, cell, model, iter):
        obj = model[iter][0]
        if (isinstance(obj, gtd.Project) or isinstance(obj, gtd.Task)) and obj.complete:
            cell.set_property("markup", "<s>"+markup_escape_text(obj.title)+"</s>")
        elif isinstance(obj, gtd.Base) or isinstance(obj, GTDActionRow):
            cell.set_property("markup", markup_escape_text(obj.title))
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
        self.__delete = GUI().get_widget("gtd_row_popup_delete").widget

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
        show_delete = not ((isinstance(obj, Realm) and len(obj.areas)) or \
                           (isinstance(obj, Area) and len(obj.projects)) or \
                           (isinstance(obj, Project) and len(obj.tasks)))
        self.__delete.set_sensitive(show_delete)


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


class SearchEntry(WidgetWrapper):

    def __init__(self, name):
        WidgetWrapper.__init__(self, name)
        self.__active = False # FIXME: we could just have search_string... either a string or none... same detail, more useful...
        self.__focused = False # we should be able to check this right?
        self.__hint = "Search..."

        #self.set_icon_from_stock(GTK_ENTRY_ICON_SECONDARY, "Clear")

        #self.widget.connect("icon-release", self.clear)
        #self.widget.connect("focus-in-event", self._focus_in)
        #self.widget.connect("focus-out-event", self._focus_out)
        #self.widget.connect("changed", self._changed)
        self.widget.show()
        self.on_search_focus_out(self.widget, None)

    def _set_hint(self):
        self.widget.set_text(self.__hint)
        self.widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse("gray"))

    def on_search_focus_in(self, widget, event):
        debug("focused")
        self.__focused = True
        if not self.__active:
            self.widget.set_text("")
            self.widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))

    def on_search_focus_out(self, widget, event):
        debug("unfocused")
        self.__focused = False
        if self.widget.get_text() == "":
            self._set_hint()

    def on_search_changed(self, widget):
        search_string = self.widget.get_text()
        debug("changed '%s'" % (search_string))
        if search_string == "" or search_string == self.__hint:
            self.__active = False
        else:
            self.__active = True

    def connect(self, signal, handler):
        self.widget.connect(signal, handler)

    def on_search_clear(self, widget, x=1, y=1):
        debug("cleared")
        if self.__focused:
            self.widget.set_text("")
        else:
            self._set_hint()

    def search(self, model, iter):
        obj = model[iter][0]
        if isinstance(obj, GTDActionRow):
            return True

        if not isinstance(obj, gtd.Base):
            return False

        if self.__active:
            return re.compile(self.widget.get_text(), re.I).search(obj.title)

        return True

