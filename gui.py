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
        gtk_widget = gtk.glade.XML.get_widget(self, name)
        if not gtk_widget:
            print "ERROR: failed to find widget: ", name
        return _WidgetWrapperBase(gtk_widget)

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

    def __init__(self, widget):
        self.widget = widget


class WidgetWrapper(_WidgetWrapperBase):
    """Wrapper for gtk widgets, automates signal connections."""

    def __init__(self, widget):
        """Construct a wrapped widget and autoconnect signal handlers.

        Keyword arguments:
        widget -- a gtk.Widget
        """
        _WidgetWrapperBase.__init__(self, widget)
        GUI().register_widget(self)
        # Note: this requires globally unique signal names
        #       move this into the GUI class and use a subtree
        #       xml object (from widget.name) if we want individual
        #       widget signal namespace
        GUI().signal_autoconnect(self)


class RealmToggles(WidgetWrapper):
    """A toolbar for toggling realm visibility"""

    __realm_buttons = {}

    def __init__(self, widget):
        """Construct a toolbar for toggling realm visibility.

        Keyword arguments:
        widget -- an empty gtk.Toolbar
        """
        # FIXME: check for widget type: gtk.Toolbar and 0 children
        WidgetWrapper.__init__(self, widget)
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
        # FIXME: throw exception if not?


# FIXME: consider renaming this to not use "Filter" as this class
# doesn't do the filtering, it's selection is used for that purpose
# by the application.
class TaskFilterListView(WidgetWrapper):
    """A treeview to display contexts or projects."""

    def __init__(self, widget, context_store, project_store):
        """Construct a treeview for contexts and projects.

        Keyword arguments:
        widget        -- the gtk.TreeView widget to wrap
        context_store -- the ContextStore for gtd.Contexts
        project_store -- the ProjectStore fot gtd.Projects
        """
        WidgetWrapper.__init__(self, widget)
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
        task = model[iter][0]
        title = task.title
        if isinstance(task, GTDActionRow):
            title = "<i>"+title+"</i>"
        cell.set_property("markup", title)

    def get_current(self):
        """Return the current gtd.Context or gtd.Project."""
        path = self.widget.get_cursor()[0]
        obj = self.widget.get_model()[path][0]
        return obj

    def on_task_filter_list_button_press(self, widget, event):
        """Display the popup menu when the right mouse button is pressed.

        Keyword arguments:
        widget -- the gtk.Menu to display
        event  -- the gtk event that caused the signal to be emitted
        """
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            # FIXME: this is really not type safe, the widget isn't tested to be a GTDPopupMenu
            popup = GUI().get_widget(widget.get_name()) 
            popup.tree_view = self
            widget.popup(None, None, None, event.button, event.time)
            return True
        return False

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


