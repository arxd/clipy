.. _page-issues:

========
Issues
========

* The new command's sed handling of config.py is too brittle.  Take into account given features?
* ./cli.py is showing the full depth of commands
* logging / logger class
* env passed through dict
* pyml

  * print/log object streaming
  * pretty formatting
  * docstring parsing
  * docstring verification (that it matches the signature)

* vault
* test-file specific venv

  * consolidate the different test runs into a single coverage report

* Maybe make the initialization code of entry_point more flexable (override-able?)


3. “Empty list” examples: second case errors (lines 559–565)

   ::

       $ ./cli.py foo -y -
       x=1  y=[2,3]

   With ``y=[2,3]``, ``-y -`` raises ``MissingArgument``, not “keep default”.
   ``foo - -`` is fine (skip both positionals → defaults). The claim that there is no CLI way to set an
   empty list is still true; the second example is simply wrong.


19. Missing from Types

    * Annotation wins over default for type inference (``a:int=None`` is int, not “unknown”).
    * Mutable defaults like ``c=[]`` work for typing empty lists as ``list[str]`` but are a Python
      footgun worth a caution.


- each() re-raises an unpickled exception at :125, which skips the proc.wait()/returncode check at :129-130. The design above keeps the returncode check after the loop so the finally is the only cleanup path.

- Venv.system_packages is only assigned when not self.use_parent (venv.py:29-33), but venv_path() reads it at :65. Running each() from a python outside the .python/<hash>/bin/ layout makes hash() (venv.py:46) scrape a bogus name, miss the directory, and fail with AttributeError: 'Venv' object has no attribute 'system_packages' instead of a clear error. Pre-existing and out of scope, but it is the failure each_async's executor-wrapped venv_path call will surface, so it should propagate cleanly rather than hang the generator.

- When a (generator) parent breaks and needs to SIGINT its child early, the out pipe is closed on the parent side while the child is still trying to write to it.  This is protected against in the child (entry_point) but maybe the parent should keep the pipe open so that the child can continue to send log info during cleanup.


ctlr-c wait
==============

A single ctlr-c does a nice shutdown (send SIGINT to child processes and wait (DON'T do proc.kill() in _cleanup))
subsequent SIGINT will be ignored for a few seconds.
If we still aren't done after a couple of seconds then display a message saying "Ctl-C again for a hard kill (subprocess may leak)"
Then the next SIGINT sends SIGKILL to subprocesses and os._exit()

Sending args to subprocesses
=============================

Currently if the sending pipe fills up and blocks the subprocesses will never be opened to read from it.  deadlock


