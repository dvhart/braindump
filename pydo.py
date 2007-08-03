#!/usr/bin/env python
#    Filename: pydo.py
#      Author: Darren Hart <dvhltc@us.ibm.com>
# Description: 
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
# Copyright (C) IBM Corporation, 2006
#
# 2007-Jun-30:	Initial version by Darren Hart <darren@dvhart.com>

import gtk, gtk.glade
import gnome
import gtd_tree
import gtd_gui

# GUI Classses and callbacks
class GUI:
    taskviewby_labels = ["context","project"]

    def __init__(self):
        xml = gtk.glade.XML('glade/pydo.glade')
        xml.signal_autoconnect(self)

        # initialize the necessary widgets
        # FIXME: load this config from gconf
        xml.get_widget("taskviewby").set_active(0)

        # load test data for now, later get the last filename from gconf
        #self.filename = "test.gtd"
        self.filename = None

        if self.filename:
            self.gtd = gtd_tree.load(self.filename)
        else:
            self.gtd = gtd_tree.gtd_tree()
            gtd_tree.save(self.gtd, "test.gtd")

        # FIXME: create a context_table object, that automatically resizes itself
        # FIXME: consider context listeners
        # build the necessary widgets based on the loaded data
        t = xml.get_widget("task_contexts_table")
        pitch = t.get_property("n-rows")
        i=0
        for context in self.gtd.contexts:
            x = i % pitch
            y = i / pitch
            print x
            print y
            print context.title
            cb = gtk.CheckButton(context.title)
            t.attach(cb, x, x+1, y, y+1)
            cb.show()
            i = i + 1

        # add all projects to the project combo box
        # FIXME: consider project listeners
        task_project = xml.get_widget("task_project")
        for project in self.gtd.projects:
            task_project.append_text(project.title)
        task_project.set_active(0)

        # add all areas to the project combo box
        # FIXME: consider area listeners
        project_area = xml.get_widget("project_area")
        for area in self.gtd.areas:
            project_area.append_text(area.title)
        project_area.set_active(0)

        # set up the task_tree model
        # FIXME: use a custom widget in glade, and override the treeview as well
        self.treeview = xml.get_widget("task_tree")
        self.treestore = gtd_gui.GTDTreeModel(self.gtd, self.treeview)

    def on_window_destroy(self, widget):
        gtk.main_quit()

    def on_taskviewby_changed(self, cb):
        print "Current selection is: " + self.taskviewby_labels[cb.get_active()]
 

# test to see if we were run directly
if __name__ == "__main__":
    # FIXME: why the try block here? What are the props for?
    #try:
    #    props = { gnome.PARAM_APP_DATADIR : '/usr/share'}
    #    prog = gnome.program_init('pydo', '0.01', properties=props)
    #except:
    #    prog = gnome.program_init('pydo', '0.01')
    #    prog.set_property('app-datadir', '/usr/share')
    gnome.init("pydo", "0.01") # simpler alternative to the props/prog bits above
    app = GUI()
    gtk.main()
