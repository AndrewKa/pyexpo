import os
import sys

import expo.lib as e


CURRENT_PATH = os.path.abspath(__file__)
CURRENT_DIR = os.path.dirname(CURRENT_PATH)


def print_pyi(pyi, indent=''):
    print indent + str(pyi)
    for child in pyi.children:
        print_pyi(child, indent=(indent+'\t'))


def print_pyi_hierarchy(dirs):
    paths = []
    for d in dirs:
        paths.append(os.path.join(CURRENT_DIR, d))
    #paths = [os.path.join(CURRENT_DIR, 'data/path1'),]
    for pyi in e.pyitems(paths):
        print_pyi(pyi)


def test_all_members():
    paths = [os.path.join(CURRENT_DIR, 'data/path1'),]
    ar_member_names = set(pyi.name for pyi in e.pyitems(paths))
    er_member_names = {'scripts', 'hello'}
    assert ar_member_names == er_member_names


def test_str():
    paths = [os.path.join(CURRENT_DIR, 'data/path1'),]
    ar_strs = dict((pyi.name, str(pyi)) for pyi in e.pyitems(paths))
    er_parts = {'scripts': 'package', 'hello': 'module'}
    for name, lsubstr in er_parts.items():
        assert name in ar_strs 
        assert ar_strs[name].lower().find(lsubstr) >= 0


def test_children():
    paths = [os.path.join(CURRENT_DIR, 'data/path1'),]
    # action in module
    hello_mod = [pyi for pyi in e.pyitems(paths) if pyi.name == 'hello'][0]
    assert len([action for action in hello_mod.children if action.name == 'foo']) > 0

    # action in package
    scripts_pkg = [pyi for pyi in e.pyitems(paths) if pyi.name == 'scripts'][0]
    assert len([i for i in scripts_pkg.children if i.name == 'foo']) > 0

    # action in submodule
    submodule = [i for i in scripts_pkg.children if i.name == 'bushes'][0]
    assert len([i for i in submodule.children if i.name == 'nice_func']) > 0


if __name__ == '__main__':
    test_all_members()
    test_str()
    test_children()
    if len(sys.argv) > 1 and sys.argv[1] == 'print':
        print_pyi_hierarchy(['data/path1', 'data/path2'])
