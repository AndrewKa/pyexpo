import os
import argparse
from pyitems import pyitems, PyNamespace, PyAction


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

        # define closure and pass it to parser
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

def build_parser(**config):
    parser = argparse.ArgumentParser(description="Exposes any function from any "
                "module in 'scripts' dir to command line")
    #parser.add_argument('-p', '--paths', dest='paths',
    #                    help='Paths to explore for python functions')
    subs = parser.add_subparsers()
    root_items = []
    for i in pyitems(**config):
        render_to_cli(i, subs)
        root_items.append(i)
    # print error items:
    if config.get('errors'):
        error_items = set()
        for i in root_items:
            if i.collector._errors:
                for error_i in i.collector._errors:
                    error_items.add(str(error_i))
        for s in error_items:
            print s
    return parser


