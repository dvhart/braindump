import os, os.path
#import stat
import fnmatch
from xml.sax import saxutils, make_parser, handler
from xml.sax._exceptions import *
import uuid
from datetime import datetime
import gtd
from gtd import GTD
from logging import debug, info, warning, error, critical
import sys

# FIXME: should we make the dates TZ aware ?
# http://docs.python.org/lib/datetime-datetime.html
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# FIXME: I think in the end, we should eliminate the singleton GTD()
# and just return a gtd tree from here...
class XMLStore(object):

    def __init__(self):
        self.__path = None

    def _obj_filename(self, obj):
        return os.path.join(self.__path, str(obj.id) + ".xml")

    def _simple_element(self, x, name, attrs, chars=None):
        x.startElement(name, attrs)
        if (chars):
            x.characters(chars)
        x.endElement(name)
        x.characters("\n") # FIXME: what is the portable way to do this?

    # FIXME: this is now of dubious utility (only context and realm can use it..., and probably
    # shouldn't in favor of a more consistent xml file format (<title>...) in every object...
    def _save_simple_element(self, name, obj):
        id_str = str(obj.id)
        fd = open(self._obj_filename(obj), "w")
        try:
            x = saxutils.XMLGenerator(fd)
            x.startDocument()
            self._simple_element(x, name, {"id":id_str}, obj.title)
            x.endDocument()
        finally:
            fd.close()

    def connect(self, tree):
        # new signals
        tree.connect("context_added", lambda t,o: self.save_context(o))
        tree.connect("task_added", lambda t,o: self.save_task(o))
        tree.connect("project_added", lambda t,o: self.save_project(o))
        tree.connect("area_added", lambda t,o: self.save_area(o))
        tree.connect("realm_added", lambda t,o: self.save_realm(o))

        # modify signals
        tree.connect("context_modified", lambda t,o: self.save_context(o))
        tree.connect("task_modified", lambda t,o: self.save_task(o))
        tree.connect("project_modified", lambda t,o: self.save_project(o))
        tree.connect("area_modified", lambda t,o: self.save_area(o))
        tree.connect("realm_modified", lambda t,o: self.save_realm(o))

        # remove signals
        tree.connect("context_removed", lambda t,o: self.delete_object(o))
        tree.connect("task_removed", lambda t,o: self.delete_object(o))
        tree.connect("project_removed", lambda t,o: self.delete_object(o))
        tree.connect("area_removed", lambda t,o: self.delete_object(o))
        tree.connect("realm_removed", lambda t,o: self.delete_object(o))

    def load(self, path):
        if path is None:
            critical("no path specified")
        elif not os.path.exists(path):
            critical("specified path does not exist: %s" % (path))
        self.__path = path

        ch = GTDContentHandler()
        eh = GTDErrorHandler()
        parser = make_parser()
        parser.setFeature(handler.feature_namespaces, 0)
        parser.setContentHandler(ch)
        parser.setErrorHandler(eh)
        #parser.setDTDHandler(?)
        #parser.setEntityResolver(?)

        # iterate on every xml file in "path"
        for file in os.listdir(self.__path):
            if fnmatch.fnmatch(file, '*.xml'):
                debug("Loading GTD object from: %s" % (os.path.join(self.__path, file)))
                try:
                    parser.parse(os.path.join(self.__path, file))
                except SAXParseException, e:
                    error("SAXParseException: %s" % (e))
                    error("The file was not created (or saved) properly.  The "
                          "most likely cause is a missing closing element tag, "
                          "such as </task>.")
                except:
                    e = sys.exc_info()[1]
                    error("Unhandled exception: %s" % (e))
                

    def save(self, gtd_tree):
        critical("not implemented")

    def delete_object(self, obj):
        filename = self._obj_filename(obj)
        if os.path.exists(filename):
            os.unlink(filename)
        else:
            warning("Couldn't delete %s" % (filename))

    def save_context(self, context):
        self._save_simple_element("context", context)

    def save_task(self, task):
        global _DATE_FORMAT
        if not isinstance(task, gtd.Task):
            critical("task is a %s" % (task.__class__.__name__))
        debug("saving task: title=%s id=%s" % (task.title, task.id))
        id_str = str(task.id)

        start_date_str = ""
        due_date_str = ""
        complete_str = ""
        if task.start_date:
            start_date_str = task.start_date.strftime(_DATE_FORMAT)
        if task.due_date:
            due_date_str = task.due_date.strftime(_DATE_FORMAT)
        if task.complete:
            complete_str = task.complete.strftime(_DATE_FORMAT)

        fd = open(self._obj_filename(task), "w")
        try:
            x = saxutils.XMLGenerator(fd)
            x.startDocument()
            x.startElement("task", {"id":id_str})
            x.characters("\n")
            self._simple_element(x, "title", {}, task.title)
            self._simple_element(x, "notes", {}, task.notes)
            self._simple_element(x, "start_date", {}, start_date_str)
            self._simple_element(x, "due_date", {}, due_date_str)
            debug("saving project")
            if not isinstance(task.project, gtd.ProjectNone):
                debug("task project is a %s" % (task.project.__class__.__name__))
                debug("referencing project: title=%s id=%s" % (task.project.title, task.project.id))
                if not isinstance(task.project, gtd.Project):
                    critical("task.project is a %s" % (task.project.__class__.__name__))
                self._simple_element(x, "project_ref", {"id":str(task.project.id)},
                                     task.project.title)
            debug("saving contexts")
            for c in task.contexts:
                if isinstance(c, gtd.ContextNone):
                    error("ContextNone should not be stored in the task!")
                    continue
                debug("referencing context: %s" % (c.title))
                self._simple_element(x, "context_ref", {"id":str(c.id)}, c.title)
            self._simple_element(x, "complete", {}, complete_str)
            x.endElement("task")
            x.endDocument()
        except:
                    e = sys.exc_info()[1]
                    error("Unhandled exception: %s while trying to save %s" %
                          (e, id_str))
        finally:
            fd.close()

    def save_project(self, project):
        debug("saving project: %s" % (project.title))
        debug("project area: %s" % (project.area))
        global _DATE_FORMAT
        id_str = str(project.id)

        start_date_str = ""
        due_date_str = ""
        complete_str = ""
        if project.start_date:
            start_date_str = project.start_date.strftime(_DATE_FORMAT)
        if project.due_date:
            due_date_str = project.due_date.strftime(_DATE_FORMAT)
        if project.complete:
            complete_str = project.complete.strftime(_DATE_FORMAT)

        fd = open(self._obj_filename(project), "w")
        try:
            x = saxutils.XMLGenerator(fd)
            x.startDocument()
            x.startElement("project", {"id":id_str})
            x.characters("\n")
            self._simple_element(x, "title", {}, project.title)
            self._simple_element(x, "notes", {}, project.notes)
            self._simple_element(x, "start_date", {}, start_date_str)
            self._simple_element(x, "due_date", {}, due_date_str)
            if not isinstance(project.area, gtd.AreaNone):
                self._simple_element(x, "area_ref", {"id":str(project.area.id)},
                                     project.area.title)
            self._simple_element(x, "complete", {}, complete_str)
            x.endElement("project")
            x.endDocument()
        finally:
            fd.close()

    def save_area(self, area):
        id_str = str(area.id)
        fd = open(self._obj_filename(area), "w")
        try:
            x = saxutils.XMLGenerator(fd)
            x.startDocument()
            x.startElement("area", {"id":id_str})
            x.characters("\n")
            self._simple_element(x, "title", {}, area.title)
            self._simple_element(x, "realm_ref", {"id":str(area.realm.id)},
                                 area.realm.title)
            x.endElement("area")
            x.endDocument()
        finally:
            fd.close()

    def save_realm(self, realm):
        self._save_simple_element("realm", realm)


