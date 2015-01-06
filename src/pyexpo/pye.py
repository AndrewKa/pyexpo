#!/usr/bin/env python

import os
import ConfigParser as cp
import inspect
from pyexpo.lib import cli


# optional module
try:
    import argcomplete
except ImportError:
    class argcomplete(object):
        @staticmethod
        def autocomplete(x):
            pass



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
    settings = {'path': get_list('paths'),
                'exclude': get_list('exclude'),
                'include': get_list('include'),
                'errors': cfgparser.get('DEFAULT', 'errors'),}
    return settings


def main():
    settings = get_settings()
    parser = cli.build_parser(**settings)

    argcomplete.autocomplete(parser)

    args = parser.parse_args()
    args.__call(args)


if __name__ == '__main__':
    main()
