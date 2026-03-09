.. _page-config:

==================
Configuration
==================

Any function needs parameters.  There are explicit parameters that are sent to the function.
There is also ambient parameters (global variables) that the function can use.

To ease cognitive load, these global parameters should be constants.
A `target` is in charge of giving them their initial value.

from .bob.cob import x, y==

x, y = Config('.bob.cob', 'x y')

Variables 
============

Each variable needs a name, but what about namespacing if two unrelated packages want to use the same name?
If there were a single config dictionary that held all of the configuration then there would be namespace issues.

The solution is to let the names live in the module namespace and let import deal with name conflicts just like any other module-level object.


Configuration variables are global variables so they use standard python import namespacing.

Secrets
---------

No secret (passwords, keys) should be stored in configuration variables.  They should be stored in files (in the vault)
and the file path should be given in a configuration variable.  One text file for each variable.  Don't put them
all together in one json file.

``vault/config.py`` is not really a secret.  It just isn't generically applicable to the application.  Semi-secret.



.. _target:

Targets
=========

Configuration values are grouped into **targets**.  A target is a function that sets some configuration
values.  Targets are defined with the ``@Config.target`` annotation.  There are three locations where targets
can be defined:

* ``config.py``  This is for deployment agnostic targets like ``local`` and ``test``
* ``local/config.py``  This is for defining custom targets that can be used for testing/debugging but won't be pushed to git.
* ``vault/config.py``  Targets in here are only relevant for deployments like ``prod`` and ``client``

Targets can be chained ``local.sub1``, ``local.sub1.sub2``.  
The target functions are just called in order so subsequent targets can override variables from the parents.

Set the target with ``-t`` when calling `cli`.


Environment
=============

This is a broad term, and often used interchangeably with `targets <page-config>`, but it is a different concept in clipy.
An environment is *where* cli.py is being executed and what it can import.

* Is it running in a development environment on your laptop?
* Is it running in a docker container executing a specific tooling function?
* Is it running on the production server or device?

The environment determines which modules python has access to, as well as other things like network access.
In a dev environment you might need a different set of modules from the prod environment.
Are you running with a python venv, or using the system python?

Which modules are available determines which commands are executable in an environment.
Because, obviously, if the command can't import the modules it needs, then it can't run.

There is a distinction to be made between the ability to import a command, and run a command.
Even if you can't run a command (because of a missing libary), it is helpful to be able to import the command so that you can read, and display, its help documentation.
The local/dev environment is where the user interacts dynamically with cli.py, so in that environment, all commands need to be importable (even if not runnable) so that documentation can be generated.
In other environments, like production, it may be fine if you can't import all commands, since only a subset of the commands may be used.



