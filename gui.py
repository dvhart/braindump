#    Filename: gui.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: glade gui singleton class
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
# 2007-Aug-3:	Initial version by Darren Hart <darren@dvhart.com>

import gtk, gtk.glade

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
        # FIXME: init this from the config (stored in gtd_tree ?)
        self.set_active(1)

    def on_toggled(self, userparam):
        if self.get_active() is True:
            print self.realm.title + " is on"
        else:
            print self.realm.title + " is off"


