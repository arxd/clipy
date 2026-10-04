.. _page-config:

==================
Configuration
==================

Any function needs parameters.
There are explicit parameters defined for the function, but there are also ambient parameters (global variables) that the function has access to through imports.
These global variables are context-aware ``contextvars.ContextVar`` derived `ConfigVar()` objects.

The value of any variable is influenced from a number of places:

1. The default value
2. The current `@Target() <Target.__call__>` (which is influenced by the `system`)
3. CLIPY_XYZ environment variables. This usually overrides the target's value, unless the target sets the value with the ``.v`` syntax.
4. Parent command's modifications

Those are listed in order of increasing knowledge.
The default value knows the least about what the value should be, and parent commands are operating with the most knowledge. 


.. _target:

Target
========

A target is a certain configuration of `ConfigVar`\ s for certain workflows or deployment environments such as staging, or production.
The target is a tuple of names corrosponding to `@Target() <Target.__call__>` decorated functions in `config.py`.

Each function in the target tuple is applied in order.
The function should change the ``.default`` value of a configvar, rather than setting its value ``.v`` so that environment variables can override them.

The target can be set from an environment variable ``CLIPY_TARGET`` or when calling a command ``./cli.py -t staging.test ...`

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

Environment variables for the project are given a project-specific prefix defined in cli.py: ``env_prefix``.

These have higher priority than settings in ``config.py`` but lower than command's modifications (from users passing arguments on the command line).



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

    @Venv(python='3.10 3.11', req='numpy matplotlib', system_packages=True, system='dev prd')
    @Command()
    def foo():
        ...

If a `Venv` is not given then the main command's environment is used.
It might be sensible for a command to always have its venv be derived from its parent, but that is not possible.
A command doesn't have a clear parent because it can be listed as a child of multiple parents and be called manually from anywhere.
Instead you can set the first parameter of ``@Venv`` to be a command (or command path string) that will be used as a base venv.
Your ``req`` get appended to the base's and you can override the other parameters as needed.

.. code-block:: python

    @Venv('libclipy.cli_foo::foo', req='somelib>2', system='dev') # Uses the command string path
    @Venv(foo, req='somelib>3', system='prd') # Uses the command object
    def bar():
        ...

The venv that matches the `system` (set through the environment `CLIPY_SYSTEM`) is chosen.

You can also set a global venv at the top of your source file that will get applied to all commands defined in that file.
It gets applied *after* any Venv decorations.

.. code-block:: python

    __venv__ = Venv(python='>3.14')

    #@Venv(python='>3.14')
    @Command()
    def foo():
        ...

    @Venv('cli::main', system='dev')
    #@Venv(python='>3.14')
    @Command()
    def bar():
        ...


.. autoclass:: libclipy.core.venv.Venv
    :members: __call__