# ContentHandler, DTDHandler, EntityResolver, and ErrorHandler
# consider HandlerBase ?
class GTDContentHandler(handler.ContentHandler):

    def __init__(self):
        self.__chars = ""     # the CDATA the parser has collected
        self.__subject = None # the object we are currently building
        self.__cache = {}     # a dict of objects we have seen referenced in the file and constructed

    def startElement(self, name, attrs):
        debug("Start element: %s" % (name))

        obj = None
        cached = False
        self.__chars = ""
        id = None
        id_str = attrs.get("id", None)
        if id_str:
            debug("ID_STR: %s" % (id_str))
            id = uuid.UUID(id_str)

        if id in self.__cache:
            debug("found %s in cache." % (id))
            cached = True
            obj = self.__cache[id]
        elif id: # if it doesn't have an id, it isn't a Primary object
            debug("%s not in cache, generating." % (id))
            # Primary objects: task, project, area, realm, and context
            # Set the __subject object when first encountered
            if name == "task":
                obj = gtd.Task.create(id)
            elif name == "project":
                obj = gtd.Project.create(id)
            elif name == "area":
                obj = gtd.Area.create(id)
            elif name == "realm":
                obj = gtd.Realm.create(id)
            elif name == "context":
                obj = gtd.Context.create(id)

        # Reference objects: fetch or build them, then assign to the __subject
        if name == "context_ref":
            if not cached:
                obj = gtd.Context.create(id)
            self.__subject.add_context(obj)
        elif name == "project_ref":
            if not cached:
                obj = gtd.Project.create(id)
            self.__subject.project.remove_task(self.__subject)
            self.__subject.project = obj
            obj.add_task(self.__subject)
        elif name == "area_ref":
            if not cached:
                obj = gtd.Area.create(id)
            self.__subject.area.remove_project(self.__subject)
            self.__subject.area = obj
            obj.add_project(self.__subject)
        elif name == "realm_ref":
            if not cached:
                obj = gtd.Realm.create(id)
            self.__subject.realm.remove_area(self.__subject)
            self.__subject.realm = obj
            obj.add_area(self.__subject)

        # Elements we do nothing with on startElement
        # notes
        # start_date
        # due_date
        # complete

        # FIXME: yulk! maybe we don't event *_ref, they might be just fine using
        # <context id="sdsadada"/> inside subject elements...
        if not cached and name in ["task", "project", "area", "realm", "context", "project_ref", "area_ref", "realm_ref", "context_ref"]:
            debug("adding %s %s to cache" % (name, id))
            self.__cache[id] = obj

        if name in ["task", "project", "area", "realm", "context"]:
            debug("setting subject to" % (id))
            self.__subject = obj


    def endElement(self, name):
        global _DATE_FORMAT
        debug("End element: %s" % (name))
        chars = ' '.join(self.__chars.split())
        self.__chars = ""

        if name in ["task", "project", "area"]:
            self.__subject = None
        elif name in ["realm", "context"]: # hrm... perhaps these should just have a <title> tag anyway..
            self.__subject.title = chars
            self.__subject = None
        elif name == "title":
            self.__subject.title = chars
        elif name == "notes":
            self.__subject.notes = chars
        elif name == "start_date":
            if chars:
                self.__subject.start_date = datetime.strptime(chars, _DATE_FORMAT)
        elif name == "due_date":
            if chars:
                self.__subject.due_date = datetime.strptime(chars, _DATE_FORMAT)
        elif name == "complete":
            complete = None
            if chars:
                complete = datetime.strptime(chars, _DATE_FORMAT)
            self.__subject.complete = complete

        # Elements we do nothing with on endElement
        # *_ref

    def characters(self, content):
        if self.__subject:
            self.__chars = self.__chars + content

class GTDErrorHandler(handler.ErrorHandler):
    def __init__(self):
        pass

    def error(self, exception):
        error("\%s\n" % (exception))
