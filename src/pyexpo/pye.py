#!/usr/bin/env python

import os
import ConfigParser as cp
import click
from pyexpo import PySpace, abs_dir, Action


tdata_abspath = abs_dir(__file__) / '../tests/data'
paths = [
    abs_dir(tdata_abspath) / 'path1',
    abs_dir(tdata_abspath) / 'path2',
    abs_dir(tdata_abspath) / 'basic',
]


class PySpaceCLI(click.MultiCommand):
    def __init__(self, *args, **kwargs):
        paths = kwargs.pop('paths', None)
        self._pyspace = PySpace(only_paths=paths)
        super(PySpaceCLI, self).__init__(*args, **kwargs)

    def list_commands(self, ctx):
        #short name?
        return [so.name.split('.')[-1] for so in self._pyspace]

    def get_command(self, ctx, name):
        return ModuleCLI(pyobject=self._pyspace[name])


class ModuleCLI(click.MultiCommand):
    #it's for Package also!
    def __init__(self, *args, **kwargs):
        self._pyobject = kwargs.pop('pyobject', None)
        super(ModuleCLI, self).__init__(*args, **kwargs)

    def list_commands(self, ctx):
        return [so.name.split('.')[-1] for so in self._pyobject.children]

    def get_command(self, ctx, name):
        child = self._pyobject[name]
        if isinstance(child, Action):
            return ActionCLI(name, pyobject=child)
        else:
            return ModuleCLI(pyobject=child)


class ActionCLI(click.Command):
    def __init__(self, *args, **kwargs):
        self._pyobject = kwargs.pop('pyobject', None)
        params = []
        for arg_name, default in self._pyobject.arguments.kwargs:
            help = "Option '{}' with default value '{}'".format(arg_name, default)
            option = click.Option(param_decls=('--'+arg_name,),
                                  default=default,
                                  help=help)
            params.append(option)
        for arg_name in self._pyobject.arguments.args:
            params.append(click.Argument(arg_name))
        kwargs['params'] = params
        kwargs['callback'] = self.callback
        super(ActionCLI, self).__init__(*args, **kwargs)

    def callback(self, *args, **kwargs):
        return self._pyobject.call(*args, **kwargs)


def get_settings():
    settings_path = os.path.join(os.path.expanduser('~/.pyexpo'), 'config.ini')
    cfgparser = cp.ConfigParser({'errors': False})
    cfgparser.read([settings_path])
    def get_list(key, sep=os.path.pathsep):
        try:
            items = [os.path.expanduser(p)
                     for p in cfgparser.get('DEFAULT', key).split(sep)]
            return [p for p in items if p.strip()]
        except cp.NoOptionError as exc:
            #logger.warn("Cannot parse settings file: %s", exc)
            return None
    return {'paths': get_list('paths'),
            'exclude': get_list('exclude'),
            'include': get_list('include'),
            'errors': cfgparser.get('DEFAULT', 'errors'),}


pyspace = PySpaceCLI(paths=get_settings().get('paths'))


if __name__ == '__main__':
    pyspace()

