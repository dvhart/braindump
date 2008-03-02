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

import gobject
import gtk, gtk.glade
import gtd
from gui_datastores import *


# FIXME: is this base class correct?  I totally just guessed!
# FIXME: try and understand what the hell is actually going on in this mess
#        perhaps there is a more elegant (read understandable) way of accomplishing this?
class GSingleton(gobject.GObjectMeta):
    def __init__(self, name, bases, dict):
        super(GSingleton, self).__init__(name, bases, dict)
        self.instance = None

    def __call__(self, *args, **kw):
        if self.instance is None:
            print "corner case: allow for access to bound variables in __init__"
            self.instance = super(GSingleton, self).__call__(*args, **kw)
        return self.instance


class GUI(gtk.glade.XML):
    __metaclass__ = GSingleton
    widgets = {}

    def __init__(self, file=""):
        print "Calling __init__ with file="+file
        gtk.glade.XML.__init__(self, file)

    def register_widget(self, wrapped_widget):
        name = wrapped_widget.widget.get_name()
        if self.widgets.has_key(name):
            # FIXME: throw a proper exception
            print 'ERROR: widgets{' + name + '} already registered - OVERWRITING!'
        print 'Registering widgets{' + name + '} as ' + str(wrapped_widget)
        self.widgets[wrapped_widget.widget.get_name()] = wrapped_widget

    # Return the wrapped widget if it exists, create one for consistent usage if not
    def get_widget(self, name):
        if self.widgets.has_key(name):
            widget = self.widgets[name]
        else:
            gtk_widget = gtk.glade.XML.get_widget(self, name)
            if not gtk_widget:
                print "ERROR: failed to find widget: ", name
            widget = WidgetWrapperBase(gtk_widget)
        return widget


# FIXME: rather than having to reference .widget, is it possible to superimpose
#        the widget namespace onto ours with metaclasses ??
class WidgetWrapperBase(object):
    def __init__(self, widget):
        self.widget = widget


class WidgetWrapper(WidgetWrapperBase):
    def __init__(self, widget):
        WidgetWrapperBase.__init__(self, widget)
        GUI().register_widget(self)
        GUI().signal_autoconnect(self)


class RealmToggleToolButton(gtk.ToggleToolButton):
    def __init__(self, realm):
        self.realm = realm
        gtk.ToggleToolButton.__init__(self)
        self.set_property("label", self.realm.title)
        self.connect("toggled", self.on_toggled)
        # FIXME: init this from the config (stored in tree ?)
        self.set_active(self.realm.visible)

    def on_toggled(self, userparam):
        self.realm.set_visible(self.get_active())
        task_filter_list = GUI().get_widget("task_filter_list")
        # FIXME: the logic doesn't belong here
        if GUI().get_widget("taskfilterby").widget.get_active() == 0:
            task_filter_list.filter_by_context()
        else:
            task_filter_list.filter_by_project()
        GUI().get_widget("area_filter_list").reload()


class TaskFilterListView(WidgetWrapper):
    def __init__(self, widget, gtd_tree):
        WidgetWrapper.__init__(self, widget)
        self.gtd_tree = gtd_tree
        self.context_store = ContextListStore(gtd_tree)
        self.project_store = ProjectListStore(gtd_tree)
        # FIXME: which model should we do first?
        self.widget.set_model(self.context_store)

        # setup the column and cell renderer
        self.tvcolumn0 = gtk.TreeViewColumn()
        self.cell0 = gtk.CellRendererText()
        self.cell0.set_property('editable', True)
        self.cell0.connect('edited', self.on_filter_edited, self.widget.get_model(), 0)
        self.tvcolumn0.pack_start(self.cell0, False)
        self.tvcolumn0.set_cell_data_func(self.cell0, self.data_func, "data")
        self.widget.append_column(self.tvcolumn0)

        # setup selection modes and callback
        self.widget.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.widget.set_rubber_banding(True)
        # FIXME: this should be connected by the application...
        self.widget.get_selection().connect("changed", GUI().get_widget("task_list").on_filter_selection_changed)

    def filter_by_context(self):
        self.widget.set_model(self.context_store)

    def filter_by_project(self):
        self.widget.set_model(self.project_store)

    def data_func(self, column, cell, model, iter, data):
        obj = model[iter][0]
        cell.set_property("markup", obj.title)

    # signal callbacks
    def on_filter_edited(self, cell, path, new_text, model, column):
        model[path][column].title = new_text
        # FIXME: notify other widgets interested in this value (ie checkbuttons)

    def on_task_filter_all(self, widget):
        self.widget.get_selection().select_all()

    def on_task_filter_none(self, widget):
        self.widget.get_selection().unselect_all()
        # FIXME: should select (No Context) or (No Project)
        # never allow viewing no tasks at all (will cause problems creating 
        # new tasks as they will just vanish from the view)


