#    Filename: date_select.py
# Description: a more functional date selector
#
# 2008-Oct-02: Initial version

from gobject import *
import gtk
from gtk import gdk
from gtk.gdk import keyval_from_name
from friendly_date import *
from logging import debug, info, warning, error, critical

class _DateSelectPopup(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)

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

        # build the popup widgets
        self._popup = gtk.Window(gtk.WINDOW_POPUP)
        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        vbox = gtk.VBox()
        self.date_calendar = gtk.Calendar()
        date_none = gtk.Button("None")
        date_today = gtk.Button("Today")
        date_tomorrow = gtk.Button("Tomorrow")
        date_this_friday = gtk.Button("This Friday")
        date_next_week = gtk.Button("Next Week")

        # assemble the popup
        frame.add(vbox)
        vbox.pack_start(self.date_calendar)
        vbox.pack_start(date_none)
        vbox.pack_start(date_today)
        vbox.pack_start(date_tomorrow)
        vbox.pack_start(date_this_friday)
        vbox.pack_start(date_next_week)
        self._popup.add(frame)

        # connect the signals
        self.connect("toggled", self._on_button_toggled)
        self._popup.connect("button-press-event", self._on_popup_button_press)
        self.date_calendar.connect("day-selected", self._on_day_selected)
        date_none.connect("clicked", self._on_date_button_clicked, "None")
        date_today.connect("clicked", self._on_date_button_clicked, "Today")
        date_tomorrow.connect("clicked", self._on_date_button_clicked, "Tomorrow")
        date_this_friday.connect("clicked", self._on_date_button_clicked, "This Friday")
        date_next_week.connect("clicked", self._on_date_button_clicked, "Next Week")

        self._date = None

    def popdown(self):
        self._popup.grab_remove()
        self._popup.hide_all()
        self.set_active(False)

    def _popup_grab_window(self):
        activate_time = 0L
        if gdk.pointer_grab(self._popup.window, True,
                         gdk.BUTTON_PRESS_MASK | 
                         gdk.BUTTON_RELEASE_MASK |
                         gdk.POINTER_MOTION_MASK,
                         None, None, activate_time) == 0:
            if gdk.keyboard_grab(self._popup.window, True, activate_time) == 0:
                return True
            else:
                self._popup.window.get_display().pointer_ungrab(activate_time);
                return False
        return False

    def popup(self):
        x, y = self.window.get_origin()
        x += self.get_allocation().x
        y += self.get_allocation().y + self.get_allocation().height
        self._popup.move(x, y)
        self._popup.show_all()

        if not self._popup_grab_window():
            self._popup.hide_all()

        self._popup.grab_add()


    def _on_popup_button_press(self, window, event):
        hide = False

        # check if we clicked outside the popup
        w, h = self._popup.get_size()
        x = event.x
        y = event.y
        if x < 0 or x > w or y < 0 or y > h:
            hide = True

        # check if we clicked on another widget in our app
        toplevel = event.window.get_toplevel()
        parent = self.date_calendar.get_parent_window()
        if toplevel != parent:
            hide = True

        if hide:
            self.popdown()

    # FIXME: close the popup if esc is pressed
    def _on_popup_key_press(self, popup, event):
        pass

    # FIXME: find a way to popup on button pressed, not just toggled
    def _on_button_toggled(self, widget):
        if self.get_active():
            self.popup()
        else:
            self._hide_popup()

    def _on_day_selected(self, cal):
        self._popup.hide()
        self.set_active(False)
        year, month, day = cal.get_date()
        datetime_val = datetime(year, month + 1, day)
        datetime_val = datetime_ceiling(datetime_val)
        self.set_date(datetime_val)

    def _on_date_button_clicked(self, btn, friendly_str):
        self._popup.hide()
        self.set_active(False)
        datetime_val = friendly_to_datetime(friendly_str)
        self.set_date(datetime_val)

    # public interface
    # FIXME: add an api to manage the date shortcut buttons
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
