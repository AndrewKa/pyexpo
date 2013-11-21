import os
import sys
import pkgutil
import importlib
import inspect
import argparse
from itertools import izip_longest, izip
from collections import defaultdict, namedtuple
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from .datastructures import DefaultOrderedDict


#useful links:
#http://www.python.org/dev/peps/pep-0302/
#http://stackoverflow.com/questions/6943208/activate-a-virtualenv-with-a-python-script

# something to consider:
# * I can call class constructors and further operate on returned
#   object - just show methods of it!
# * Actually each returned value can be inspected if it wasn't None.
# * So, in abstract manner I can state this:
#   * On any step I can get list of namespace/action
#   * If something is namespace then I can explore names of it
#   * If something is action then I can run it and it doesn't have children
#   * Python's module/package/object is a namespace,
#     and function is an action.


# new (2013.10.10):
# *  For specified search paths show available packages/modules
#    (Which info should be outputted here?)
# Some description:
# 1. for search_path: iter_modules -->  (importer, name, ispkg)
# 2. import package/module, getmembers(functions/modules)
# 3. split:
# 3. 1. for functions: get functions and their args description
#    2. for package: repeat 2, 3

# "search path" is a flat search space with ordinary python rules

# CLI scheme:
# main -> parser <intro point>
#      -> subparsers
#             package1 -> parser
#                      -> subparsers
#                             subpackage1 -> parser
#                                         -> subparsers
#                                                function1 -> parser
#                             module1 -> parser
#                                     -> subparsers
#                                             function1 -> parser
#                             function1 -> parser
#             package2 -> parser
#                      -> subparsers
#             module1 -> parser
#                     -> subparsers
#                             function1 -> parser

## get packages/modules for all search paths:
#for loader, name, ispkg in pkgutil.iter_modules(path=['./expo/tests/path1']):
#     print loader, name, ispkg 
##output:
##<pkgutil.ImpImporter instance at 0x2aa2368> hello False
##<pkgutil.ImpImporter instance at 0x2aa2368> scripts True
#
## get functions
#pkg_or_module = __import__('scripts')
#inspect.getmembers(pkg_or_module, inspect.isfunction) 
##output:
##[('foo', <function scripts.foo>)]
#
## get package's modules/subpackages:
#for loader, name, ispkg in pkgutil.iter_modules(path=pkg.__path__):
#    print loader, name, ispkg
##output:
##<pkgutil.ImpImporter instance at 0x2aa5fc8> bushes False
##<pkgutil.ImpImporter instance at 0x2aa5fc8> grass False


def functions(pkg_name, modname):
    full_modname = '{0}.{1}'.format(pkg_name, modname)
    #print sys.path
    pkg = __import__(full_modname)
    mod = getattr(pkg, modname)
    return inspect.getmembers(mod, inspect.isfunction)


def get_callables_2(packages):
    for path in reversed(packages):
        if path not in sys.path:
            sys.path.insert(0, path)

    pkg_modules = DefaultOrderedDict(OrderedDict)
    for imp, name, _ in pkgutil.iter_modules(packages):
        pkg_name = os.path.basename(imp.path)
        pkg_modules[pkg_name][name] = [{'name': n, 'callable': f, 'arguments': get_args2(f)}
                                       for n, f in functions(pkg_name, name)]
    return pkg_modules


ArgValue = namedtuple('ArgValue', 'data is_default')
def get_args2(function):
    """Return ordered dict of arguments, where key is name
    and value is list, filled with value if it's default.
    """
    spec = inspect.getargspec(function)
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


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 


def _build_func_parser(mod_subparsers, func):
    f_name, f_arguments, f_callable = func['name'], func['arguments'], func['callable']
    func_parser = mod_subparsers.add_parser(f_name)
    # add arguments of function
    for name, value in f_arguments.items():
        if value.is_default:
            func_parser.add_argument('--'+name, default=value.data, type=type(value.data))
        else:
            func_parser.add_argument(name)
    # define function and pass it to parser
    def call(parsed_args):
        args = []
        kwargs = {}
        for name, value in f_arguments.items():
            if value.is_default:
                kwargs[name] = getattr(parsed_args, name, value.data)
            else:
                args.append(getattr(parsed_args, name))
        f_callable(*args, **kwargs)
    func_parser.set_defaults(__call=call)
    return func_parser


