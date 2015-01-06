import sys
import pkgutil
import importlib
import inspect
from itertools import izip_longest, izip
from collections import namedtuple, OrderedDict


class LoadError(ImportError):
    def __init__(self, msg, item):
        self._item = item
        super(LoadError, self).__init__(msg)


class Collector(object):
    def __init__(self, include=None, exclude=None, errors=False, path=None):
        self._include = include or []
        self._exclude = exclude or []
        self._errors = [] if errors else None
        self._path = path

    def _is_valid(self, load_info, parent=None):
        loader, name, ispkg = load_info
        valid = True
        full_name = PyItem.get_full_name(name, parent=parent)
        if self._exclude:
            valid = not full_name in self._exclude
        if valid and self._include:
            valid = full_name in self._include
        return valid

    def iter_items(self, path=None, parent=None):
        _path = path if path is not None else self._path
        for info in pkgutil.iter_modules(path=_path):
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
    # Is it better to use object.__dict__ directly? (for instances, classes,
    # modules)
    # Use getattr with keys of __dict__ due to __slots__!
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


def ensure_in_sys_path(path):
    for p in reversed(path):
        if p not in sys.path:
            sys.path.insert(0, p)

def pyitems(**config):
    if config.get('path'):
        ensure_in_sys_path(config['path'])
    return Collector(**config).iter_items()