class TaskListView(WidgetWrapper):
    def __init__(self, widget, gtd_tree):
        WidgetWrapper.__init__(self, widget)
        self.gtd_tree = gtd_tree
        self.widget.set_model(TaskListStore(self.gtd_tree))

        # create the TreeViewColumns to display the data
        self.tvcolumn0 = gtk.TreeViewColumn("Done")
        self.tvcolumn1 = gtk.TreeViewColumn("Title")

        # append the columns to the view
        widget.append_column(self.tvcolumn0)
        widget.append_column(self.tvcolumn1)

        # create the CellRenderers
        self.cell0 = gtk.CellRendererToggle()
        self.cell0.connect('toggled', self.toggled, widget.get_model(), 0)
        self.cell1 = gtk.CellRendererText()
        self.cell1.set_property('editable', True)
        self.cell1.connect('edited', self.edited, widget.get_model(), 1)

        # attach the CellRenderers to each column
        self.tvcolumn0.pack_start(self.cell0) # expand True by default
        self.tvcolumn1.pack_start(self.cell1)

        # display data directly from the gtd object, rather than setting attributes
        self.tvcolumn0.set_cell_data_func(self.cell0, self.task_data_func, "complete")
        self.tvcolumn1.set_cell_data_func(self.cell1, self.task_data_func, "title")

        # make it searchable
        widget.set_search_column(1)

    def task_data_func(self, column, cell, model, iter, data):
        task = model[iter][0]
        if data is "complete":
            if isinstance(task, gtd.NewTask):
                cell.set_property("inconsistent", True)
            else:
                cell.set_property("active", task.complete)
                cell.set_property("inconsistent", False)
        elif data is "title":
                cell.set_property("markup", task.title)
        else:
            # FIXME: throw an exception
            print "ERROR: didn't set %s property for "%data, obj.title

    # return the selected task
    def get_current_task(self):
        task = None
        # FIXME: is this error checking necessary
        path = self.widget.get_cursor()[0]
        if path:
            task = self.widget.get_model()[path][0]
        return task

    def update_current_context(self, context, active):
        task = self.get_current_task()
        # don't try this on None or gtd.NewTask objects
        if isinstance(task, gtd.Task):
            update_tree = False
            model = self.widget.get_model()
            if active:
                if not task.contexts.count(context):
                    # FIXME: force refresh? need signals and slots
                    task.add_context(context)
            else:
                if task.contexts.count(context):
                    # FIXME: force refresh? need signals and slots
                    task.remove_context(context)
                    # FIXME: this should be done via some signals and slots mechanism of the gtd.Tree
                    self.on_filter_selection_changed(GUI().get_widget("task_filter_list").widget.get_selection())

    def update_current_project(self, project):
        task = self.get_current_task()
        # don't try this on None or gtd.NewTask objects
        if isinstance(task, gtd.Task):
            if task.project is not project:
                print "update_current_project: ", project.title
                # FIXME: this should be in one place... probably task- or tree- centric?
                task.project.remove_task(task)
                task.project = project
                project.add_task(task)
                # FIXME: this should be done via some signals and slots mechanism of the gtd.Tree
                self.on_filter_selection_changed(GUI().get_widget("task_filter_list").widget.get_selection())

    def on_filter_selection_changed(self, selection):
        self.widget.get_model().filter_by_selection(selection)
        return

    # signal callbacks
    def on_task_list_cursor_changed(self, tree):
        path = tree.get_cursor()[0]
        task = tree.get_model()[path][0]
        if task:
            if isinstance(task, gtd.NewTask):
                GUI().get_widget("task_form_vbox").widget.set_sensitive(False)
            else:
                GUI().get_widget("task_form_vbox").widget.set_sensitive(True)
            task_notes = GUI().get_widget("task_notes").widget
            task_contexts = GUI().get_widget("task_contexts_table")
            task_notes.get_buffer().set_text(task.notes)
            task_contexts.set_active_contexts(task.contexts)
            GUI().get_widget("task_project").set_active(task.project)

    def toggled(self, cell, path, model, column):
        complete = model[path][column]
        task = model[path][0]
        # don't try and set the complete field on a gtd.NewTask
        if isinstance(task, gtd.Task):
            task.complete = not task.complete

    def edited(self, cell, path, new_text, model, column):
        task = model[path][0]
        if task:
            task.title = new_text


