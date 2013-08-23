import os
import pkgutil
import inspect
from collections import defaultdict, OrderedDict
from datastructures import DefaultOrderedDict

# Some ideas:
# * routing stuff can be externalized (like Django's urls.py)
# * access can be switched on/off (include/exclude/glob/...)
# * input/output formats can be (traditionally) subclassed
# * result of any output can be symbolized and appropriate symbol
#   can be put as input argument to other function

# Approach: it should be like request-response, i.e.
#   I can init same structure for output and input/for validation
# Is Django Forms is appropriate here? It's too complicated :)

def get_pkg_modules(packages):
    pkg_modules = defaultdict(list)
    for imp, name, _ in pkgutil.iter_modules(packages):
        pkg_name = os.path.basename(imp.path)
        pkg_modules[pkg_name].append(name)
    return pkg_modules


def get_functions(pkg_modules):
    functions = OrderedDict()
    for pkg_name in pkg_modules:
        for modname in pkg_modules[pkg_name]:
            full_modname = '{0}.{1}'.format(pkg_name, modname)
            pkg = __import__(full_modname)
            mod = getattr(pkg, modname)
            for name, function in inspect.getmembers(mod, inspect.isfunction):
                full_name = '{0}.{1}'.format(full_modname, name)
                functions[full_name] = function
    return functions


def print_fun_arguments(pkg_paths):
    funs = get_functions(get_pkg_modules(pkg_paths))
    for name, function in funs.items():
        spec = inspect.getargspec(function)
        args = []
        kwargs = OrderedDict()
        for i, arg in enumerate(spec.args):
            z = i - len(spec.args)
            if spec.defaults and len(spec.defaults) >= abs(z):
                d = len(spec.args) - len(spec.defaults)
                assert (i - d) >= 0, (i, d)
                kwargs[arg] = spec.defaults[i - d]
            else:
                args.append(arg)
        print name, ':', ', '.join(args), ', '.join('{0}={1}'.format(k,v) for k,v in kwargs.items())


#---------------


def functions(pkg_name, modname):
    full_modname = '{0}.{1}'.format(pkg_name, modname)
    pkg = __import__(full_modname)
    mod = getattr(pkg, modname)
    return inspect.getmembers(mod, inspect.isfunction)


def get_callables_(packages):
    pkg_modules = DefaultOrderedDict(OrderedDict)
    for imp, name, _ in pkgutil.iter_modules(packages):
        pkg_name = os.path.basename(imp.path)
        pkg_modules[pkg_name][name] = [{'name': n, 'callable': f, 'arguments': get_args(f)}
                                       for n, f in functions(pkg_name, name)]
    return pkg_modules


def get_args(function):
    """Return ordered dict of arguments, where key is name
    and value is list, filled with value if it's default.
    """
    spec = inspect.getargspec(function)
    args = OrderedDict()
    for i, arg in enumerate(spec.args):
        z = i - len(spec.args)
        if spec.defaults and len(spec.defaults) >= abs(z):
            d = len(spec.args) - len(spec.defaults)
            assert (i - d) >= 0, (i, d)
            args[arg] = [spec.defaults[i - d]]
        else:
            args[arg] = []
    return args


def print_fun_args(pkg_paths):
    sarg = lambda name, default: '{}={}'.format(name, default[0]) if len(default) else name
    for pkg_name, modules in get_callables_(pkg_paths).iteritems():
        for mod_name, functions in modules.iteritems():
            for func in functions:
                args = [sarg(n, d) for n, d in func['arguments'].items()]
                print pkg_name, mod_name, func['name'], ','.join(args)
#----------------------

if __name__ == '__main__':
    pkg_paths = ['./scripts',]
    #print_fun_arguments(pkg_paths)
    print_fun_args(pkg_paths)
