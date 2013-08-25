import os
import pkgutil
import inspect
from itertools import izip_longest, izip
from collections import defaultdict, OrderedDict, namedtuple
from datastructures import DefaultOrderedDict

import argparse

# Some ideas:
# * routing stuff can be externalized (like Django's urls.py)
# * access can be switched on/off (include/exclude/glob/...)
# * input/output formats can be (traditionally) subclassed
# * result of any output can be symbolized and appropriate symbol
#   can be put as input argument to other function

# Approach: it should be like request-response, i.e.
#   I can init same structure for output and input/for validation
# Is Django Forms is appropriate here? It's too complicated :)


def functions(pkg_name, modname):
    full_modname = '{0}.{1}'.format(pkg_name, modname)
    pkg = __import__(full_modname)
    mod = getattr(pkg, modname)
    return inspect.getmembers(mod, inspect.isfunction)


def get_callables_2(packages):
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
    r_defaults = reversed(spec.defaults)
    args = []
    vals = []
    not_specified = object()
    for arg, default in izip_longest(r_args, r_defaults, fillvalue=not_specified):
        args.append(arg)
        vals.append(
            ArgValue(default, not default is not_specified)
        )
    return OrderedDict(izip(reversed(args), reversed(vals)))


def _build_func_parser(mod_subparsers, func):
    f_name, f_arguments, f_callable = func['name'], func['arguments'], func['callable']
    func_parser = mod_subparsers.add_parser(f_name)
    # add arguments of function
    for name, value in f_arguments.items():
        if value.is_default:
            func_parser.add_argument('--'+name, default=value.data, type=type(value.data))
        else:
            func_parser.add_argument(name)
    # bind function with parser
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


if __name__ == '__main__':
    pkg_paths = ['./scripts',]
    parser = build_parser(pkg_paths)
    namespace = parser.parse_args()
    namespace.__call(namespace)
