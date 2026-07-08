============
Design
============


The primary design decision is that a function (`Command`) should be the entrypoint instead of using scripts.
This reduces cognitive load by logically mapping the function's docstring and parameters to the command line interface.

The next major design is to have each `Command` (in the chain of commands) run in a separate process.
This was done for a few reasons:

* Each command gets a 'clean' execution environment to reduce cognitive load.
* Reduces the complexity of mixing sync and async functions.

    Notably, you can't wait for an async function from within a sync function when there is already a loop running.
    Therefore you must run nested event loops in a different thread or process.
    You can't run them in a different thread because it is not possible to stop a thread once it is running, and if you receive SIGINT you need to be able to cancel the threads.
    Which leaves only multiprocessing.

Running each `Command` in its own process has the downside of requiring that arguments and return-values are pickleable.
Also, for niceness, os.exec() is used for tail-call optimization when possible.


Code Layout
=============

cli.py
---------

This serves a dual role.

1) It is executable __name__=='__main__' and bootstraps command execution
2) It is an importable library of project configuration and useful cli related objects

libclipy
----------

This holds the code that is clipy related tooling and should be relatively independent of the project-specific code.
Project-specific commands can go in here, but ideally they should be relatively simple wrappers around project libraries and interfaces.

libclipy/tools
----------------

These map one-to-one with system tools and provide simple, convenient wrappers to use them.

libclipy/core
---------------

This code should, ideally, not need to be touched, but it is there if tweaks need to be made.

docs
-------

Sphinx based documentation

docs/_dist
-----------

This is a git branch that holds the built documentation.

.python
-----------

The default location for the python virtual environments.  This can be deleted whenever you feel like it.

local
---------

This is the default location of the working directory.
A location outside of git's jurisdiction for temporary files and other longer-lived project-specific runtime files.

