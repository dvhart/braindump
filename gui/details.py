#    Filename: details.py
#      Author: Darren Hart <darren@dvhart.com>
# Description: a gtd object fields editor
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
# Copyright (C) Darren Hart, 2008
#
# 2008-Oct-03:	Initial version by Darren Hart <darren@dvhart.com>

import time
import datetime
import gtk, gtk.glade
from widgets import *
from context_table import *
import braindump.gtd
from logging import debug, info, warning, error, critical

class Details(WidgetWrapper):
    """ A form to display and edit the details of GTD objects.

    We're basically a Mediator for all the widgets that comprise the details
    form.  We also encapsulate appropriate methods that operate only on the
    subject object itself here.
    """

    def __init__(self, name, project_store, area_store):
        WidgetWrapper.__init__(self, name)
        self.__notes = GUI().get_widget("notes")
        self.__start = GUI().get_widget("start_date")
        self.__due = GUI().get_widget("due_date")
        self.__details_controls = GUI().get_widget("details_controls")
        self.__project_label = GUI().get_widget("parent_project_label")
        self.__project = GTDCombo("parent_project", project_store, ProjectNone())
        self.__area_label = GUI().get_widget("parent_area_label")
        self.__area = GTDCombo("parent_area", area_store, AreaNone())
        self.__contexts = ContextTable("context_table")
        self.__subject = None # the gtd object we're working with

        self.__notes.widget.get_buffer().connect("changed", self._on_notes_changed)
        self.__contexts.connect("changed", lambda w,c,a: self._on_context_toggled(c, a))

        # Set our initial size request as if all the widgets were visible
        width, height = self.__details_controls.widget.size_request()
        self.widget.set_size_request(width, -1)
        # Nothing visible until our subject is set
        self.__details_controls.widget.hide()
        self._show_task_widgets(False)
        self._show_project_widgets(False)

    def _show_project_widgets(self, show):
        if show:
            self.__area_label.widget.show()
            self.__area.widget.show()
        else:
            self.__area_label.widget.hide()
            self.__area.widget.hide()

    def _show_task_widgets(self, show):
        if (show):
            self.__project_label.widget.show()
            self.__project.widget.show()
            self.__contexts.widget.show()
        else:
            self.__project_label.widget.hide()
            self.__project.widget.hide()
            self.__contexts.widget.hide()

    def _on_notes_changed(self, buffer):
        # FIXME: consider adding a notes field to gtd.Base, or deriving each from gtd.AnnotatedBase
        if isinstance(self.__subject, gtd.Task) or isinstance(self.__subject, gtd.Project):
            self.__subject.notes = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())

    def _on_start_date_changed(self, dateedit):
        d = datetime.datetime.fromtimestamp(dateedit.get_time())
        self.__subject.start_date = d
        debug(d)

    def _on_due_date_changed(self, dateedit):
        d = datetime.datetime.fromtimestamp(dateedit.get_time())
        self.__subject.due_date = d
        debug(d)

    # FIXME, merge these two
    # FIXME, update gtd code so we only have to set the parent here (not remove self from parent)
    def _on_parent_project_changed(self, project_combo):
        project = self.get_parent()
        if isinstance(self.__subject, gtd.Task) and not self.__subject.project == project :
            self.__subject.project.remove_task(self.__subject)
            if isinstance(project, gtd.Project):
                project.add_task(self.__subject)
            self.__subject.project = project

    def _on_parent_area_changed(self, area_combo):
        area = self.get_parent()
        if isinstance(self.__subject, gtd.Project) and not self.__subject.area == area:
            self.__subject.area.remove_project(self.__subject)
            if isinstance(area, gtd.Area):
                area.add_project(self.__subject)
            self.__subject.area = area

    def _on_context_toggled(self, context, active):
        if isinstance(self.__subject, gtd.Task):
            if active:
                self.__subject.add_context(context)
            else:
                self.__subject.remove_context(context)

    def set_subject(self, subject):
        self.__subject = subject
        notes = ""
        start_date = 0 # FIXME: this sets it to today()... we really want blank... (3 others like this)
        due_date = 0
        contexts = [] # only relevant for tasks

        # FIXME: mostly redundant for Task and Project...
        # o maybe change ftd base to have a "parent" field
        if not isinstance(subject, gtd.Task) and not isinstance(subject, gtd.Project):
            self.__details_controls.widget.hide()
            self._show_task_widgets(False)
            self._show_project_widgets(False)
        else:
            # common fields
            notes = self.__subject.notes
            # FIXME: might be better to wrap the widget so we can simply use datetime objects here
            if self.__subject.start_date:
                # FIXME, this can throw an exception if a bad date was stored, or out of range (1969...)
                start_date = int(time.mktime(self.__subject.start_date.timetuple()))
                start_date = 0
            if self.__subject.due_date:
                due_date = int(time.mktime(self.__subject.due_date.timetuple()))

            # task and project specific fields
            if isinstance(subject, gtd.Task):
                contexts = self.__subject.contexts
                self.__project.set_active(self.__subject.project)
                self._show_project_widgets(False)
                self.__details_controls.widget.show()
                self._show_task_widgets(True)
            elif isinstance(subject, gtd.Project):
                self.__area.set_active(self.__subject.area)
                self._show_task_widgets(False)
                self.__details_controls.widget.show()
                self._show_project_widgets(True)

        self.__notes.widget.get_buffer().set_text(notes)
        self.__start.widget.set_time(start_date)
        self.__due.widget.set_time(due_date)
        self.__contexts.set_active_contexts(contexts)

    def get_parent(self):
        if isinstance(self.__subject, gtd.Task):
            return self.__project.get_active()
        elif isinstance(self.__subject, gtd.Project):
            return self.__area.get_active()
        return None