def build_parser(pkg_paths):
    parser = argparse.ArgumentParser(description="Exposes any function from any "
                "module in 'scripts' dir to command line")
    subs = parser.add_subparsers()
    for pkg_name, modules in get_callables_2(pkg_paths).iteritems():
        for mod_name, functions in modules.iteritems():
            mod_parser = subs.add_parser(mod_name)
            mod_subs = mod_parser.add_subparsers()
            for func in functions:
                _build_func_parser(mod_subs, func)
    return parser

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

def render_to_cli(pyi, subparsers):
    parser = subparsers.add_parser(pyi.name)
    if isinstance(pyi, PyNamespace):
        ssp = parser.add_subparsers()
        for si in pyi.children:
            render_to_cli(si, ssp)
    else:
        assert isinstance(pyi, PyAction)

        # add arguments of function to parser
        for name, value in pyi._action_args.items():
            if value.is_default:
                parser.add_argument('--'+name, default=value.data, type=type(value.data))
            else:
                parser.add_argument(name)

        # define function and pass it to parser
        def call(parsed_args):
            args = []
            kwargs = {}
            for name, value in pyi._action_args.items():
                if value.is_default:
                    kwargs[name] = getattr(parsed_args, name, value.data)
                else:
                    args.append(getattr(parsed_args, name))
            pyi(*args, **kwargs)
        parser.set_defaults(__call=call)

def build_parser2(paths):
    parser = argparse.ArgumentParser(description="Exposes any function from any "
                "module in 'scripts' dir to command line")
    subs = parser.add_subparsers()
    for i in pyitems(paths):
        render_to_cli(i, subs)
    return parser


class PyItem(object):
    def __init__(self, name, instance=None, parent=None):
        self.name = name
        self._instance = instance
        self._parent = parent
        # Is "children" appropriate here?
        # Even action (function) is a namespace, but I hide it :)
        self._children = None

    @property
    def full_name(self):
        if self._parent is None:
            return self.name
        else:
            return '{}.{}'.format(self._parent.full_name, self.name)

    @property
    def children(self):
        return []

    @property
    def instance(self):
        return self._instance


class PyNamespace(PyItem):
    @property
    def children(self):
        if self._children is None:
            functions = inspect.getmembers(self.instance, inspect.isfunction)
            actions = [PyAction(name, instance=instance, parent=self)
                       for name, instance in functions]
            self._children = actions
        return self._children

    @property
    def instance(self):
        if self._instance is None:
            self._instance = importlib.import_module(self.full_name)
        return self._instance


class PyPkg(PyNamespace):
    @property
    def children(self):
        if self._children is None:
            actions = super(PyPkg, self).children
            assert actions == self._children
            iterator = pkgutil.iter_modules(path=self.instance.__path__)
            subs = []
            for loader, name, ispkg in iterator:
                Item = PyPkg if ispkg else PyMod
                subs.append(Item(name, parent=self))
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


def ensure_in_sys_path(packages):
    for path in reversed(packages):
        if path not in sys.path:
            sys.path.insert(0, path)

def pyitems(search_paths):
    if search_paths:
        ensure_in_sys_path(search_paths)
    for loader, name, ispkg in pkgutil.iter_modules(path=search_paths):
        #print dir(loader)
        #instance ?== loader
        Item = PyPkg if ispkg else PyMod
        #yield Item(name, loader)
        yield Item(name, None)

if __name__ == '__main__':
    pkg_path = os.path.join(os.path.dirname(__file__), './scripts')
    pkg_paths = [pkg_path,]
    #pkg_paths = [r'C:\tools\Python27\Lib\bsddb',]
    parser = build_parser(pkg_paths)
    namespace = parser.parse_args()
    namespace.__call(namespace)