class TaskListView(WidgetWrapper):
    """A treeview to display tasks."""

    def __init__(self, widget, task_store):
        """Construct a treeview for tasks.

        Keyword arguments:
        widget     -- the gtk.TreeView widget to wrap
        task_store -- the TaskStore for gtd.Tasks
        """
        WidgetWrapper.__init__(self, widget)
        self.widget.set_model(task_store)

        # create the TreeViewColumns to display the data
        tvcolumn0 = gtk.TreeViewColumn("Done")
        tvcolumn1 = gtk.TreeViewColumn("Title")

        # append the columns to the view
        widget.append_column(tvcolumn0)
        widget.append_column(tvcolumn1)

        # create the CellRenderers
        cell0 = gtk.CellRendererToggle()
        cell0.connect('toggled', self._on_toggled, widget.get_model(), 0)
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
        widget.set_search_column(1)

    def _on_toggled(self, cell, path, model, column):
        complete = model[path][column]
        task = model[path][0]
        if isinstance(task, gtd.Task):
            task.complete = not task.complete

    def _on_edited(self, cell, path, new_text, model_lambda, column):
        task = model_lambda()[path][0]
        if task:
            task.title = new_text

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

    def get_current(self):
        """Return the current gtd.Task."""
        task = None
        # FIXME: is this error checking necessary
        path = self.widget.get_cursor()[0]
        if path:
            task = self.widget.get_model()[path][0]
        return task

    # gtk signal callbacks (defined in and connected via Glade)
    def on_task_list_button_press(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            popup = GUI().get_widget(widget.get_name()) 
            popup.tree_view = self
            widget.popup(None, None, None, event.button, event.time)
            return True
        return False

    # FIXME: this should connect to a TaskForm.set_task(task)
    def on_task_list_cursor_changed(self, tree):
        path = tree.get_cursor()[0]
        task = tree.get_model()[path][0]
        if task:
            notes = ""
            contexts = []
            project = None
            if isinstance(task, GTDActionRow):
                GUI().get_widget("task_form_vbox").widget.set_sensitive(False)
            else:
                GUI().get_widget("task_form_vbox").widget.set_sensitive(True)
                notes = task.notes
                contexts = task.contexts
                project = task.project
            GUI().get_widget("task_notes").widget.get_buffer().set_text(notes)
            GUI().get_widget("task_contexts_table").set_active_contexts(contexts)
            GUI().get_widget("task_project").set_active(project)


class AreaFilterListView(WidgetWrapper):
    def __init__(self, widget, area_store):
        WidgetWrapper.__init__(self, widget)
        self.widget.set_model(area_store)

        # setup the column and cell renderer
        self.tvcolumn0 = gtk.TreeViewColumn()
        self.cell0 = gtk.CellRendererText()
        self.cell0.set_property('editable', True)
        self.cell0.connect('edited', self.on_filter_edited, lambda: self.widget.get_model(), 0)
        self.tvcolumn0.pack_start(self.cell0, False)
        self.tvcolumn0.set_cell_data_func(self.cell0, self.data_func, "data")
        self.widget.append_column(self.tvcolumn0)

        # setup selection modes and callback
        self.widget.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.widget.set_rubber_banding(True)

    def data_func(self, column, cell, model, iter, data):
        area = model[iter][0]
        title = area.title
        if isinstance(area, GTDActionRow):
            title = "<i>"+title+"</i>"
        cell.set_property("markup", title)

    def get_current(self):
        path = self.widget.get_cursor()[0]
        obj = self.widget.get_model()[path][0]
        return obj

    # signal callbacks
    def on_area_filter_list_button_press(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            popup = GUI().get_widget(widget.get_name()) 
            popup.tree_view = self
            widget.popup(None, None, None, event.button, event.time)
            return True
        return False

    def on_filter_edited(self, cell, path, new_text, model_lambda, column):
        model_lambda()[path][column].title = new_text

    def on_area_filter_all(self, widget):
        self.widget.get_selection().select_all()

    def on_area_filter_none(self, widget):
        self.widget.get_selection().unselect_all()
        # FIXME: should select (No Context) or (No Project)
        # never allow viewing no tasks at all (will cause problems creating
        # new tasks as they will just vanish from the view)

    # pynotify signal handlers
    def on_realm_visible_changed(self, realm):
        pass
        # FIXME: we don't actually _need_ a new method, but this is easier to read
#        self.reload()


class ProjectListView(WidgetWrapper):
    def __init__(self, widget, project_store):
        WidgetWrapper.__init__(self, widget)
        self.widget.set_model(project_store)

        # create the TreeViewColumns to display the data
        self.tvcolumn0 = gtk.TreeViewColumn("Done")
        self.tvcolumn1 = gtk.TreeViewColumn("Title")
        self.tvcolumn2 = gtk.TreeViewColumn("Tasks")

        # append the columns to the view
        widget.append_column(self.tvcolumn0)
        widget.append_column(self.tvcolumn1)
        widget.append_column(self.tvcolumn2)

        # create the CellRenderers
        self.cell0 = gtk.CellRendererToggle()
        self.cell0.connect('toggled', self._on_toggled, widget.get_model(), 0)
        self.cell1 = gtk.CellRendererText()
        self.cell1.set_property('editable', True)
        self.cell1.connect('edited', self._on_edited, lambda: self.widget.get_model(), 1)
        self.cell2 = gtk.CellRendererText()

        # attach the CellRenderers to each column
        self.tvcolumn0.pack_start(self.cell0, False)
        self.tvcolumn1.pack_start(self.cell1) # expand True by default
        self.tvcolumn1.pack_start(self.cell2, False)

        # display data directly from the gtd object, rather than setting attributes
        self.tvcolumn0.set_cell_data_func(self.cell0, self.project_data_func, "complete")
        self.tvcolumn1.set_cell_data_func(self.cell1, self.project_data_func, "title")
        # FIXME: shouldn't this next one be tvcolumn2?
        self.tvcolumn1.set_cell_data_func(self.cell2, self.project_data_func, "tasks")

        # make it searchable
        widget.set_search_column(1)

    def _on_toggled(self, cell, path, model, column):
        complete = model[path][column]
        project = model[path][0]
        if isinstance(project, gtd.Project):
            project.complete = not project.complete

    def _on_edited(self, cell, path, new_text, model_lambda, column):
        project = model_lambda()[path][0]
        if project:
            project.title = new_text

    # return the selected project
    def get_current(self):
        project = None
        # FIXME: is this error checking necessary
        path = self.widget.get_cursor()[0]
        if path:
            project = self.widget.get_model()[path][0]
        return project

    def project_data_func(self, column, cell, model, iter, data):
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

    # gtk signal callbacks (defined in and connected via Glade)
    def on_project_list_button_press(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            popup = GUI().get_widget(widget.get_name()) 
            popup.tree_view = self
            widget.popup(None, None, None, event.button, event.time)
            return True
        return False

    # FIXME: this should connect to a ProjectForm.set_project(project)
    def on_project_list_cursor_changed(self, tree):
        path = tree.get_cursor()[0]
        project = tree.get_model()[path][0]
        notes = ""
        area = None
        if isinstance(project, gtd.Project):
            GUI().get_widget("project_form_vbox").widget.set_sensitive(True)
            notes = project.notes
            area = project.area
        else:
            GUI().get_widget("project_form_vbox").widget.set_sensitive(False)
        GUI().get_widget("project_notes").widget.get_buffer().set_text(notes)
        GUI().get_widget("project_area").set_active(area)


class RealmAreaTreeView(WidgetWrapper):
    def __init__(self, widget, realm_area_store):
        WidgetWrapper.__init__(self, widget)
        self.widget.set_model(realm_area_store)

        # create the TreeViewColumn to display the data
        self.tvcolumn1 = gtk.TreeViewColumn("Title")
        self.cell1 = gtk.CellRendererText()
        self.cell1.set_property('editable', True)
        self.cell1.connect('edited', self._on_edited, lambda: self.widget.get_model(), 1)
        self.tvcolumn1.pack_start(self.cell1) # expand True by default
        self.tvcolumn1.set_cell_data_func(self.cell1, self._data_func, "title")
        widget.append_column(self.tvcolumn1)

        self.widget.expand_all()

    def _on_edited(self, cell, path, new_text, model_lambda, column):
        obj = model_lambda()[path][0]
        if obj:
            obj.title = new_text

    def _data_func(self, column, cell, model, iter, data):
        project = model[iter][0]
        if data is "title":
            title = project.title
            #FIXME: nice to have a common NewGTDElement class...
            if isinstance(project, GTDActionRow):
                title = "<i>"+title+"</i>"
            cell.set_property("markup", title)
        else:
            # FIXME: throw an exception
            print "ERROR: didn't set %s property for "%data, obj.title

    # return the gtd element of the current row
    # FIXME: all tree views should implement this (others have get_current...)
    # Perhaps make the have a base class?  All the next three functions should
    # be identical for all tree_views...
    def get_current(self):
        path = self.widget.get_cursor()[0]
        obj = self.widget.get_model()[path][0]
        return obj

    # gtk signal callbacks (defined in and connected via Glade)
    # connected to event_after, widget will be the popup menu
    # see glade signal properties for the realm_area_tree for details
    # FIXME: take advantage of the connect_object approach elsewhere
    def on_realms_and_areas_button_press(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            popup = GUI().get_widget(widget.get_name()) 
            popup.tree_view = self
            widget.popup(None, None, None, event.button, event.time)
            return True
        return False

class BrainDumpWindow(WidgetWrapper):
    def __init__(self, widget):
        WidgetWrapper.__init__(self, widget)

    # signal callbacks
    def on_window_destroy(self, widget):
        gtk.main_quit()


# Class aggregrating GtkTable to list contexts for tasks
# FIXME: find a way to use Shrink=No on the hbox in the hpaned
#        now this widget won't shrink (reduce cols) once they get added
#        so it basically ratchets wider with now way of shrinking.  But
#        if Shrink=Yes, then we can get widget clipping which looks bad.
class ContextTable(WidgetWrapper):
    __context_cbs = {}
    __max_width = 0
    __last_allocation = None

    def __init__(self, widget):
        WidgetWrapper.__init__(self, widget)
        self.__table = gtk.Table()
        widget.add(self.__table)
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

    def _on_toggled(self, widget, context):
        task = GUI().get_widget("task_list").get_current()
        if isinstance(task, Task):
            if widget.get_active():
                task.add_context(context)
            else:
                task.remove_context(context)

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

    # FIXME: both the old an dthe new show up in the table
    def on_context_renamed(self, context):
        if self.__context_cbs.has_key(context):
            self.__context_cbs[context].set_label(context.title)
        self.__rebuild(self.widget.allocation)

    def on_context_added(self, context):
        cb = gtk.CheckButton(context.title)
        cb.connect("toggled", self._on_toggled, context)
        self.__context_cbs[context] = cb
        self.__max_width = max(self.__max_width, cb.size_request()[0])
        self.__rebuild(self.widget.allocation, True)

    def on_context_removed(self, context):
        if self.__context_cbs.has_key(context):
            self.__context_cbs.remove(context)
        self.__rebuild(self.widget.allocation, True)
 

# add all projects to the project combo box
# FIXME: consider project listeners
# we need to be able update when projects are added or removed, and when selected realms change
# and when projects change which realm they pertain to
class ProjectCombo(WidgetWrapper):
    def __init__(self, widget, model):
        WidgetWrapper.__init__(self, widget)
 
        renderer = gtk.CellRendererText()
        self.widget.pack_start(renderer)
        self.widget.set_cell_data_func(renderer, self._data_func)
        self.widget.set_model(model)
        self.widget.set_active(0)

    def _data_func(self, column, cell, model, iter):
        project = model[iter][0]
        cell.set_property("text", project.title)
            
    def get_active(self):
        iter = self.widget.get_active_iter()
        if iter:
            return self.widget.get_model()[iter][0]
        else:
            return None

    def set_active(self, project):
        iter = self.project_iter(project)
        if iter:
            return self.widget.set_active_iter(iter)
        else:
            return self.widget.set_active(-1)

    # return the iter, or None, corresponding to "project"
    # consider a more consistent function name (with gtk names)
    # like get_iter_from_project
    # FIXME: If we use generic stores, then we either have to
    # to do this method here, or we store the wrapped class for reference...
    # the latter might be preferable
    def project_iter(self, project):
        model = self.widget.get_model()
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == project:
                return iter
            iter = model.iter_next(iter)
        return None

    # FIXME: control logic should be elsewhere?
    def on_task_project_changed(self, task_list):
        task = GUI().get_widget(task_list.name).get_current()
        project = self.get_active()
        if isinstance(task, gtd.Task) and not task.project == project :
            if isinstance(project, gtd.Project):
                project.add_task(task)
            task.project.remove_task(task)
            task.project = project

    def on_project_renamed(self, project):
        self.widget.queue_draw()


# add all areas to the area combo box
# FIXME: consider area listeners
# we need to be able update when areas are added or removed, and when selected realms change
# and when areas change which realm they pertain to
class AreaCombo(WidgetWrapper):
    def __init__(self, widget, model):
        WidgetWrapper.__init__(self, widget)

        renderer = gtk.CellRendererText()
        self.widget.pack_start(renderer)
        self.widget.set_cell_data_func(renderer, self._data_func)
        self.widget.set_model(model)
        self.widget.set_active(0)

    def _data_func(self, column, cell, model, iter):
        area = model[iter][0]
        if area:
            cell.set_property("text", area.title)

    def get_active(self):
        iter = self.widget.get_active_iter()
        if iter:
            return self.widget.get_model()[iter][0]
        else:
            return None

    def set_active(self, area):
        if isinstance(area, gtd.Area):
            return self.widget.set_active_iter(self.area_iter(area))
        else:
            return self.widget.set_active(-1)

    # return the iter, or None, corresponding to "area"
    # consider a more consistent function name (with gtk names)
    # like get_iter_from_area
    def area_iter(self, area):
        model = self.widget.get_model()
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == area:
                return iter
            iter = model.iter_next(iter)
        return None

    # FIXME: control logic should be elsewhere?
    def on_project_area_changed(self, project_list):
        project = GUI().get_widget(project_list.name).get_current()
        area = self.get_active()
        if isinstance(project, gtd.Project) and not project.area == project :
            if isinstance(area, gtd.Area):
                area.add_project(project)
            project.area.remove_project(project)
            project.area = area

    def on_area_renamed(self, area):
        self.widget.queue_draw()

# menu bar callbacks
class MenuBar(WidgetWrapper):
    def __init__(self, widget):
        WidgetWrapper.__init__(self, widget)

    def on_realms_and_areas_activate(self, menuitem):
        GUI().get_widget("realm_area_dialog").widget.show()

    # FIXME: the main window should grow/shrink to accomodate this form
    #        consider moving both forms to the same parent hbox so it can
    #        be shown/hidden in one shot.
    def on_details_activate(self, menuitem):
        if menuitem.active:
            GUI().get_widget("task_form_vbox").widget.show()
            GUI().get_widget("project_form_vbox").widget.show()
        else:
            GUI().get_widget("task_form_vbox").widget.hide()
            GUI().get_widget("project_form_vbox").widget.hide()

    def on_about_activate(self, menuitem):
        GUI().get_widget("about_dialog").widget.show()


class GTDRowPopup(WidgetWrapper):
    def __init__(self, widget):
        WidgetWrapper.__init__(self, widget)
        self.tree_view = None
    
    # gtk signal callbacks (defined in and connected via Glade)
    def on_gtd_row_popup_rename(self, widget):
        print "on_rename"
        print "tree_view is a", self.tree_view.__class__
        obj = self.tree_view.get_current()
        print "current element is a", obj.__class__

    def on_gtd_row_popup_delete(self, widget):
        obj = self.tree_view.get_current()
        print "on_delete", obj.title
        # FIXME: implement the remove path in the GTD tree


class AboutDialog(WidgetWrapper):
    def __init__(self, widget):
        WidgetWrapper.__init__(self, widget)

    def on_about_dialog_delete(self, dialog, event):
        self.widget.hide()
        return True

    def on_about_dialog_response(self, dialog, response):
        if response == gtk.RESPONSE_CANCEL:
            self.widget.hide()


class RealmAreaDialog(WidgetWrapper):
    def __init__(self, widget, realm_area_store):
        WidgetWrapper.__init__(self, widget)
        self.realm_area_store = realm_area_store
        self.realm_area_tree = RealmAreaTreeView(GUI().get_widget("realm_area_tree").widget,
                                                 self.realm_area_store.model)

    def on_realm_area_dialog_delete(self, dialog, event):
        self.widget.hide()
        return True

    def on_realm_area_dialog_response(self, dialog, response):
        if response == gtk.RESPONSE_OK:
            self.widget.hide()
