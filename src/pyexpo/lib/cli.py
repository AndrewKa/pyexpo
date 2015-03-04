import os
import argparse
from pyitems import pyitems, Namespace, Action, LoadError


def render_to_cli(pyi, subparsers):
    #TODO: let's try to make it lazy: argparse.ArgumentParser.parse_known_args() + subparsers
    parser = subparsers.add_parser(pyi.name)
    if isinstance(pyi, Namespace):
        ssp = parser.add_subparsers()
        for si in pyi.children:
            try:
                render_to_cli(si, ssp)
            except LoadError as exc:
                msg = "Cannot dive into {}: {}".format(si.full_name, exc)
                print msg
                if pyi.collector._errors is None:
                    raise
                else:
                    pyi.collector._errors.append(exc._item)
    else:
        assert isinstance(pyi, Action)

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
    #iterate by PySearchPath(???not implemented) items or all top-level modules on sys.path
    for i in pyitems(**config):
        render_to_cli(i, subs)
        root_items.append(i)
    # print error items:
    if config.get('errors'):
        error_items = set()
        for i in root_items:
            print "Some errors ({}) have happened".format(len(i.collector._errors))
            if i.collector._errors:
                for error_i in i.collector._errors:
                    error_items.add(str(error_i))
        for s in error_items:
            print s
    return parser


