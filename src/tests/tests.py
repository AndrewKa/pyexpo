from nose.tools import *
from pyexpo import explore_paths, PySpace, Package
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

PATH1 = os.path.join(DATA_DIR, 'path1')
PATH2 = os.path.join(DATA_DIR, 'path2')
PATH_BASIC = os.path.join(DATA_DIR, 'basic')

PATHS = (PATH1, PATH2, PATH_BASIC)


def setup():
    print "SETUP!"


def teardown():
    print "TEAR DOWN!"


def test__simple():
    names = {i.name for i in explore_paths(PATHS)}
    assert 'pkg_bar' in names


def test__toplevel_package():
    space = PySpace(only_paths=PATHS)
    p = space['foo']
    # variants:
    #p = space.get('foo')
    #p = space['foo']
    #p = space.foo
    assert isinstance(p, Package)


def test__package_children():
    space = PySpace(only_paths=PATHS)
    foo = space['foo']
    submodule_names = {m.name for m in foo.children}
    expected = {'foo.subfoo', 'foo.bar', 'foo.__main__', 'foo.print_dir'}
    assert expected == submodule_names, submodule_names


def test__dictlike_package_access():
    space = PySpace(only_paths=[PATH1])
    assert space['foo']['subfoo'].name == 'foo.subfoo'

def test__subpackage_func():
    space = PySpace(only_paths=[PATH1])
    assert space['foo']['bar']['func'].name == 'foo.bar.func'

def test__function_arguments():
    #foo.bar.func(a,b='2')
    space = PySpace(only_paths=[PATH1])
#: set autocmd BufWritePost * !nosetests
