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


#expo_location = '~/projects/py'
#current_dir = os.path.dirname(os.path.abspath(__file__))
#sys.path.insert(0, os.path.expanduser(expo_location))
#sys.path.insert(0, os.path.dirname(current_dir))

def get_settings():
    settings_path = os.path.expanduser('~/.pyexpo')
    cfgparser = cp.ConfigParser()
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
            'errors': True}


def main():
    settings = get_settings()
    parser = cli.build_parser(**settings)

    argcomplete.autocomplete(parser)

    args = parser.parse_args()
    args.__call(args)


if __name__ == '__main__':
    main()
