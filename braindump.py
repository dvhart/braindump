#!/usr/bin/env python
#    Filename: braindump.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: BrainDump application class and program initialization code
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
from gui_datastores import *
import gnome
import gtd

# GUI Classses and callbacks
class BrainDump:
    def __init__(self):
        # aggregate widgets, with member callbacks
        GUI("glade/braindump.glade")

        # load test data for now, later get the last filename from gconf
        #self.filename = "test.gtd"
        self.filename = None

        if self.filename:
            self.gtd_tree = gtd.load(self.filename)
        else:
            self.gtd_tree = gtd.Tree()
            gtd.save(self.gtd_tree, "test.gtd")

        BrainDumpWindow(GUI().get_widget("braindump_window").widget)

        # task tab widgets
        TaskListView(GUI().get_widget("task_list").widget, self.gtd_tree)
        TaskFilterListView(GUI().get_widget("task_filter_list").widget, self.gtd_tree)
        TaskFilterBy(GUI().get_widget("taskfilterby").widget)
        ContextTable(GUI().get_widget("task_contexts_table").widget, self.gtd_tree)
        # FIXME: use an app wide ProjectTreeModel
        ProjectCombo(GUI().get_widget("task_project").widget, ProjectListStore(self.gtd_tree))

        # project tab widgets
        ProjectListView(GUI().get_widget("project_list").widget, self.gtd_tree)
        AreaFilterListView(GUI().get_widget("area_filter_list").widget, self.gtd_tree)
        # FIXME: use an app wide ProjectTreeModel
        AreaCombo(GUI().get_widget("project_area").widget, AreaListStore(self.gtd_tree))

        # add all areas to the project combo box
        # FIXME: consider area listeners
#        project_area = GUI().get_widget("project_area").widget
#        for r in self.gtd_tree.realms:
#            if r.visible:
#                for a in r.areas:
#                    project_area.append_text(a.title)
#        project_area.set_active(0)

        # add the realm toggle buttons
        # FIXME: custom toolbar? as a realm listener?
        realm_toggles = GUI().get_widget("realm_toggles").widget
        for realm in self.gtd_tree.realms:
            rtb = RealmToggleToolButton(realm)
            realm_toggles.insert(rtb, -1)
            rtb.show()

        # FIXME: get the last selection and filterby from last time we were run
        GUI().get_widget("task_filter_list").widget.get_selection().select_all()
        GUI().get_widget("area_filter_list").widget.get_selection().select_all()


# test to see if we were run directly
if __name__ == "__main__":
    # FIXME: why the try block here? What are the props for?
    #try:
    #    props = { gnome.PARAM_APP_DATADIR : '/usr/share'}
    #    prog = gnome.program_init('braindump', '0.01', properties=props)
    #except:
    #    prog = gnome.program_init('braindump', '0.01')
    #    prog.set_property('app-datadir', '/usr/share')
    gnome.init("braindump", "0.01") # simpler alternative to the props/prog bits above
    app = BrainDump()
    gtk.main()