# FIXME: perhaps this can really all be done in glade, and a callback in task_filter_list
class TaskFilterBy(WidgetWrapper):
    def __init__(self, widget):
        WidgetWrapper.__init__(self, widget)
        # FIXME: pull the default view from a config
        self.widget.set_active(0)

    # FIXME: this connection should be made by the app
    # signal callbacks
    def on_filterby_changed(self, widget):
        view = widget.get_active()
        task_filter_list = GUI().get_widget("task_filter_list")
        # FIXME: don't use magic numbers
        if view == 0:
            task_filter_list.filter_by_context()
        elif view == 1:
            task_filter_list.filter_by_project()


class AreaFilterListView(WidgetWrapper):
    def __init__(self, widget, gtd_tree):
        WidgetWrapper.__init__(self, widget)
        self.gtd_tree = gtd_tree
        self.widget.set_model(AreaListStore(gtd_tree))

        # setup the column and cell renderer
        self.tvcolumn0 = gtk.TreeViewColumn()
        self.cell0 = gtk.CellRendererText()
        self.cell0.set_property('editable', True)
        self.cell0.connect('edited', self.on_filter_edited, self.widget.get_model(), 0)
        self.tvcolumn0.pack_start(self.cell0, False)
        self.tvcolumn0.set_cell_data_func(self.cell0, self.data_func, "data")
        self.widget.append_column(self.tvcolumn0)

        # setup selection modes and callback
        self.widget.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.widget.set_rubber_banding(True)
        # FIXME: this connection should be made in the application
        self.widget.get_selection().connect("changed", GUI().get_widget("project_list").on_filter_selection_changed)
        self.reload()

    def reload(self):
        self.widget.get_model().reload()

    def data_func(self, column, cell, model, iter, data):
        obj = model[iter][0]
        cell.set_property("markup", obj.title)

    # signal callbacks
    def on_filter_edited(self, cell, path, new_text, model, column):
        model[path][column].title = new_text
        # FIXME: notify other widgets interested in this value (ie checkbuttons)

    def on_area_filter_all(self, widget):
        self.widget.get_selection().select_all()

    def on_area_filter_none(self, widget):
        self.widget.get_selection().unselect_all()
        # FIXME: should select (No Context) or (No Project)
        # never allow viewing no tasks at all (will cause problems creating
        # new tasks as they will just vanish from the view)


