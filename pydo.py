#!/usr/bin/env python
#    Filename: pydo.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: Pydo application class and program initialization code
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
from gui import *
import gnome
import gtd

# GUI Classses and callbacks
class Pydo:
    taskviewby_labels = ["context","project"]

    def __init__(self):
        # aggregate widgets, with member callbacks
        GUI("glade/pydo.glade")
        PydoWindow(GUI().get_widget("pydo_window").widget)
        TaskTree(GUI().get_widget("task_tree").widget)
        TaskViewBy(GUI().get_widget("taskviewby").widget)

        # load test data for now, later get the last filename from gconf
        #self.filename = "test.gtd"
        self.filename = None

        if self.filename:
            self.gtd = gtd.load(self.filename)
        else:
            self.gtd = gtd.Tree()
            gtd.save(self.gtd, "test.gtd")

        GTDTreeModel(self.gtd, GUI().get_widget("task_tree").widget)

        # FIXME: create a context_table object, that automatically resizes itself
        # FIXME: consider context listeners
        # build the necessary widgets based on the loaded data
        t = GUI().get_widget("task_contexts_table").widget
        pitch = t.get_property("n-rows")
        i=0
        for context in self.gtd.contexts:
            x = i % pitch
            y = i / pitch
            cb = gtk.CheckButton(context.title)
            t.attach(cb, x, x+1, y, y+1)
            cb.show()
            i = i + 1

        # add all projects to the project combo box
        # FIXME: consider project listeners
        task_project = GUI().get_widget("task_project").widget
        for r in self.gtd.realms:
            if r.visible:
                for a in r.areas:
                    for p in a.projects:
                        task_project.append_text(p.title)
        task_project.set_active(0)

        # add all areas to the project combo box
        # FIXME: consider area listeners
        project_area = GUI().get_widget("project_area").widget
        for r in self.gtd.realms:
            if r.visible:
                for a in r.areas:
                    project_area.append_text(a.title)
        project_area.set_active(0)

        # add the realm toggle buttons
        # FIXME: custom toolbar? as a realm listener?
        realm_toggles = GUI().get_widget("realm_toggles").widget
        for realm in self.gtd.realms:
            rtb = RealmToggleToolButton(realm)
            realm_toggles.insert(rtb, -1)
            rtb.show()
            

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
    app = Pydo()
    gtk.main()
