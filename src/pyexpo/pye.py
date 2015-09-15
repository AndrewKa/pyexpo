#!/usr/bin/env python

import os
import ConfigParser as cp
import click
from pyexpo import PySpace, Action
from pyexpo.utils import abs_dir


tdata_abspath = abs_dir(__file__) / '../tests/data'
paths = [
    abs_dir(tdata_abspath) / 'path1',
    abs_dir(tdata_abspath) / 'path2',
    abs_dir(tdata_abspath) / 'basic',
]


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
        for arg_name in self._pyobject.arguments.args:
            params.append(click.Argument(param_decls=(arg_name,)))
        for arg_name, default in self._pyobject.arguments.kwargs:
            help = "Option '{}' with default value '{}'".format(arg_name, default)
            option = click.Option(param_decls=('--'+arg_name,),
                                  default=default,
                                  help=help)
            params.append(option)
        kwargs['params'] = params
        kwargs['callback'] = self.callback
        super(ActionCLI, self).__init__(*args, **kwargs)

    def callback(self, *args, **kwargs):
        click.echo(
            self._pyobject.call(*args, **kwargs)
        )
        #TODO: make it optional
        #return self._pyobject.call(*args, **kwargs)


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


paths = get_settings().get('paths')
pyspace = ModuleCLI(pyobject=PySpace(only_paths=paths))


if __name__ == '__main__':
    pyspace()

