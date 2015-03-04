import sys
import pkgutil
import importlib
import inspect
import logging
from itertools import izip_longest, izip
from collections import namedtuple, OrderedDict


class LoadError(ImportError):
    def __init__(self, msg, item):
        self._item = item
        super(LoadError, self).__init__(msg)


class Collector(object):
    def __init__(self, include=None, exclude=None, errors=False, paths=None):
        self._include = include or []
        self._exclude = exclude or []
        self._errors = [] if errors else None
        self._paths = paths

    def _is_needed(self, name, parent=None):
        valid = True
        full_name = PyItem.get_full_name(name, parent=parent)
        if self._exclude:
            valid = not full_name in self._exclude
        if valid and self._include:
            valid = full_name in self._include
        return valid

    def iter_items(self, paths=None, parent=None):
        _paths = paths if paths is not None else self._paths
        print "iterating by paths %s..." % _paths
        #! point 1
        for importer, name, is_pkg in pkgutil.iter_modules(path=_paths):
            try:
                if self._is_needed(name, parent=parent):
                    N = Package if is_pkg else Module
                    yield N(name, parent=parent, collector=self)
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
    def __init__(self, name, **kwargs):
        self._name = name
        self._instance = kwargs.get('instance')
        self._parent = kwargs.get('parent')
        # Is "children" appropriate here?
        # Even action (function) is a namespace, but I hide it :)
        self._collector = kwargs.get('collector')
        self._children = None

    @staticmethod
    def get_full_name(name, parent=None):
        if parent is None:
            return name
        else:
            return '{}.{}'.format(parent.full_name, name)

    @property
    def name(self):
        return self._name

    @property
    def full_name(self):
        return self.get_full_name(self._name, self._parent)

    @property
    def children(self):
        #dir(self.instance)?
        #it returns strings!
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

    def __str__(self):
        return "{} '{}'".format(type(self).__name__, self.full_name)


class SearchPaths(PyItem):
    def __init__(self, name, **kwargs):
        paths = kwargs.get('paths')
        if paths:
            self.ensure_in_sys_path(paths)

    @staticmethod
    def ensure_in_sys_path(paths):
        for p in reversed(paths):
            #! point
            if p not in sys.path:
                sys.path.insert(0, p)


class Namespace(PyItem):
    # Is it better to use object.__dict__ directly? (for instances, classes,
    # modules)
    # Use getattr with keys of __dict__ due to __slots__!
    @property
    def children(self):
        if self._children is None:
            #! point 2
            functions = inspect.getmembers(self.instance, inspect.isfunction)
            actions = [Action(name, instance=instance, parent=self)
                       for name, instance in functions]
            self._children = actions
        return self._children

    def _load_module(self):
        try:
            #! point
            print "loading '%s'..." % self.full_name
            return importlib.import_module(self.full_name)
        except Exception as exc:
            msg = "Error has occured during import of {}: {}".format(
                self.full_name, exc
            )
            logging.error(msg, exc_info=True)
            raise LoadError(msg, self)

    @property
    def instance(self):
        if self._instance is None:
            self._instance = self._load_module()
        return self._instance


class Package(Namespace):
    @property
    def children(self):
        super(Package, self).children
        #! point 1+
        print "iterating for pkg __path__ %s..." % self.instance.__path__
        self._children.extend(i for i in self.collector.iter_items(
            self.instance.__path__, parent=self))
        return self._children


class Module(Namespace):
    pass


"""
Examples:
  # run mypkg/__main__
  pye --x-debug --x-bust-cache mypkg --x-run

  # run mypkg/mod[if ...__main__...]
  pye --x-debug --x-bust-cache mypkg.mod --x-run

  # write to stdout result of func (as str)
  pye mypkg.func arg --opt=123 --x-print

  # build instance of class and build subcommands from it (and autocomplete!)
  pye mod.classname arg --opt=123 --x-enum method marg --mopt


  # Do I need smth like this?
  pye mod.foo fooarg --x-bind=bararg --x-more mod.bar bararg --x-run
"""

ArgValue = namedtuple('ArgValue', 'data is_default')
class Action(PyItem):
    def __init__(self, name, instance=None, parent=None):
        super(Action, self).__init__(name, instance=instance, parent=parent)
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


def ensure_in_sys_path(paths):
    for p in reversed(paths):
        #! point
        if p not in sys.path:
            sys.path.insert(0, p)

def pyitems(**config):
    if config.get('paths'):
        ensure_in_sys_path(config['paths'])
    return Collector(**config).iter_items()
