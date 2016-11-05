#!/usr/bin/env python

import imp
import os
import sys
import subprocess


STD_PREFIX = 'PYEXPO_PATH_'
MY_PATH = os.path.abspath(__file__)


def pack(fd, pathname, description):
    to_open = str(1 if fd else 0)
    desc = os.pathsep.join(map(str, description))
    return os.pathsep.join((to_open, pathname, desc))


def unpack(packed):
    to_open, pathname, desc0, desc1, desc2 = packed.split(os.pathsep)
    description = desc0, desc1, int(desc2)
    to_open = int(to_open)
    fd = open(pathname) if to_open == 1 else None
    return fd, pathname, description


def modules_to_env_vars(*module_names):
    r = {}
    for n in module_names:
        if '.' in n:
            raise ValueError("Cannot process embedded module '{}'".format(n))
        var_name = STD_PREFIX + n
        var_value = pack(*imp.find_module(n))
        r[var_name] = var_value
    return r


def extract_modules_from_env():
    for n, v in os.environ.iteritems():
        if not n.startswith(STD_PREFIX):
            continue
        modname = n[len(STD_PREFIX):]
        mod_properties = [modname]
        mod_properties.extend(unpack(v))
        mod = imp.load_module(*mod_properties)


def push_other_python(venv_root_or_python):
    if os.path.isfile(venv_root_or_python):
        other_python = venv_root_or_python
    else:
        other_python = '%s/bin/python' % venv_root_or_python
    env_vars = modules_to_env_vars('pyexpo', 'click')
    #parts = ['eval "$(_PYE_COMPLETE=source pye)"']
    parts = ['{}={}'.format(n, v) for n, v in env_vars.iteritems()]
    parts.extend([other_python, MY_PATH]) # args?
    #params = dict(
    #    venv_path='/home/akazakin/venvs/tmp',
    #    MY_PATH=os.path.abspath(__file__),
    #    pyexpo_path=pyexpo.__path__[0],
    #)
    #cmdline = ' '.join([
    #    'PYEXPO_MY_PATH={pyexpo_path}',
    #    '{venv_path}/bin/python',
    #    '{MY_PATH}'
    #]).format(**params)
    cmdline = ' '.join(parts)
    print cmdline
    subprocess.call(cmdline, shell=True)


def do():
    is_foreign = (STD_PREFIX + 'pyexpo') in os.environ 
    if is_foreign:
        extract_modules_from_env()
        # ready for normal operations...
        from pyexpo.pye import pyspace
        pyspace()
    else:
        # may be need another virtualenv
        if True:  # need
            push_other_python('/usr/bin/python')


class ModuleInCli(object):
    def __init__(self, packed=None, unpacked=None):
        if unpacked:
            # from module to str
            #fd, pathname, description = unpacked
            packed = pack(*unpacked)
        else:
            # from str to module
            fd, pathname, description = unpack(packed)

            # it could be not found...
            pyexpo = imp.load_module('pyexpo', fd, pathname, description)
            sys.modules


if __name__ == '__main__':
    do()
