This file requires editing
==========================

Note to the author: Please add something informative to this README *before*
releasing your software, as `a little documentation goes a long way`_.  Both
README.rst (this file) and NEWS.txt (release notes) will be included in your
package metadata which gets displayed in the PyPI page for your project.

You can take a look at the README.txt of other projects, such as repoze.bfg
(http://bfg.repoze.org/trac/browser/trunk/README.txt) for some ideas.

.. _`a little documentation goes a long way`: http://www.martinaspeli.net/articles/a-little-documentation-goes-a-long-way

Credits
-------

- `Distribute`_
- `Buildout`_
- `modern-package-template`_

.. _Buildout: http://www.buildout.org/
.. _Distribute: http://pypi.python.org/pypi/distribute
.. _`modern-package-template`: http://pypi.python.org/pypi/modern-package-template


Ideas (may be implemented or not)
---------------------------------
- put ``--x-debug`` to alter logging (to console/stderr in DEBUG level)
- create cache and ``--x-bust-cache``/``--x-without-cache``
- expose "any" action/namespace: functions, classes,
  modules, packages (can be action if contains __main__)
- "expose" means:

  * enumerate it (for namespace)
  * execute it (for action)
  * print info about parameters for actions
  * print 1st line of docstring for any pyitem

- let's have alterable  default behaviour for functions/classes
  (execute/enumerate children) - for more "namespace"-like we
  should list, for "action"-like - execute

  * ``--x-enum``/``--x-run``
  * ``--x-help``

- let's have a way to manipulate results: either serialization of result to stdout:

  * ``--x-export=str``, ``--x-export=json``, ``--x-export=yaml``,...
  * ``--x-export-conf=name_of_conf_in_ini``

  or more complicated manipulations (is it possible with std argparse?):

  * ``--x-next-name_of_param_in_next_action_or_num_of_position``
  
  or make it work like stack! (explore Forth, please!)

- let's make it possible to run in `specified virtualenv`_

.. _specified virtualenv: http://stackoverflow.com/questions/6943208/activate-a-virtualenv-with-a-python-script

- use sphinx markup from docstrings for documentation

- make simple scripts with smth like: pyexpo.functions_to_cli(func1, func2, ...)

- expose via web, as shovel_

.. _shovel: https://github.com/seomoz/shovel

- start with smth simple: search path location: show packages/modules
- Basically, there are different stuff:

  * explore some point in fs for python packages/modules/callables
  * converting exploration result into some form - ArgParser, currently

Design principles
-----------------
- In any case it should be simple for main purpose - run any function via CLI
- Should I use dotted notation for package namespaces? It should have natural flavour for python developer.
- One dotted piece of string - one parser. It should be possible


UX
--
- It should be easy for deployment (pip/rpm/deb/msi)
- It should be easy for usage (autocomplete, fast, simple)


Technical Details
-----------------
Code::

    for importer, name, is_pkg in pkgutil.iter_modules(path=_paths):
        try:
            if self._is_needed(name, parent=parent):
                N = Package if is_pkg else Module
                yield N(name, parent=parent, collector=self)
        except LoadError as exc:

Another code::

    if p not in sys.path:
        sys.path.insert(0, p)

More::

    functions = inspect.getmembers(self.instance, inspect.isfunction)
    actions = [Action(name, instance=instance, parent=self)
               for name, instance in functions]

And more::

    def explore_paths(paths):
        for importer, name, is_pkg in pkgutil.iter_modules(path=paths):
            yield name

what's about class browser?


Useful links
------------
- `PEP 302 - New Import Hooks
  <http://www.python.org/dev/peps/pep-0302/>`_

