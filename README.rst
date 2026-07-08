======
cli.py
======

`Read the built documentation <../../blob/docs/markdown/README.md>`__

This project serves two primary purposes.

1. A universal command line interface for any project. (See: :ref:`Commands <page-commands>`)

   - Sub-commands are known deterministically.

     - Command-line arguments for all commands are parsed before any commands are executed.
     - Child commands may be discovered only when needed for efficiency.
   
   - Easy-to-read documentation automatically generated from the docstring with ``-h`` or ``--help``.
   - The function's annotations and default values are used to coerce the command line arguments to the correct type.
   - A consistent way to call all kinds of function signatures (using ``inspect.signature`` to the fullest extent).
   - Generators, async, and async generators are all supported.
   - The ability to accept multiple list-typed parameters.
   - ``*args`` and ``**kwargs`` have useful abilities.

2. An inline-library of useful functions for scripting and tooling.

   - environment setup:  Making sure you have the right python version, venv, packages needed.
   - configuration:  Per-target (local, staging, production) configuration variables.
   - printing/logging:  Combining these two ideas and adding console-specific pretty printing.
   - system commands:  Working with other command-line-tools such as nginx, grep, aws, docker, etc.
   - documentation:  Coordinating sphinx-based documentation generation.
   - vault:  Keeping secrets in the project secret.
   
A project is a meta-program that may produce other program executables, or even produce a whole network of connected services.
The meta-program is a single command-line-interface (CLI) to all of the functionality exposed by the project.
Everything the project is capable of doing is managed/orchestrated through this sole CLI.

This project is a project based on the cli.py concept, so it is a good demonstration of itself.


Getting Started
================

Run ``./cli.py`` to see what commands are available.
Run ``./cli.py docs view`` and read all of this documentation in the browser.

Create a new project.

.. code-block:: console

   # Create a new project
   $ ./cli.py create my_project


Rational
===========

There are lots of CLI script front-end programs like ``make``, ``npm/yarn``, ``uv``, etc. that can run custom tooling-related scripts.  Each framework/language has their own pet program.

They all are inadequate for mostly the same reason.  They are an opaque library/binary that tries to be as universal as possible while simultaneously not providing an adequate API.  So they do more, and less than you want, and you can't change the implementation.

clipy, on the other hand, is not an external library.  It lies somewhere between boilerplate code and library code.
This project bootstraps new clipy-based projects by copying in boilerplate and library clipy code.
That code is then owned, and can be freely edited/adapted, by the new project.


.. toctree::
   :maxdepth: 1

   docs/commands
   docs/issues
   docs/configuration
   docs/design

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
