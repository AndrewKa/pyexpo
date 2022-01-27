#!/usr/bin/env python

import os
import ConfigParser as cp
import click
from pyexpo import PySpace, Action


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


class ModuleCLI(click.MultiCommand):
    # it's for Package also!
    def __init__(self, *args, **kwargs):
        self._pyobject = kwargs.pop('pyobject', None)
        super(ModuleCLI, self).__init__(*args, **kwargs)

    def list_commands(self, ctx):
        click.echo('ctx={}'.format(dir(ctx)))
        return [so.name.split('.')[-1] for so in self._pyobject.children]

    def get_command(self, ctx, name):
        child = self._pyobject[name]
        if isinstance(child, Action):
            return ActionCLI(name, pyobject=child)
        else:
            return ModuleCLI(pyobject=child)

    def _execute_as_agent(self, ctx, param, value):
        click.echo('ctx={}, param={}, value={}'.format(ctx, param, value))
        ctx.exit()

    def get_params(self, ctx):
        params = super(ModuleCLI, self).get_params(ctx)

        params.append(click.Option(
            param_decls=('--command-file', ),
            help='Specify this option if you want to run this app in agent mode (to communicate with primary instance)',
            is_eager=True,
            callback=self._execute_as_agent,
            # expose_value=False,
        ))

        return params


def get_settings():
    settings_path = os.path.join(os.path.expanduser('~/.pyexpo'), 'config.ini')
    cfgparser = cp.ConfigParser(defaults={'errors': False})
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


# -----------------------\
import sys


# borrow some internals from click:

def _get_complete_stuff(cli, prog_name, cwords, cword):
    from click._bashcomplete import resolve_ctx
    from click.core import MultiCommand, Option

    # Do I need click as a kind of strange adapter here?
    # It's better to get straightforward result from own machinery
    # and pass it to click as one of UIs.
    # But I need my own "vocabulary" for such case - it's my domain.
    #
    # TODO: I need cli interface in one place only. The other
    # side - agent - should communicate with current cli by
    # some specific protocol. That's all!
    #
    # I can use this same app as agent with cli option --control-url

    args = cwords[1:cword]
    try:
        incomplete = cwords[cword]
    except IndexError:
        incomplete = ''

    ctx = resolve_ctx(cli, prog_name, args)
    if ctx is None:
        return []

    choices = []
    if incomplete and not incomplete[:1].isalnum():
        for param in ctx.command.params:
            if not isinstance(param, Option):
                continue
            choices.extend(param.opts)
            choices.extend(param.secondary_opts)
    elif isinstance(ctx.command, MultiCommand):
        choices.extend(ctx.command.list_commands(ctx))

    return [item for item in choices if item.startswith(incomplete)]


def _click_internals():
    from click.utils import make_str
    from click.parser import split_arg_string
    from click._bashcomplete import do_complete
    # patch os.environ and call do_complete direclty?
    prog_name = make_str(os.path.basename(
        sys.argv and sys.argv[0] or __file__))
    cwords = split_arg_string(os.environ['COMP_WORDS'])
    cword = int(os.environ['COMP_CWORD'])
    # for param in ctx.command.params:
    #   param.opts                   -> [potential] choices
    #   param.secondary_opts         -> [potential] choices
    # ctx.command.list_commands(ctx) -> [potential] choices
    return _get_complete_stuff(pyspace, prog_name, cwords, cword)
# -----------------------/


if __name__ == '__main__':
    pyspace()
