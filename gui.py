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
        print "treeview is of type ", type(treeview)
        treeview.set_model(self)

        # create the TreeViewColumn to display the data
        self.tvcolumn0 = gtk.TreeViewColumn("Done")
        self.tvcolumn1 = gtk.TreeViewColumn("Title")

        # add tvcolumn to treeview
        treeview.append_column(self.tvcolumn0)
        treeview.append_column(self.tvcolumn1)

        # create a CellRendererText to render the data
        self.cell0 = gtk.CellRendererToggle()
        self.cell0.connect('toggled', self.toggled, self, 0)
        self.cell1 = gtk.CellRendererText()
        self.cell1.set_property('editable', True)
        self.cell1.connect('edited', self.edited_cb, self, 1)

        # add the cell to the tvcolumn and allow it to expand
        self.tvcolumn0.pack_start(self.cell0, True)
        self.tvcolumn1.pack_start(self.cell1, True)

        # set the cell "text" attribute to column 0 - retrieve text
        # from that column in treestore
        self.tvcolumn0.add_attribute(self.cell0, 'active', 0)
        self.tvcolumn0.set_cell_data_func(self.cell0, self.task_data_func, "complete")
        #self.tvcolumn1.add_attribute(self.cell1, 'markup', 1)
        self.tvcolumn1.set_cell_data_func(self.cell1, self.task_data_func, "title")

        # make it searchable
        treeview.set_search_column(1)

        # Allow sorting on the column
        self.tvcolumn1.set_sort_column_id(1)

    def view_by_context(self):
        print "view by context"
        self.clear()
        for c in self.gtd.contexts:
            piter = self.append(None, [0, c])
            for t in c.tasks:
                if t.project.area.realm.visible:
                    self.append(piter, [1, t])

    def view_by_project(self):
        print "view by project"
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

    def edited_cb(self, cell, path, new_text, store, column):
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
        if data is "complete" and isinstance(obj, gtd.Task):
            cell.set_property("active", obj.complete)
        if data is "title":
            cell.set_property("markup", obj.title)
    


class TaskTree(WidgetWrapper):
    def __init__(self, widget):
        WidgetWrapper.__init__(self, widget)

    # signal callbacks
    def on_task_tree_cursor_changed(self, tree):
        path = tree.get_cursor()[0]
        row_data = tree.get_model()[path][1]
        task_title = GUI().get_widget("task_title").widget
        task_notes = GUI().get_widget("task_notes").widget
        if isinstance(row_data, gtd.Task):
            task_title.set_text(row_data.title)
            # FIXME: update contexts table
            # FIXME: update project combo box
            task_notes.get_buffer().set_text(row_data.notes)
        elif isinstance(row_data, gtd.Context):
            task_title.set_text("")
            # FIXME: set context checkbox
            print "FIXME: set context to: " + row_data.title
            # FIXME: clear project combo box
            task_notes.get_buffer().set_text("")
        elif isinstance(row_data, gtd.Project):
            task_title.set_text("")
            # FIXME: clear contexts table
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
    def __init_(self, widget):
        WidgetWrapper.__init__(self, widget)

    # signal callbacks
    def on_window_destroy(self, widget):
        gtk.main_quit()
