import sys
import pkgutil
import importlib
import inspect
from itertools import izip_longest, izip
from collections import namedtuple
try:
    from collections import OrderedDict
except ImportError:
    from .ordereddict import OrderedDict


#useful links:
#http://www.python.org/dev/peps/pep-0302/
#http://stackoverflow.com/questions/6943208/activate-a-virtualenv-with-a-python-script

# something to consider:
# * I can call class constructors and further operate on returned
#   object - just show methods of it!
# * Actually each returned value can be inspected if it wasn't None.
#   (as a kind of namespace)
# * So, in abstract manner I can state this:
#   * On any step I can get list of namespace/action
#   * If something is namespace then I can explore names of it
#   * If something is action then I can run it and it doesn't have children
#   * Python's module/package/object is a namespace,
#     and function is an action (but can be namespace also!).
# * I can specify --print-result and send to stdout returned from function
#   object's __str__ or __repr__
# * --explore-result command will continue to expose object's namespace


class LoadError(ImportError):
    def __init__(self, msg, item):
        self._item = item


class Collector(object):
    def __init__(self, include=None, exclude=None, errors=False, paths=None):
        self._include = include or []
        self._exclude = exclude or []
        self._errors = [] if errors else None
        self._paths = paths

    def _is_valid(self, load_info, parent=None):
        loader, name, ispkg = load_info
        valid = True
        full_name = PyItem.get_full_name(name, parent=parent)
        if self._exclude:
            valid = not full_name in self._exclude
        if valid and self._include:
            valid = full_name in self._include
        return valid

    def iter_items(self, paths=None, parent=None):
        _paths = paths if paths is not None else self._paths
        for info in pkgutil.iter_modules(path=_paths):
            try:
                if self._is_valid(info, parent=parent):
                    Namespace = PyPkg if info[2] else PyMod
                    i = Namespace(info[1], parent=parent, collector=self)
                    if self._errors is not None:
                        i._load_module()
                    #print 'Going to construct %s' % PyItem.get_full_name(info[1], parent=parent)
                    yield i
            except LoadError as exc:
                if self._errors is None:
                    raise
                else:
                    self._errors.append(exc._item)

    @property
    def load_errors(self):
        if self._errors is not None:
            return self._errors
        else:
            return []


class PyItem(object):
    def __init__(self, name, instance=None, parent=None, collector=None):
        self.name = name
        self._instance = instance
        self._parent = parent
        # Is "children" appropriate here?
        # Even action (function) is a namespace, but I hide it :)
        self._children = None
        self._collector = collector

    @staticmethod
    def get_full_name(name, parent=None):
        if parent is None:
            return name
        else:
            return '{}.{}'.format(parent.full_name, name)

    @property
    def full_name(self):
        return self.get_full_name(self.name, self._parent)

    @property
    def children(self):
        return []

    @property
    def instance(self):
        return self._instance

    @property
    def collector(self):
        if self._collector:
            return self._collector
        elif self._parent:
            return self._parent.collector
        else:
            self._collector = Collector()
            return self._collector


class PyNamespace(PyItem):
    @property
    def children(self):
        if self._children is None:
            functions = inspect.getmembers(self.instance, inspect.isfunction)
            actions = [PyAction(name, instance=instance, parent=self)
                       for name, instance in functions]
            self._children = actions
        return self._children

    def _load_module(self):
        try:
            return importlib.import_module(self.full_name)
        except Exception as exc:
            msg = "Error has occured during import of {}: {}".format(
                self.full_name, exc
            )
            raise LoadError(msg, self)

    @property
    def instance(self):
        if self._instance is None:
            self._instance = self._load_module()
        return self._instance


class PyPkg(PyNamespace):
    @property
    def children(self):
        if self._children is None:
            actions = super(PyPkg, self).children
            assert actions == self._children
            subs = []
            #iterator = pkgutil.iter_modules(path=self.instance.__path__)
            #for loader, name, ispkg in iterator:
            #    if _is_valid_pyitem(loader, name, ispkg):
            #        Item = PyPkg if ispkg else PyMod
            #        subs.append(Item(name, parent=self))
            for i in self.collector.iter_items(self.instance.__path__, parent=self):
                subs.append(i)
            self._children.extend(subs)
        return self._children

    def __str__(self):
        return "Package: " + self.full_name


class PyMod(PyNamespace):
    def __str__(self):
        return "Module: " + self.full_name


ArgValue = namedtuple('ArgValue', 'data is_default')
class PyAction(PyItem):
    #def __init__(self, name, parent=None):
    #    self.name = name
    #    self._parent = parent
    #    self._children = None
    def __init__(self, name, instance=None, parent=None):
        super(PyAction, self).__init__(name, instance=instance, parent=parent)
        self._action_args = self._extract_args()

    def _extract_args(self):
        spec = inspect.getargspec(self.instance)
        r_args = reversed(spec.args)
        r_defaults = reversed(spec.defaults if not spec.defaults is None else [])
        args = []
        vals = []
        not_specified = object()
        for arg, default in izip_longest(r_args, r_defaults, fillvalue=not_specified):
            args.append(arg)
            vals.append(
                ArgValue(default, not default is not_specified)
            )
        return OrderedDict(izip(reversed(args), reversed(vals)))

    def __call__(self, *args, **kwargs):
        self.instance(*args, **kwargs)

    def __str__(self):
        return "Action: " + self.full_name


def ensure_in_sys_path(paths):
    for path in reversed(paths):
        if path not in sys.path:
            sys.path.insert(0, path)

def pyitems(**config):
    if config.get('paths'):
        ensure_in_sys_path(config['paths'])
    return Collector(**config).iter_items()
