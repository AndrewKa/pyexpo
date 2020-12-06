#!/usr/bin/env python
from __future__ import print_function

import imp
import os
import sys
import tempfile
import json
import socket

# if os.name == 'posix' and sys.version_info[0] < 3:
#     import subprocess32 as subprocess
# else:
#     import subprocess
import subprocess


def _send_json_obj(filename, json_obj):
    # json_obj = {chr(c): c for c in range(ord('a'), ord('z')+1)}
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(filename)
        sock.sendall(json.dumps(json_obj))
    finally:
        sock.close()


def _pass_uds_name_and_read_obj():
    with tempfile.NamedTemporaryFile() as f:
        # get unique filename
        filename = f.name

    # TODO: socket timeout
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(filename)
    try:
        sock.listen(1)

        yield filename
        # TODO: start process

        connection, _ = sock.accept()
        chunks = []
        buffer_size = 4096
        s = connection.recv(buffer_size)
        while s:
            chunks.append(s)
            s = connection.recv(buffer_size)
        data = ''.join(chunks)

        obj = json.loads(data)
        yield obj

        connection.close()
    finally:
        os.remove(filename)


# TODO: create custom MultiCommand (can old be reused?) and pull content for it from communication
#       with other process via some file (it can be communication over the network)
#       Other process can be the same app, but in other environment (other venv, in container, at other host).
#       So basically it has two parts:
#       1. Initiate connection (maybe run some process first or smth else)
#       2. Communicate over the connection to do stuff


import socket
def send_at_9999(data):
    HOST, PORT = "localhost", 9999

    # Create a socket (SOCK_STREAM means a TCP socket)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to server and send data
        sock.connect((HOST, PORT))
        sock.sendall(data + "\n")

        # Receive data from the server and shut down
        received = sock.recv(1024)
    except socket.error as error:
        pass  # silently ignore the error
    finally:
        sock.close()


def parent_send(data):
    send_at_9999('parent: {}'.format(data))


def child_send(data):
    send_at_9999('child: {}'.format(data))


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


def _env_dict_to_list(env):
    return ['{}="{}"'.format(n, v) for n, v in env.items()]


def _get_completion_vars():
    completion_vars = [
        '_PE_COMPLETE',
        'COMP_CWORD',
        'COMP_WORDS',
    ]
    completion_values = {v: os.environ[v] for v in completion_vars if v in os.environ}
    if len(completion_values) == len(completion_vars):
        return completion_values
    return {}


def push_other_python(venv_root_or_python):
    """
    What is the goal? Start me in other process with right venv.
    Bash completion env should be similar to current process.
    Output of child process should go to env var COMPREPLY.
    :param venv_root_or_python:
    :return:
    """
    if os.path.isfile(venv_root_or_python):
        other_python = venv_root_or_python
    else:
        other_python = '%s/bin/python' % venv_root_or_python
    parent_send('other_python={}'.format(other_python))
    cmdline = ' '.join(
        _env_dict_to_list(modules_to_env_vars('pyexpo', 'click'))  # TODO: pass env to make process
        + _env_dict_to_list(_get_completion_vars())  # TODO: pass env to make process
        + [other_python, MY_PATH]
        + sys.argv[1:]
    )
    parent_send('cmdline to execute: {}'.format(cmdline))

    # completed_process = subprocess.run(
    #     cmdline, shell=True, stdout=subprocess.PIPE)
    # parent_send('from child: code={}\noutput: {}'.format(
    #     completed_process.returncode, completed_process.stdout))
    # child_stdout = subprocess.check_output(cmdline, shell=True)
    # parent_send('child stdout: {}'.format(child_stdout))
    # print(child_stdout)
    p = subprocess.Popen(cmdline, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    parent_send('child code={}, stdout: {}\nstderr: {}'.format(p.returncode, stdout, stderr))
    print(stdout or stderr)


def do():
    is_foreign = (STD_PREFIX + 'pyexpo') in os.environ 
    if is_foreign:
        child_send('it is foreign, extracting...')
        extract_modules_from_env()
        # ready for normal operations...
        from pyexpo.pye import pyspace
        child_send('before running pyspace...')
        # execute instance of click.MultiCommand:
        pyspace()
    else:
        push_other_python('/usr/bin/python')


def do2():
    steps = _pass_uds_name_and_read_obj()
    filename = next(steps)
    parent_send('start process, pass "{}" and write obj in this process'.format(filename))
    obj = next(steps)
    parent_send('I have got {}'.format(obj))
    next(steps, None)  # finalize


# borrow some internals from click:

def _get_complete_stuff(cli, prog_name):
    from click.parser import split_arg_string
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

    cwords = split_arg_string(os.environ['COMP_WORDS'])
    cword = int(os.environ['COMP_CWORD'])
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
    # from click._bashcomplete import do_complete
    from pyexpo.pye import ModuleCLI, paths, PySpace
    cli = ModuleCLI(pyobject=PySpace(only_paths=paths))
    prog_name = make_str(os.path.basename(
        sys.argv and sys.argv[0] or __file__))
    return _get_complete_stuff(cli, prog_name)


if __name__ == '__main__':
    do()
