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

import gtk, gtk.glade
from singleton import *
import gtd
from gui_datastores import *


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
            print 'ERROR: widgets{' + name + '} already registered - OVERWRITING!'
        print 'Registering widgets{' + name + '} as ' + str(wrapped_widget)
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


class RealmToggles(WidgetWrapper):
    """A toolbar for toggling realm visibility"""

    __realm_buttons = {}

    def __init__(self, name):
        """Construct a toolbar for toggling realm visibility.

        Keyword arguments:
        widget -- an empty gtk.Toolbar
        """
        # FIXME: check for widget type: gtk.Toolbar and 0 children
        WidgetWrapper.__init__(self, name)
        for realm in GTD().realms:
            self.on_realm_added(realm)
        GTD().sig_realm_added.connect(self.on_realm_added)
        GTD().sig_realm_renamed.connect(self.on_realm_renamed)
        GTD().sig_realm_removed.connect(self.on_realm_removed)

    def _on_toggled(self, widget, realm):
        realm.set_visible(widget.get_active())

    # FIXME: alpha order?
    def on_realm_added(self, realm):
        """Add a gtk.ToggleToolButton for realm."""
        # FIXME: check it doesn't already exist
        tb = gtk.ToggleToolButton()
        tb.set_property("label", realm.title)
        tb.set_active(realm.visible)
        tb.connect("toggled", self._on_toggled, realm)
        tb.show()
        self.widget.insert(tb, 0)
        self.__realm_buttons[realm] = tb

    # FIXME: alpha reorder?
    def on_realm_renamed(self, realm):
        """Update the label of the button corresponding to realm."""
        if self.__realm_buttons.has_key(realm):
            self.__realm_buttons[realm].set_property("label", realm.title)
        # FIXME: throw exception if not?

    def on_realm_removed(self, realm):
        """Remove the button corresponding to realm."""
        if self.__realm_buttons.has_key(realm):
            self.widget.remove(self.__realm_buttons[realm])
            del self.__realm_buttons[realm]


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

    def __init__(self, name, context_store, project_store):
        """Construct a treeview for contexts and projects.

        Keyword arguments:
        widget        -- the gtk.TreeView widget to wrap
        context_store -- the ContextStore for gtd.Contexts
        project_store -- the ProjectStore fot gtd.Projects
        """
        GTDTreeView.__init__(self, name)
        self.__context_store = context_store
        self.__project_store = project_store
        # FIXME: which model should we do first?
        self.widget.set_model(self.__context_store)

        # setup the column and cell renderer
        tvcolumn0 = gtk.TreeViewColumn()
        cell0 = gtk.CellRendererText()
        cell0.set_property('editable', True)
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

    def on_task_filter_list_button_press(self, widget, event):
        return GTDTreeView.on_button_press(self, widget, event, 0)

    def on_task_filterby_changed(self, widget):
        """Update the model according to the selected filter.

        Keywork arguments:
        widget -- A gtk.ComboBox with active text of either
                  "By Context" or "By Project"
        """
        filter_by = widget.get_active_text()
        if filter_by == "By Context":
            self.widget.set_model(self.__context_store)
        elif filter_by == "By Project":
            self.widget.set_model(self.__project_store)

    def on_task_filter_all(self, widget):
        """Select all the rows in the view."""
        self.widget.get_selection().select_all()

    def on_task_filter_none(self, widget):
        """Select none of the rows in the view."""
        self.widget.get_selection().unselect_all()
        # FIXME: should select (No Context) or (No Project)
        # never allow viewing no tasks at all (will cause problems creating 
        # new tasks as they will just vanish from the view)


class TaskListView(GTDTreeView):
    """A treeview to display tasks.
    
    Public members variables:
    follow_new -- whether or not to jump to a newly created task
    """
    
    __new_task_handler = None
    follow_new = True

    def __init__(self, name, task_store, new_task_handler):
        """Construct a treeview for tasks.

        Keyword arguments:
        widget     -- the gtk.TreeView widget to wrap
        task_store -- the TaskStore for gtd.Tasks
        """
        GTDTreeView.__init__(self, name)
        self.__new_task_handler = new_task_handler
        self.widget.set_model(task_store)
        task_store.connect("row_inserted", self._on_row_inserted)

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
            print "ERROR: didn't set %s property for "%data, obj.title

    # gtk signal callbacks (defined in and connected via Glade)
    def on_task_list_button_press(self, widget, event):
        return GTDTreeView.on_button_press(self, widget, event, 1)

    # FIXME: this should connect to a TaskForm.set_task(task)
    # FIXME: application logic
    def on_task_list_cursor_changed(self, tree):
        path = tree.get_cursor()[0]
        task = tree.get_model()[path][0]
        if task:
            notes = ""
            contexts = []
            project = None
            if isinstance(task, GTDActionRow):
                GUI().get_widget("task_details_form").widget.set_sensitive(False)
            else:
                GUI().get_widget("task_details_form").widget.set_sensitive(True)
                notes = task.notes
                contexts = task.contexts
                project = task.project
            GUI().get_widget("task_notes").widget.get_buffer().set_text(notes)
            GUI().get_widget("task_contexts_table").set_active_contexts(contexts)
            GUI().get_widget("task_project").set_active(project)


