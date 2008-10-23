#    Filename: date_select.py
# Description: A more functional date selector.
#
# Copyright (C) Darren Hart, 2008
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
# Author(s): Darren Hart <darren@dvhart.com>
#
# Acknowledgements:
# o Johan Dahlin for the kiwi dateentry widget, and the insight it provided
#   into the quirks of the gtk *grab* routines.

from gobject import *
import gtk
from gtk import gdk, keysyms
from gtk.gdk import keyval_from_name
from friendly_date import *
from logging import debug, info, warning, error, critical

class _DateSelectPopup(gtk.Window):
    """A friendly date selection popup window"""

    __gsignals__ = {'date-selected' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
                    'popdown' : (SIGNAL_RUN_FIRST, TYPE_NONE, ())}

    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)

        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.add(frame)
        frame.show()

        vbox = gtk.VBox()
        frame.add(vbox)
        vbox.show()

        self._calendar = gtk.Calendar()
        vbox.pack_start(self._calendar)
        self._calendar.show()

        btn_box = gtk.HButtonBox()
        btn_box.set_border_width(6)
        vbox.pack_start(btn_box)
        btn_box.show()

        for label in ["None", "Today", "Tomorrow"]:
            button = gtk.Button(label)
            button.connect("clicked", self._on_date_button_clicked, label)
            btn_box.pack_start(button)
            button.show()

        self.connect("button-press-event", self._on_button_press)
        self.connect("key-press-event", self._on_key_press)
        self._calendar.connect("day-selected", self._on_day_selected)

    # private interface
    def _grab_window(self):
        activate_time = 0L
        if gdk.pointer_grab(self.window, True,
                         gdk.BUTTON_PRESS_MASK | 
                         gdk.BUTTON_RELEASE_MASK |
                         gdk.POINTER_MOTION_MASK,
                         None, None, activate_time) == 0:
            if gdk.keyboard_grab(self.window, True, activate_time) == 0:
                return True
            else:
                self.window.get_display().pointer_ungrab(activate_time);
                return False
        return False

    def _on_button_press(self, window, event):
        hide = False

        # check if we clicked outside the popup
        w, h = self.get_size()
        x = event.x
        y = event.y
        if x < 0 or x > w or y < 0 or y > h:
            hide = True

        # check if we clicked on another widget in our app
        toplevel = event.window.get_toplevel()
        parent = self.get_parent_window()
        if toplevel != parent:
            hide = True

        if hide:
            self.popdown()

    def _on_key_press(self, popup, event):
        """
        Mimics Combobox behavior

        Escape or Alt+Up: Close
        """

        keyval = event.keyval
        state = event.state & gtk.accelerator_get_default_mod_mask()
        if (keyval == keysyms.Escape or
            ((keyval == keysyms.Up or keyval == keysyms.KP_Up) and
             state == gdk.MOD1_MASK)):
            self.popdown()
            return True

    def _on_day_selected(self, cal):
        if self.get_property("visible"):
            self.popdown()
        year, month, day = cal.get_date()
        datetime_val = datetime(year, month + 1, day)
        datetime_val = datetime_ceiling(datetime_val)
        self.emit("date-selected", datetime_val)

    def _on_date_button_clicked(self, btn, friendly_str):
        self.popdown()
        datetime_val = friendly_to_datetime(friendly_str)
        self.emit("date-selected", datetime_val)

    # public interface
    def popdown(self):
        self.grab_remove()
        self.hide_all()
        self.emit("popdown")

    def popup(self, widget):
        self.realize()
        x, y = widget.window.get_origin()
        x += widget.get_allocation().x
        y += widget.get_allocation().y + widget.get_allocation().height
        self.move(x, y)
        self.show_all()

        if not self._grab_window():
            error("failed to grab window")

        self.grab_add()

    def set_date(self, datetime_val):
        if datetime_val:
            self._calendar.select_month(datetime_val.month-1, datetime_val.year)
            self._calendar.select_day(datetime_val.day)


class DateSelect(gtk.ToggleButton):
    """A more functional date selector"""

    _keys = map(keyval_from_name,("space", "KP_Space", "Return", "KP_Enter"))
    __gsignals__ = {'changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, ())}

    def __init__(self):
        """Construct a DateSelect from individual widgets."""
        gtk.ToggleButton.__init__(self)
        self.set_focus_on_click(False)

        hbox = gtk.HBox()
        arrow = gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_NONE)
        self._label = gtk.Label("None")
        self._label.set_alignment(0, 0.5)
        hbox.pack_start(self._label, False)
        hbox.pack_end(arrow, False)
        self.add(hbox)
        self.show_all()

        self._popup = _DateSelectPopup()

        self.connect("toggled", self._on_button_toggled)
        self._popup.connect("date-selected", lambda w,d: self.set_date(d))
        self._popup.connect("popdown", lambda w: self.set_active(False))

        self._date = None

    def _on_button_toggled(self, widget):
        if self.get_active():
            self._popup.set_date(self._date)
            self._popup.popup(self)

    # public interface
    def get_date(self):
        """Return the selected date"""
        return self._date

    def set_date(self, datetime_val):
        """ Set the active item via its index.

        Keyword arguments:
        datetime_val         -- the date to set
        """
        self._date = datetime_val
        self._label.set_text(datetime_to_friendly(self._date))
        self.emit("changed")