class ProjectListView(WidgetWrapper):
    def __init__(self, widget, gtd_tree):
        WidgetWrapper.__init__(self, widget)
        self.gtd_tree = gtd_tree
        self.widget.set_model(ProjectListStore(self.gtd_tree, True))

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
        self.cell0.connect('toggled', self.toggled, widget.get_model(), 0)
        self.cell1 = gtk.CellRendererText()
        self.cell1.set_property('editable', True)
        self.cell1.connect('edited', self.edited, widget.get_model(), 1)
        self.cell2 = gtk.CellRendererText()

        # attach the CellRenderers to each column
        self.tvcolumn0.pack_start(self.cell0, False)
        self.tvcolumn1.pack_start(self.cell1) # expand True by default
        self.tvcolumn1.pack_start(self.cell2, False)

        # display data directly from the gtd object, rather than setting attributes
        self.tvcolumn0.set_cell_data_func(self.cell0, self.project_data_func, "complete")
        self.tvcolumn1.set_cell_data_func(self.cell1, self.project_data_func, "title")
        self.tvcolumn1.set_cell_data_func(self.cell2, self.project_data_func, "tasks")

        # make it searchable
        widget.set_search_column(1)

    # return the selected project
    def get_current_project(self):
        project = None
        # FIXME: is this error checking necessary
        path = self.widget.get_cursor()[0]
        if path:
            project = self.widget.get_model()[path][0]
        return project

    def update_current_area(self, area):
        project = self.get_current_project()
        # don't try this on None or gtd.NewTask objects
        if isinstance(project, gtd.Project):
            if project.area is not area:
                print "update_current_area: ", area.title
                # FIXME: this should be in one place... probably project- or tree- centric?
                project.area.remove_project(project)
                project.area = area
                area.add_project(project)
                # FIXME: this should be done via some signals and slots mechanism of the gtd.Tree
                self.on_filter_selection_changed(GUI().get_widget("area_filter_list").widget.get_selection())

    def project_data_func(self, column, cell, model, iter, data):
        project = model[iter][0]
        if data is "complete":
            if isinstance(project, gtd.NewProject):
                cell.set_property("inconsistent", True)
            else:
                cell.set_property("active", project.complete)
                cell.set_property("inconsistent", False)
        elif data is "title":
            cell.set_property("markup", project.title)
        elif data is "tasks":
            if isinstance(project, gtd.NewProject):
                cell.set_property("markup", "")
            else:
                cell.set_property("markup", len(project.tasks))
        else:
            # FIXME: throw an exception
            print "ERROR: didn't set %s property for "%data, obj.title

    def on_filter_selection_changed(self, selection):
        self.widget.get_model().filter_by_selection(selection)

    # signal callbacks
    def on_project_list_cursor_changed(self, tree):
        path = tree.get_cursor()[0]
        project = tree.get_model()[path][0]
        if project:
            if isinstance(project, gtd.NewProject):
                GUI().get_widget("project_form_vbox").widget.set_sensitive(False)
            else:
                GUI().get_widget("project_form_vbox").widget.set_sensitive(True)
            project_notes = GUI().get_widget("project_notes").widget
            project_notes.get_buffer().set_text(project.notes)
            GUI().get_widget("project_area").set_active(project.area)

    def toggled(self, cell, path, model, column):
        complete = model[path][column]
        project = model[path][0]
        # don't try and set the complete field on a gtd.NewTask
        if isinstance(project, gtd.Project):
            project.complete = not project.complete

    def edited(self, cell, path, new_text, model, column):
        project = model[path][0]
        if project:
            project.title = new_text


class BrainDumpWindow(WidgetWrapper):
    def __init__(self, widget):
        WidgetWrapper.__init__(self, widget)

    # signal callbacks
    def on_window_destroy(self, widget):
        gtk.main_quit()


class ContextCheckButton(gtk.CheckButton):
    def __init__(self, context):
        gtk.CheckButton.__init__(self, context.title)
        self.context = context


# Class aggregrating GtkTable to list contexts for tasks
class ContextTable(WidgetWrapper):
    def __init__(self, widget, gtd_tree):
        WidgetWrapper.__init__(self, widget)
        self.table = gtk.Table()
        widget.add(self.table)
        self.table.show()
        self.gtd_tree = gtd_tree
        self.last_allocation = None
        self.context_cbs = {}
        self.max_width = 0
        # FIXME: move to a context listener function or something...
        for context in self.gtd_tree.contexts:
            cb = ContextCheckButton(context)
            cb.connect("toggled", self.on_checkbutton_toggled)
            self.context_cbs[context] = cb
            self.max_width = max(self.max_width, cb.size_request()[0])
        self.on_size_allocate(self.widget, self.widget.allocation)

    def set_active_contexts(self, contexts):
        for c, cb in self.context_cbs.iteritems():
            cb.set_property("active", c in contexts)

    def uncheck_all(self):
        for c, cb in self.context_cbs.iteritems():
            cb.set_property("active", False)

    def on_size_allocate(self, widget, allocation):
        if self.last_allocation and \
           allocation.width == self.last_allocation.width:
            return
        self.last_allocation = allocation

        # resize it (with forced col spacing of 5)
        cols = max(1, min(allocation.width / (self.max_width+5), len(self.context_cbs)))
        rows = max(1, len(self.context_cbs)/cols)
        if len(self.context_cbs) % cols:
            rows = rows + 1

        if (self.table.get_property("n-columns") != cols):
            self.table.set_size_request(cols*self.max_width+5, -1)
            for c, cb in self.context_cbs.iteritems():
                if cb.parent:
                    self.table.remove(cb)
            self.table.resize(rows, cols)
            i=0
            for c, cb in self.context_cbs.iteritems():
                x = i % cols
                y = i / cols
                self.table.attach(cb, x, x+1, y, y+1)
                cb.show()
                i = i + 1

    # checkbox callbacks
    # FIXME: is there a way to set the active property without triggering the signal?
    # if not, we need to be careful not to act on an event that we did programmatically
    # vs. the user clicking the checkbox
    def on_checkbutton_toggled(self, cb):
        tree = GUI().get_widget("task_list")
        tree.update_current_context(cb.context, cb.get_active())
 

