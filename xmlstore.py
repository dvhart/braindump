import os, os.path
import stat
import fnmatch
from xml.sax import saxutils, make_parser, handler
import uuid
from datetime import datetime
import gtd
from gtd import GTD
from logging import debug, info, warning, error, critical

# FIXME: should we make the dates TZ aware ?
# http://docs.python.org/lib/datetime-datetime.html
#_DATE_FORMAT = "%F %T"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# FIXME: I think in the end, we should eliminate the singleton GTD()
# and just return a gtd tree from here...
class XMLStore(object):
    __path = None

    def __init__(self):
        pass

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
        fd = open("xml/" + id_str + ".xml", "w")
        x = saxutils.XMLGenerator(fd)
        x.startDocument()
        self._simple_element(x, name, {"id":id_str}, obj.title)
        x.endDocument()

    def connect(self, tree):
        # new signals
        tree.sig_context_added.connect(self.save_context)
        tree.sig_task_added.connect(self.save_task)
        tree.sig_project_added.connect(self.save_project)
        tree.sig_area_added.connect(self.save_area)
        tree.sig_realm_added.connect(self.save_realm)

        # modify signals
        tree.sig_context_modified.connect(self.save_context)
        tree.sig_task_modified.connect(self.save_task)
        tree.sig_project_modified.connect(self.save_project)
        tree.sig_area_modified.connect(self.save_area)
        tree.sig_realm_modified.connect(self.save_realm)

        # remove signals
        tree.sig_context_removed.connect(self.delete_object)
        tree.sig_task_removed.connect(self.delete_object)
        tree.sig_project_removed.connect(self.delete_object)
        tree.sig_area_removed.connect(self.delete_object)
        tree.sig_realm_removed.connect(self.delete_object)

    def load(self, path):
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
        for file in os.listdir(path):
            if fnmatch.fnmatch(file, '*.xml'):
                print "Loading GTD object from:", os.path.join(path, file)
                parser.parse(os.path.join(path, file))

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
        id_str = str(task.id)

        start_date_str = ""
        due_date_str = ""
        if task.start_date:
            start_date_str = task.start_date.strftime(_DATE_FORMAT)
        if task.due_date:
            due_date_str = task.due_date.strftime(_DATE_FORMAT)

        fd = open("xml/" + id_str + ".xml", "w")
        x = saxutils.XMLGenerator(fd)
        x.startDocument()
        x.startElement("task", {"id":id_str})
        x.characters("\n")
        self._simple_element(x, "title", {}, task.title)
        self._simple_element(x, "notes", {}, task.notes)
        self._simple_element(x, "start_date", {}, start_date_str)
        self._simple_element(x, "due_date", {}, due_date_str)
        # FIXME: how do we want to represent project none?  should tasks
        # be required to have SOME project defined in the backing store?
        if not isinstance(task.project, gtd.ProjectNone):
            self._simple_element(x, "project_ref", {"id":str(task.project.id)})
        for c in task.contexts:
            if not isinstance(c, gtd.ContextNone):
                print "referencing context: ", c.title
                self._simple_element(x, "context_ref", {"id":str(c.id)})
        self._simple_element(x, "complete", {}, str(task.complete))
        x.endElement("task")
        x.endDocument()

    def save_project(self, project):
        debug("saving project: %s" % (project.title))
        debug("project area: %s" % (project.area))
        global _DATE_FORMAT
        id_str = str(project.id)

        start_date_str = ""
        due_date_str = ""
        if project.start_date:
            start_date_str = project.start_date.strftime(_DATE_FORMAT)
        if project.due_date:
            due_date_str = project.due_date.strftime(_DATE_FORMAT)

        fd = open("xml/" + id_str + ".xml", "w")
        x = saxutils.XMLGenerator(fd)
        x.startDocument()
        x.startElement("project", {"id":id_str})
        x.characters("\n")
        self._simple_element(x, "title", {}, project.title)
        self._simple_element(x, "notes", {}, project.notes)
        self._simple_element(x, "start_date", {}, start_date_str)
        self._simple_element(x, "due_date", {}, due_date_str)
        if not isinstance(project.area, gtd.AreaNone):
            self._simple_element(x, "area_ref", {"id":str(project.area.id)})
        self._simple_element(x, "complete", {}, str(project.complete))
        x.endElement("project")
        x.endDocument()

    def save_area(self, area):
        id_str = str(area.id)
        fd = open("xml/" + id_str + ".xml", "w")
        x = saxutils.XMLGenerator(fd)
        x.startDocument()
        x.startElement("area", {"id":id_str})
        x.characters("\n")
        self._simple_element(x, "title", {}, area.title)
        self._simple_element(x, "realm_ref", {"id":str(area.realm.id)})
        x.endElement("area")
        x.endDocument()

    def save_realm(self, realm):
        self._save_simple_element("realm", realm)


# ContentHandler, DTDHandler, EntityResolver, and ErrorHandler
# consider HandlerBase ?
class GTDContentHandler(handler.ContentHandler):
    __chars = ""     # the CDATA the parser has collected
    __subject = None # the object we are currently building
    __cache = {}     # a dict of objects we have seen referenced in the file and constructed

    def __init__(self):
        pass

    def startElement(self, name, attrs):
        print "\nStart element: ", name
        obj = None
        cached = False
        self.__chars = ""
        id = None
        id_str = attrs.get("id", None)
        if id_str:
            print "ID_STR: ", id_str
            id = uuid.UUID(id_str)

        if id in self.__cache:
            print "found", id, "in cache"
            cached = True
            obj = self.__cache[id]
        elif id: # if it doesn't have an id, it isn't a Primary object
            print id, "not in cache, generating"
            # Primary objects: task, project, area, realm, and context
            # Set the __subject object when first encountered
            if name == "task":
                obj = gtd.Task(id)
            elif name == "project":
                obj = gtd.Project(id)
            elif name == "area":
                obj = gtd.Area(id)
            elif name == "realm":
                obj = gtd.Realm(id)
            elif name == "context":
                obj = gtd.Context(id)

        # Reference objects: fetch or build them, then assign to the __subject
        if name == "context_ref":
            if not cached:
                obj = gtd.Context(id)
            self.__subject.add_context(obj)
        elif name == "project_ref":
            if not cached:
                obj = gtd.Project(id)
            self.__subject.project.remove_task(self.__subject)
            self.__subject.project = obj
            obj.add_task(self.__subject)
        elif name == "area_ref":
            if not cached:
                obj = gtd.Area(id)
            self.__subject.area.remove_project(self.__subject)
            self.__subject.area = obj
            obj.add_project(self.__subject)
        elif name == "realm_ref":
            if not cached:
                obj = gtd.Realm(id)
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
            print "adding %s %s to cache" % (name, id)
            self.__cache[id] = obj

        if name in ["task", "project", "area", "realm", "context"]:
            print "setting subject to", id
            self.__subject = obj


    def endElement(self, name):
        global _DATE_FORMAT
        print "End element: ", name
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
            complete = False
            if chars == "True":
                complete = True
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
        sys.stderr.write("\%s\n" % (exception))
