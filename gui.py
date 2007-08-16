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
            widget = WidgetWrapperBase(gtk.glade.XML.get_widget(self, name))
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
        store = GUI().get_widget("task_tree").widget.get_model()
        if GUI().get_widget("taskviewby").widget.get_active() == 0:
            store.view_by_context()
        else:
            store.view_by_project()


class GTDTreeModel(gtk.TreeStore):
    def __init__(self, gtd, treeview):
        gtk.TreeStore.__init__(self, 'gboolean', object)
        self.gtd = gtd

        # set up the task_tree model
        treeview.set_model(self)

        # create the TreeViewColumns to display the data
        self.tvcolumn0 = gtk.TreeViewColumn("Done")
        self.tvcolumn1 = gtk.TreeViewColumn("Title")

        # append the columns to the view
        treeview.append_column(self.tvcolumn0)
        treeview.append_column(self.tvcolumn1)

        # create the CellRenderers
        self.cell0 = gtk.CellRendererToggle()
        self.cell0.connect('toggled', self.toggled, self, 0)
        self.cell1 = gtk.CellRendererText()
        self.cell1.set_property('editable', True)
        self.cell1.connect('edited', self.edited, self, 1)

        # attach the CellRenderers to each column
        self.tvcolumn0.pack_start(self.cell0, False)
        self.tvcolumn1.pack_start(self.cell1, True)

        # display data directly from the gtd object, rather than setting attributes
        self.tvcolumn0.set_cell_data_func(self.cell0, self.task_data_func, "complete")
        self.tvcolumn1.set_cell_data_func(self.cell1, self.task_data_func, "title")

        # make it searchable
        treeview.set_search_column(1)

        # Allow sorting on the column
        self.tvcolumn1.set_sort_column_id(1)

    def view_by_context(self):
        self.clear()
        for c in self.gtd.contexts:
            piter = self.append(None, [0, c])
            for t in self.gtd.context_tasks(c):
                if t.project.area.realm.visible:
                    self.append(piter, [1, t])

    def view_by_project(self):
        self.clear()
        for r in self.gtd.realms:
            if r.visible:
                for a in r.areas:
                    for p in a.projects:
                        piter = self.append(None, [0, p])
                        for t in p.tasks:
                            self.append(piter, [1, t])

    # signal callbacks
    def toggled(self, cell, path, store, column):
        complete = store[path][column]
        row_data = store[path][1]
        if isinstance(row_data, gtd.Task):
            row_data.complete = not row_data.complete

    def edited(self, cell, path, new_text, store, column):
        #piter = store.iter_parent(store.get_iter(path))
        row_data = store[path][column]
        row_data.title = new_text
        if isinstance(row_data, gtd.Task):
            GUI().get_widget("task_title").widget.set_text(row_data.title)

    # FIXME: use something like this so all we store in the tree is the task object itself
    # may need a gtd_row abstract class and derived classes
    # assign to a column like:
    def task_data_func(self, column, cell, store, iter, data):
        obj = store.get_value(iter, 1)
        # FIXME: add project.complete var, and update to handle in first test below
        if data is "complete":
            if isinstance(obj, gtd.Task):  # or isinstance(obj, gtd.Project)
                cell.set_property("active", obj.complete)
            else:
                cell.set_property("active", False)
        elif data is "title":
            text = obj.title
            if not isinstance(obj, gtd.Task):
                text = "<b>%s</b>"%text
            cell.set_property("markup", text)
        else:
            # FIXME: throw an exception
            print "ERROR: didn't set toggle property for ", obj.title


class TaskTree(WidgetWrapper):
    def __init__(self, widget):
        WidgetWrapper.__init__(self, widget)

    # return the current gtd object
    def get_current_data(self):
        row_data = None
        path = self.widget.get_cursor()[0]
        if path:
            row_data = self.widget.get_model()[path][1]
        return row_data

    # signal callbacks
    def on_task_tree_cursor_changed(self, tree):
        path = tree.get_cursor()[0]
        row_data = tree.get_model()[path][1]
        task_title = GUI().get_widget("task_title").widget
        task_notes = GUI().get_widget("task_notes").widget
        if isinstance(row_data, gtd.Task):
            task_title.set_text(row_data.title)
            GUI().get_widget("task_contexts_table").set_active_contexts(row_data.contexts)
            # FIXME: update project combo box
            task_notes.get_buffer().set_text(row_data.notes)
        elif isinstance(row_data, gtd.Context):
            task_title.set_text("")
            GUI().get_widget("task_contexts_table").set_active_contexts([row_data])
            # FIXME: clear project combo box
            task_notes.get_buffer().set_text("")
        elif isinstance(row_data, gtd.Project):
            task_title.set_text("")
            # FIXME: clear contexts table
            GUI().get_widget("task_contexts_table").uncheck_all()
            # FIXME: set project combo box
            print "FIXME: set project combo box to: " + row_data.title
            task_notes.get_buffer().set_text("")


# Example class using aggregation instead of inheritance
class TaskViewBy(WidgetWrapper):
    def __init__(self, widget):
        WidgetWrapper.__init__(self, widget)
        # FIXME: pull the default view from a config
        self.widget.set_active(0)

    # signal callbacks
    def on_taskviewby_changed(self, widget):
        view = widget.get_active()
        model = GUI().get_widget("task_tree").widget.get_model()
        # FIXME: don't use magic numbers
        if view == 0:
            model.view_by_context()
        elif view == 1:
            model.view_by_project()

class PydoWindow(WidgetWrapper):
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
        row_data = GUI().get_widget("task_tree").get_current_data()
        if row_data and isinstance(row_data, gtd.Task):
            # FIXME: this shouldn't have to be done twice
            if cb.get_active():
                row_data.add_context(cb.context)
            else:
                row_data.remove_context(cb.context)
            # FIXME: tell the tree to update itself

