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
    def __init__(self):
        xml = gtk.glade.XML('glade/pydo.glade')
        xml.signal_autoconnect(self)

        # load test data for now, later get the last filename from gconf
        self.filename = "test.gtd"
        #self.filename = None

        if self.filename:
            self.gtd = gtd_tree.load(self.filename)
        else:
            self.gtd = gtd_tree.gtd_tree()
            gtd_tree.save(self.gtd, "test.gtd")

        # set up the task_tree model
        # FIXME: use a custom widget in glade, and override the treeview as well
        self.treeview = xml.get_widget("task_tree")
        self.treestore = gtd_gui.GTDTreeModel(self.gtd, self.treeview)

    def on_window_destroy(self, widget):
        gtk.main_quit()

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

# test to see if we were run directly... ???
#if __name__ == "__main__":
#    hello = HelloWorld()
#    hello.main()

