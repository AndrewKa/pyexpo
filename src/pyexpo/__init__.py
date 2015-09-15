import pkgutil
import inspect
import sys
import StringIO
import importlib
from collections import OrderedDict, namedtuple
import itertools
import runpy
#pyclbr?


#TODO: put class decorator for debug print...


class NoChildFound(Exception):
    pass


class PySpaceObject(object):
    """This class can acts like null object"""
    # it makes sense to convert these class-level fields to properties
    # and incorporate logging to them

    callable = True

    """Return tuples of args/kwargs. In case of args
    tuple is one-element
    """
    arguments = ()

    description = ''

    children = ()

    def call(self, *args, **kwargs):
        pass

    def __init__(self, **kwargs):
        prohibited_attrs = {k for k in self.__dict__
                            if not k.startswith('_')}
        error_attrs = prohibited_attrs & set(kwargs)
        if error_attrs:
            raise ValueError("Cannot override in init these attrs: %s" % error_attrs)

        error_args = {k for k in kwargs
                      if k.startswith('_')}
        if error_args:
            raise ValueError("Cannot introduce non-public attrs: %s" % error_args)

        self.__dict__.update(kwargs)

    def __getitem__(self, name):
        raise KeyError("Cannot find child '%s'" % name)

    def __str__(self):
        #May be it's worth to have constructor to instantiate from simple string?
        #Like these:
        #   Module('foo.subfoo.bobo') or space.create('foo.subfoo.bobo')
        return "<pyexpo.%s '%s' at 0x%x>" % (type(self).__name__, self.name, id(self))


#class ErrorProcessor(object):
#    REPLACE = 'replace'
#    IGNORE = 'ignore'
#    RAISE = 'raise'
#    def pass():
#        pass
#        #TODO: introduce misc error-processing (replace, ignore, raise)
#        #I can return here or later PySpaceObject with err description


class ModuleBase(PySpaceObject):

    def __init__(self, **kwargs):
        self._mute = True
        self._out = StringIO.StringIO()
        self._err = StringIO.StringIO()
        super(ModuleBase, self).__init__(**kwargs)

    @staticmethod
    def _new_child_data():
        return {'items': OrderedDict()}

    def _child_of_type(self, name, type_, default=NoChildFound):

        def new_value(d):
            nv = default() if callable(default) else default
            d['items'][type_] = nv
            return nv

        data = self._child_stuff.get(name)
        if not data:
            if default is NoChildFound:
                raise NoChildFound("Cannot find child with name '%s'" % name)
            else:
                self._child_stuff[name] = data = self._new_child_data()
                return new_value(data)

        for t, v in data['items'].iteritems():
            if t == type_ or issubclass(t, type_):
                return v
        else:
            if default is NoChildFound:
                raise NoChildFound(
                    "Cannot find child with "
                    "name '%s' and type '%s'" % (name, type_))
            else:
                return new_value(data)

    def _set_child_stuff(self):
        if hasattr(self, '_child_stuff'):
            return self._child_stuff

        self._child_stuff = OrderedDict()
        if hasattr(self.instance, '__path__'):
            iter_paths = pkgutil.iter_modules(self.instance.__path__)
            # NOTE: importer is the same for all children
            for importer, name, is_pkg in iter_paths:
                self._child_stuff[name] = data = self._new_child_data()
                Cls = Package if is_pkg else Module
                data['items'][Cls] = Cls(name=self._full_child_name(name))

        self._set_actions()

    def _create_mod_instance(self):
        stdout, stderr = sys.stdout, sys.stderr
        if self._mute:
            sys.stdout, sys.stderr = self._out, self._err
        try:
            return importlib.import_module(self.name)
        except ImportError as exc:
            print "Loading %s error:" % self.name, exc
            #TODO: introduce misc error-processing (replace, ignore, raise)
            #I can return here or later PySpaceObject with err description
            return
        finally:
            sys.stdout, sys.stderr = stdout, stderr

    def _full_child_name(self, name):
        return '{}.{}'.format(self.name, name)

    @property
    def instance(self):
        if not hasattr(self, '_instance'):
            self._instance = self._create_mod_instance()
        return self._instance

    @property
    def children(self):
        """Precedence in odinary child-query will be given to modules
        (as opposed to function)
        """
        self._set_child_stuff()
        #Is generic inspect.getmembers(self.instance) better suited here?
        for name in self._child_stuff:
            for t in (ModuleBase, Action):
                try:
                    yield self._child_of_type(name, t)
                except NoChildFound:
                    pass

    def _set_actions(self):
        if hasattr(self, '_action_traversed'):
            return

        #Is generic inspect.getmembers(self.instance) better suited here?
        for name, instance in inspect.getmembers(self.instance, inspect.isfunction):
            new_action = lambda: Action(
                name=self._full_child_name(name),
                instance=instance)
            self._child_of_type(name, Action, default=new_action)

        self._action_traversed = True

    def __getitem__(self, name):
        self._set_child_stuff()
        if name in self._child_stuff:

            try:
                return self._child_of_type(name, ModuleBase)
            except NoChildFound:
                return self._child_of_type(name, Action)

        return super(ModuleBase, self).__getitem__(name)

    def call(self, *args, **kwargs):
        #
        #NOTE: File can be loaded twice!
        #TODO: prevent second load! Use already loaded file!
        #

        # alternative:
        #path = inspect.getsourcefile(self.instance)
        #context = {'__name__': '__main__'}
        #execfile(path, context)

        runpy.run_module(self.name, run_name='__main__')
        # explore internals of https://docs.python.org/2/library/runpy.html


class Module(ModuleBase):
    HAS_PATHS = False


class Package(ModuleBase):
    HAS_PATHS = True
    
    @property
    def callable(self):
        self._set_child_stuff()
        try:
            m = self._child_of_type(
                '__main__',
                Module
            )
            return bool(m)
        except NoChildFound:
            return False


class ActionArguments(object):
    """Thin wrapper on ArgSpec.
    ArgSpec reminder:
    # foo = lambda a, b, k1=1, k2=2, *args, **kwargs: None
    # inspect.getargspec(foo) #=>
    # ArgSpec(args=['a', 'b', 'k1', 'k2'],
    #         varargs='args',
    #         keywords='kwargs',
    #         defaults=(1, 2))
    """
    def __init__(self, func):
        self._as = inspect.getargspec(func)

    @property
    def args(self):
        if self._as.defaults is None:
            return self._as.args
        else:
            return self._as.args[:-len(self._as.defaults)]

    @property
    def kwargs(self):
        if self._as.defaults is None:
            return tuple()
        else:
            return tuple(itertools.izip(
                self._as.args[-len(self._as.defaults):],
                self._as.defaults
            ))

    @property
    def args_name(self):
        return self._as.varargs

    @property
    def kwargs_name(self):
        return self._as.keywords


class Action(PySpaceObject):

    @property
    def arguments(self):
        return ActionArguments(self.instance)

    def call(self, *args, **kwargs):
        return self.instance(*args, **kwargs)


def paths_to_sys(paths):
    for path in paths:
        if path not in sys.path:
            sys.path.insert(0, path)


class PySpaceInstance(object):
    def __init__(self, paths):
        self.__path__ = paths


class PySpace(ModuleBase):

    def __init__(self, only_paths=None):
        self._only = only_paths
        if self._only:
            paths_to_sys(self._only)
        self._instance = PySpaceInstance(paths=only_paths)

    def _full_child_name(self, name):
        return name

    @property
    def instance(self):
        return self._instance


def explore_paths(paths):
    return PySpace(only_paths=paths).children


