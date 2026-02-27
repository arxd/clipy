======
clipy
======

This project serves two primary purposes.

1. A universal command line interface for any project.
2. An inline-library of useful functions for scripting and tooling.

A project is a meta-program that may produce other programs, or even produce a whole network of connected services.
The meta-program is a single command-line-interface (CLI).
Everything the project is capable of doing is managed/orchestrated through this sole CLI.

This project, itself, of a project based on the cli.py single-interface concept.

Getting Started
================

Run ``./cli.py -h`` and read the documentation to see what this project can do.

Create a new project.

.. code-block:: console

   # Minimal project
   $ ./cli.py create-project simple

   # With features
   $ ./cli.py create-project complex --docs --vault --docker


Rational
===========

There are lots of CLI script front-end programs like ``make``, ``npm/yarn``, ``uv``, etc. that can run custom scripts/tools that help your project function.  Each framework/language has their own pet program.

They all are inadequate for mostly the same reason.  They are an opaque library/binary that tries to be as universal as possible while simultainiously not providing an adequate API.  So they do more, and less than you want, and you can't change the implementation.

This, on the other hand, is not an external library.  It lies somewhere between boilerplate code and library code.
This project bootstraps new projects by copying in boilerplate and library clipy code.
That code is then owned, and can be freely edited/adapted, by the new project.


Design
========

Like most command line interfaces, clipy uses a chain of commands that take parameters.
Like python, there are positional parameters, and named (keyword) parameters.
Named parameters can have a long name using double-dashes ``--long-name`` and a single letter short name ``-s``.
Variable arguments ``*args`` is also supported.

The output of a command can be used as the input to a sub-command.
So, ``./cli.py command -n 3 sub-command -q``, would result in something like, ``sub_command(q=True, parent=command(n=3))``.


commands
----------

Each command is defined by a python function decorated with @CLI().
The function's parameters and the associated docstring fully define the command's interface and documentation.

The `./cli.py` executable (using ``#!/usr/bin/env python``) is the `root` command.
It imports other python modules to look for sub-commands.


configuration
---------------

Almost all projects need target specific configuration.  This is often done in the most crude way with environment variables like ``.env``.
However, keeping configuration in python gives you programmatic control and complex configuration variables.
Then, configuration can take on a broader purpose of providing 'ambient' parameters.
That is, instead of parameters passed explicitly to your function, they are parameters 'inherited' from the context in which your function is executing.
In other languages/frameworks this kind of thing is done with 'Provider' objects.  In python this is done with `context variables <https://docs.python.org/3.14/library/contextvars.html>`_.
Name-spacing is done by using the normal python namespace for config variables ``import my_var as differ_name from .somewhere``.

So you declare a configuration variable in the most appropriate global context (same as a function or class):

.. code-block:: python

   endpoint_url = ConfigVar('The endpoint for backend services')
   max_users = ConfigVar('The maximum number of users we can handle', default=10)

And then you import it and use it somewhere else.  The value ``url.v`` will be a context-aware, target-specific value.

.. code-block:: python

   from .backend import endpoint_url as url

   def handler():
      print(url.v)


targets
~~~~~~~~

A target is a set of configuration variables.  They are ususally named ``local``, ``stage``, ``prod``, etc.
Commands that you execute run with variables that are set from one of those target configurations.
The most obvious example of a configuration variable that would change per-target would be an ``endpoint_url``.
Other variables like the project's ``name`` might be the same between different targets.

By default, when no ``-t <target>`` argument is given, the ``local`` or ``dev`` target is chosen as the safest default choice.
That way, you can't mess up anything important by accident.
When you explicitly set the target ``./cli.py -t prod delete user bob`` you know you need to be careful.


environments
~~~~~~~~~~~~~

This is a term often used interchangeabley with `targets`, but it is a different concept in clipy.
An environment is *where* cli.py is being executed.

* Is it running in a development environment on your laptop?
* Is it running in a docker container executing a specifc tooling function?
* Is it running on the production server or device?

The environment determines which modules python has access to, as well as other things like network access.
In a dev environment you might need a different set of modules from the prod environment.
Are you running with a python venv, or using the system python?

Which modules are available determines which commands are executable in an environment.
Because, obviously, if the command can't import the modules it needs, then it can't run.

There is a distinction to be made between the ability to import a command, and run a command.
Even if you can't run a command (becuase of a missing libary), it is helpful to be able to import the command so that you can read, and display, its help documentation.
The local/dev environment is where the user interacts dynamically with cli.py, so in that environment, all commands need to be importable (even if not runnable) so that documentation can be generated.
In other environments, like production, it may be fine if you can't import all commands, since only a subset of the commands may be used.


cli.py
---------

This is the main, executable, entrypoint that defines the root command.

The first thing it does when run is to check the `environment` it is running in and make sure of the following.

* Are we running in a venv?  If not, should we be?
* Do we have the bare-minimum modules to import the commands that should be viewable from this environment?

After those two conditions are met, it hands control over to the command execution engine.

You should be able to clone any project and run ``./cli.py -h`` to see everything that can be done with the project.


.. toctree::
   :maxdepth: 1

   docs/gen/cli/cli
   docs/config

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