class AreaFilterListView(GTDTreeView):
    def __init__(self, name, area_store):
        GTDTreeView.__init__(self, name)
        self.widget.set_model(area_store)

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

    def on_area_filter_all(self, widget):
        self.widget.get_selection().select_all()

    def on_area_filter_none(self, widget):
        self.widget.get_selection().unselect_all()


class ProjectListView(GTDTreeView):
    def __init__(self, name, project_store):
        GTDTreeView.__init__(self, name)
        self.widget.set_model(project_store)
        project_store.connect("row_inserted", self._on_row_inserted)

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
            Project(new_text)
        else:
            project.title = new_text

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
            print "ERROR: didn't set %s property for "%data, obj.title

    def _on_row_inserted(self, model, path, iter):
        self.widget.set_cursor(path, None, False)

    # gtk signal callbacks (defined in and connected via Glade)
    def on_project_list_button_press(self, widget, event):
        return GTDTreeView.on_button_press(self, widget, event, 1)

    # FIXME: this should connect to a ProjectForm.set_project(project)
    # FIXME: application logic
    def on_project_list_cursor_changed(self, tree):
        path = tree.get_cursor()[0]
        project = tree.get_model()[path][0]
        notes = ""
        area = None
        if isinstance(project, gtd.Project):
            GUI().get_widget("project_details_form").widget.set_sensitive(True)
            notes = project.notes
            area = project.area
        else:
            GUI().get_widget("project_details_form").widget.set_sensitive(False)
        GUI().get_widget("project_notes").widget.get_buffer().set_text(notes)
        GUI().get_widget("project_area").set_active(area)


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

    def _on_edited(self, cell, path, new_text, model_lambda, column):
        obj = model_lambda()[path][0]
        if obj:
            obj.title = new_text

    def _data_func(self, column, cell, model, iter, data):
        obj = model[iter][0]
        if data is "title":
            title = obj.title
            if isinstance(obj, GTDActionRow) or isinstance(obj, gtd.BaseNone):
                title = "<i>"+title+"</i>"
            cell.set_property("markup", title)
        else:
            # FIXME: throw an exception
            print "ERROR: didn't set %s property for "%data, obj.title

    def on_realms_and_areas_button_press(self, widget, event):
        return GTDTreeView.on_button_press(self, widget, event, 0)


# Class aggregrating GtkTable to list contexts for tasks
# FIXME: find a way to use Shrink=No on the hbox in the hpaned
#        now this widget won't shrink (reduce cols) once they get added
#        so it basically ratchets wider with now way of shrinking.  But
#        if Shrink=Yes, then we can get widget clipping which looks bad.
class ContextTable(WidgetWrapper):
    __context_cbs = {}
    __max_width = 0
    __last_allocation = None
    __on_toggled = None

    def __init__(self, name, toggle_handler):
        WidgetWrapper.__init__(self, name)
        self.__on_toggled = toggle_handler
        self.__table = gtk.Table()
        self.widget.add(self.__table)
        self.__table.show()
        for context in GTD().contexts:
            self.on_context_added(context)
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
 

class GTDCombo(WidgetWrapper):
    __none = None

    def __init__(self, name, model, none=None):
        WidgetWrapper.__init__(self, name)
        self.__none = none
        print "model is ", model.__class__
        self.widget.set_model(model)
        model.connect("row_changed", lambda m,p,i: self.widget.queue_draw)
        renderer = gtk.CellRendererText()
        self.widget.pack_start(renderer)
        self.widget.set_cell_data_func(renderer, self._data_func)
        self.widget.set_active(-1)

    def _data_func(self, column, cell, model, iter):
        obj = model[iter][0]
        if isinstance(obj, gtd.Base):
            cell.set_property("text", obj.title)
        else:
            # FIXME: throw an exception
            print "ERROR: obj is not a gtd.Base: ", obj.__class__
            
    def get_active(self):
        iter = self.widget.get_active_iter()
        if iter:
            return self.widget.get_model()[iter][0]
        else:
            return self.__none

    def set_active(self, obj):
        iter = self.gtd_iter(obj)
        if iter:
            return self.widget.set_active_iter(iter)
        else:
            return self.widget.set_active(-1)

    def gtd_iter(self, obj):
        model = self.widget.get_model()
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == obj:
                return iter
            iter = model.iter_next(iter)
        return None


class GTDRowPopup(WidgetWrapper):
    __tree_view = None
    __edit_col = 0

    def __init__(self, name):
        WidgetWrapper.__init__(self, name)
    
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
            print "ERROR: unknown object:", obj.__class__

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
