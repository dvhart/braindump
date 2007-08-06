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
import gtd

class GUI(gtk.glade.XML):
    instance = None       
    def __new__(self, *args, **kargs): 
        if self.instance is None:
            self.instance = gtk.glade.XML('glade/pydo.glade')
        return self.instance

class RealmToggleToolButton(gtk.ToggleToolButton):
    def __init__(self, realm):
        self.realm = realm
        gtk.ToggleToolButton.__init__(self)
        self.set_property("label", self.realm.title)
        self.connect("toggled", self.on_toggled)
        # FIXME: init this from the config (stored in tree ?)
        self.set_active(1)

    def on_toggled(self, userparam):
        self.realm.set_visible(self.get_active())
        store = GUI().get_widget("task_tree").get_model()
        if GUI().get_widget("taskviewby").get_active() == 0:
            store.view_by_context()
        else:
            store.view_by_project()

class GTDTreeModel(gtk.TreeStore):
    def __init__(self, gtd, treeview):
        gtk.TreeStore.__init__(self, 'gboolean', object)
        self.gtd = gtd

        # set up the task_tree model
        treeview.set_model(self)

        # create the TreeViewColumn to display the data
        self.tvcolumn0 = gtk.TreeViewColumn("Done")
        self.tvcolumn1 = gtk.TreeViewColumn("Title")

        # add tvcolumn to treeview
        treeview.append_column(self.tvcolumn0)
        treeview.append_column(self.tvcolumn1)

        # create a CellRendererText to render the data
        self.cell0 = gtk.CellRendererToggle()
        self.cell1 = gtk.CellRendererText()
        self.cell1.set_property('editable', True)
        self.cell1.connect('edited', self.edited_cb, self, 1)

        # add the cell to the tvcolumn and allow it to expand
        self.tvcolumn0.pack_start(self.cell0, True)
        self.tvcolumn1.pack_start(self.cell1, True)

        # set the cell "text" attribute to column 0 - retrieve text
        # from that column in treestore
        self.tvcolumn0.add_attribute(self.cell0, 'active', 0)
        #self.tvcolumn1.add_attribute(self.cell1, 'markup', 1)
        self.tvcolumn1.set_cell_data_func(self.cell1, task_data_func, data="title")

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

    def edited_cb(self, cell, path, new_text, store, column):
        #piter = store.iter_parent(store.get_iter(path))
        row_data = store[path][column]
        row_data.title = new_text
        if isinstance(row_data, gtd.task):
            GUI().get_widget("task_title").set_text(row_data.title)
        return

# FIXME: use something like this so all we store in the tree is the task object itself
# may need a gtd_row abstract class and derived classes
# assign to a column like:
# tvcolumn1.set_cell_data_func(cell1, task_data_func, data="title")
def task_data_func(column, cell, store, iter):
        task = store.get_value(iter, 1)
        data = "Unknown"
        # if we add user_data, the signature doesn't seem to match ???
        # need to find something else to switch on
        # if user_data == "title":
        data = task.title
        cell.set_property("markup", data)