# add all projects to the project combo box
# FIXME: consider project listeners
# we need to be able update when projects are added or removed, and when selected realms change
# and when projects change which realm they pertain to
class ProjectCombo(WidgetWrapper):
    def __init__(self, widget, model):
        WidgetWrapper.__init__(self, widget)
 
        # FIXME: This causes a gtk warning... not sure how else to get the renderer,
        # and we need it to set the cell_data_func... ??
        #renderer = self.widget.get_child().get_cell_renderers()[0]
        #self.widget.clear_attributes(renderer)
        
        # Altnernatively we create our own CellRendererText object and pack it in,
        # but we should clear the old one out - but that gives the same warning ???
        #self.widget.clear()
        renderer = gtk.CellRendererText()
        self.widget.pack_start(renderer)
        print "Renderers: ", len(self.widget.get_child().get_cell_renderers())
        self.widget.set_cell_data_func(renderer, self.cell_data_func)
        self.widget.set_model(model)
        self.widget.set_active(0)

    def cell_data_func(self, column, cell, model, iter):
        project = model[iter][0]
        if project:
            cell.set_property("text", project.title)
        else:
            # FIXME: throw an exception here
            cell.set_property("text", "Null Project?")
            
    def get_active(self):
        return self.widget.get_model()[self.widget.get_active()][0]

    def set_active(self, project):
        return self.widget.set_active_iter(self.widget.get_model().project_iter(project))

    # FIXME: this should just emit a signal, slots should defined in other objects, and
    # connected in the main application code.
    def on_task_project_changed(self, widget):
        print "task_project_changed: ", self.get_active().title
        tree = GUI().get_widget("task_list")
        tree.update_current_project(self.get_active())


# add all areas to the area combo box
# FIXME: consider area listeners
# we need to be able update when areas are added or removed, and when selected realms change
# and when areas change which realm they pertain to
class AreaCombo(WidgetWrapper):
    def __init__(self, widget, model):
        WidgetWrapper.__init__(self, widget)

        # FIXME: This causes a gtk warning... not sure how else to get the renderer,
        # and we need it to set the cell_data_func... ??
        #renderer = self.widget.get_child().get_cell_renderers()[0]
        #self.widget.clear_attributes(renderer)

        # Altnernatively we create our own CellRendererText object and pack it in,
        # but we should clear the old one out - but that gives the same warning ???
        #self.widget.clear()
        renderer = gtk.CellRendererText()
        self.widget.pack_start(renderer)
        print "Renderers: ", len(self.widget.get_child().get_cell_renderers())
        self.widget.set_cell_data_func(renderer, self.cell_data_func)
        self.widget.set_model(model)
        self.widget.set_active(0)

    def cell_data_func(self, column, cell, model, iter):
        area = model[iter][0]
        if area:
            cell.set_property("text", area.title)
        else:
            # FIXME: throw an exception here
            cell.set_property("text", "Null Area?")

    def get_active(self):
        return self.widget.get_model()[self.widget.get_active()][0]

    def set_active(self, area):
        return self.widget.set_active_iter(self.widget.get_model().area_iter(area))

    # FIXME: this should just emit a signal, slots should defined in other objects, and
    # connected in the main application code.
    def on_project_area_changed(self, widget):
        print "project_area_changed: ", self.get_active().title
        tree = GUI().get_widget("project_list")
        tree.update_current_area(self.get_active())

