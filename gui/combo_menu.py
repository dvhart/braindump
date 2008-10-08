#    Filename: combo_menu.py
# Description: Provide a flat combo box for use in panels and titles
# 2008-Oct-02: Initial version

from gobject import *
import gtk
from gtk.gdk import keyval_from_name
from logging import debug, info, warning, error, critical

class ComboMenu(gtk.ToggleButton):
    """A Combo Box with a flat (RELIEF_NONE) look.

    This object attempts a similar, but not identical, interface as the
    gtk.ComboBox while allowing the user to store useful objects in the list.
    On change the "changed" signal is emitted.
    """

    _keys = map(keyval_from_name,("space", "KP_Space", "Return", "KP_Enter"))
    __gsignals__ = {'changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,))}

    def __init__(self):
        """Construct a ComboMenu from individual widgets."""

        gtk.Button.__init__(self)
        self._items = []
        self._index = -1
        self._markup = "", ""
        self._data_func = lambda i: str(i)
        self.set_relief(gtk.RELIEF_NONE)

        self._hbox = gtk.HBox()
        self._arrow = gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_NONE)
        self._label = gtk.Label()
        self._label.set_alignment(0, 0.5)
        self._hbox.pack_start(self._label, False)
        self._hbox.pack_end(self._arrow, False)
        self.add(self._hbox)

        self._menu = gtk.Menu()
        self._menu.connect("deactivate", lambda w: gtk.ToggleButton.set_active(self, False))
        self._menu.attach_to_widget(self, None)

        self.connect("button_press_event", self._on_button_press)
        self.connect("key_press_event", self._on_key_press)

    def _set_text(self, item):
        self._label.set_markup(self._markup[0]+self._data_func(item)+self._markup[1])

    def _set_none(self):
        self._label.set_markup("")
        self._index = -1
        self.emit("changed", index)

    def _menu_pos(self, menu, data=None):
        x, y = self.window.get_origin()
        x += self.get_allocation().x
        y += self.get_allocation().y + self.get_allocation().height
        return (x, y, False)

    def _on_button_press(self, widget, event):
        gtk.ToggleButton.set_active(self, True)
        self._menu.set_size_request(-1, -1)
        width = max(self.allocation.width, self._menu.size_request()[0])
        self._menu.set_size_request(width, -1)
        self._menu.popup(None, None, self._menu_pos, event.button, event.time)

    def _on_key_press(self, widget, event):
        if event.keyval in self._keys:
            gtk.ToggleButton.set_active(self, True)
            self._menu.set_size_request(-1, -1)
            width = max(self.allocation.width, self._menu.size_request()[0])
            self._menu.set_size_request(width, -1)
            self._menu.popup(None, None, self._menu_pos, 1, event.time)
            return True
        return False

    def _on_activate(self, menuitem, index):
        self._set_text(self._items[index][0])
        self._index = index
        self.emit("changed", index)
        gtk.ToggleButton.set_active(self, False)

    # public interface
    def add_item(self, item):
        """Add an object to the list.

        The item will be paired with a menuitem whose label will be set via
        the data_func, which defaults to str(item).

        Keyword arguments:
        item          -- the object to add
        """
        menuitem = gtk.MenuItem(self._data_func(item))
        self._menu.append(menuitem)
        self._items.append((item, menuitem))
        menuitem.connect("activate", self._on_activate, len(self._items) - 1)
        menuitem.show()

    def remove_item(self, item):
        """ Remove an object from the list.

        Keyword arguments:
        item          -- the object to remove
        """
        for i,m in self._items:
            if i is item:
                if index is self._index:
                    self._set_none()
                del self._items[index]

    def get_active(self):
        """ Return the index of the active item.

        Here we override the ToggleButton's get_active method so we can more
        closely resemble a ComboBox.
        """
        return self._index

    def set_active(self, index):
        """ Set the active item via its index.

        Here we override the ToggleButton's set_active method so we can more
        closely resemble a ComboBox.  If the index is out of bounds, set the
        active item to None (-1).

        Keyword arguments:
        index         -- the index of the object to make active
        """
        if index == self._index:
            return
        if index >= 0 and index < len(self._items):
            self._items[index][1].activate()
            self._index = index
        else:
            self._set_none()

    def get_active_item(self):
        """ Return the active item."""
        if self._index >= 0:
            return self._items[self._index][0]
        return None

    def set_active_item(self, item):
        """ Set the active item.

        If item doesn't exist in the list, set active to None.

        Keyword arguments:
        item          -- the object to set active
        """
        for i,m in self._items:
            if i is item:
                m.activate()
                return
        self._set_none()

    def set_markup(self, start, end):
        """ Set the markup tags to wrap the button label with.

        Defaults to empty.  To make the button appear bold, use "<b>" and "</b>".

        Keyword arguments:
        start         -- the opening markup tag
        end           -- the closing markup tag
        """
        self._markup = start, end

    def set_data_func(self, func):
        """ Set the data_func for converting the items to strings.

        Keyword arguments:
        func          -- the function should accept an item and return a string
        """

        self._data_func = func
