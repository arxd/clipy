.. _page-config:

==================
Configuration
==================

Any function needs parameters.
There are explicit parameters defined for the function, but there are also ambient parameters (global variables) that the function has access to.

These ambient values have various levels of mutability and configurability.

1. Constant:  Example, ``name``, ``version``.  These are defined in ``cli.py`` and are the same across `target`s and `system`s.
    To change them you need to change the source code.

2. Environment variables:  These have the ability to be set at the OS environment level so they feel more like constants (semi-constant), even though they have runtime-mutability.
    Their limited storage capacity, string-type, and flat namespace are inconvenient.
    Their main benefit is that they carry over to sub-command processes.

3. `ConfigVar`:  These are python's context-aware ``contextvars.ContextVar`` objects.  They have proper namespace separation and any python type.  The downside is that they don't survive across to sub-command processes.



.. _target:

Target
========

A target is a certain configuration of `ConfigVar`\ s for certain workflows or deployment environments such as staging, or production.
The actual target name is set as an environment variable and can be changed more dynamically as a parameter to cli.py. ``./cli.py -t staging ...`

In practice, a target is just a function defined in cli.py and decorated with `@Target() <Target.__call__>`


.. autoclass:: libclipy.core.config.Target
    :members: __call__



.. _system:

System
=======

A system is *where* cli.py is being executed.
The system dictates things like what libraries and architecture-specific abilities are available.

* Is it running on your development laptop?
* Is it running in a docker container executing a specific tooling function?
* Is it running on the production server or device?

Which modules are available determines which commands are executable in a system (if the command can't import the modules it needs, then it can't run).

There is a distinction to be made between the ability to import a command, and run a command.
Even if you can't run a command (because of a missing library), it is helpful to be able to import the command so that you can read, and display, its help documentation.
The local/dev system is usually where the user is interactively calling cli.py, so all commands need to be importable (even if not runnable) so that documentation can be generated.
For other systems, like production, it may be fine if you can't import all commands, since only a subset of the commands may be used.



Environment Variables
=======================

Environment variables for the project are given a project-specific prefix defined in cli.py, ``env = Env(prefix,...)``.
These should be thought of as high-level semi-constant (bashrc) configuration.
To overcome the limitation of only being able to store short strings, and to benefit from the ability to carry configuration variables over to sub-command processes, private variables are used.

A private environment variable is one that starts with an underscore, ``Env('MY_', _private=(1,2))``.
When set with a value, private variables are not actually put in the os environment.
They are transferred to sub-command processes via a pipe, so they can be any pickleable type.


.. autoclass:: libclipy.core.venv.Env



ConfigVar 
============

Environment variables share a flat namespace, so they must rely on name-prefix based namespacing.
A better solution is to let the names live in the native module namespace and then use the standard python ``import as`` mechanism deal with name conflicts.

A `ConfigVar` variable is created at a global scope in the module that created the need for it.


.. code-block:: python

    from cli import ConfigVar

    max_size = ConfigVar('max_size The maximum size of the buffer', default=16)

    @ConfigVar()
    def a_pair(v='a b'):
        ''' A pair of important configuration values '''
        return v.split(' ')
    
    def use_the_var():
        buffer = a_pair.v * max_size.v


.. autoclass:: libclipy.core.config.ConfigVar
    :members: __call__



Secrets
---------

No secret (passwords, keys) should be stored in configuration variables.  They should be stored in files (in the `vault`)
and the file path should be given in a configuration variable.  One text file for each variable.
Don't put them all together in one json file.



Virtual Environment
-----------------------

Each `Command` has the option of defining its own python virtual environment requirements.
The virtual environment configuration can be set on the command with a decorator

.. code-block:: python

    @Venv(python='3.10 3.11', requirements='numpy matplotlib', system_packages=True, system='dev prd')
    @Command()
    def foo():
        ...

If a `Venv` is not given then the parent command's environment is used.

.. autoclass:: libclipy.core.venv.Venv
    :members: __call__

