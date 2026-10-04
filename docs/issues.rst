.. _page-issues:

========
Issues
========

* The new command's sed handling of config.py is too brittle.  Take into account given features?
* ./cli.py is showing the full depth of commands

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
* Produce clipy docs from docstrings (liblcipy/docs/docs.py)



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

Command subprocesses
=============================

* Sending args to subprocesses: currently if the sending pipe fills up and blocks the subprocesses will never be opened to read from it.  deadlock
* Pass log objects through the out pipe to the parent
* When a sub-command does an Exec it should close its output pipe to the parent but the parent still waits for it to exit.

    * The Exec system needs to know if it should close the output pipe or not.

* make Command sub-processes work the same as run() sub processes.

    * run(...) is an alias for cmd(...).run()
    * await cmd(...).wait()
    * for line in cmd(...).each(): ...
    * with cmd(...) as proc: ...
    * return cmd(...).exec()


No win32 support
==================

* The shm_open in libclipy/core/command/channels.py::Mem
* selector stuff in Cmd ?


  ┌──────────────────────────────────────┬────────────────────────────────┐
  │                runner                │            outcome             │
  ├──────────────────────────────────────┼────────────────────────────────┤
  │ asyncio.run(main())                  │ child survived, marker missing │
  ├──────────────────────────────────────┼────────────────────────────────┤
  │ manual loop + shutdown_asyncgens()   │ child gone, cleaned up         │
  ├──────────────────────────────────────┼────────────────────────────────┤
  │ manual loop, no shutdown_asyncgens() │ child survived, marker missing │
  └──────────────────────────────────────┴────────────────────────────────┘
So asyncio.run() — the one that does call shutdown_asyncgens — is the one that fails. The mechanism is in CPython's
_asyncgen_finalizer_hook: it discards the generator from loop._asyncgens and then schedules agen.aclose() as a task. asyncio.run
runs _cancel_all_tasks() before shutdown_asyncgens(), so that task is cancelled before its first step — kill_proc never runs, no
SIGINT is ever sent — and by then shutdown_asyncgens() finds an empty set. The cleanup isn't delayed; it's destroyed.

Row 2 passes for a subtler reason than its name suggests: not because shutdown_asyncgens found the generator, but because the
loop simply ran again and let the pending aclose task take its step.

entry_point.run_coro (entry_point.py:97) has the same shape — cancel pending tasks, then shutdown_asyncgens — so it has the same
hole.

Let me encode all three runners as tests, and fix the two test defects I hit:



The three failures, in order of importance:

1. test_nothing_outlives_the_parent — your MUST, violated. Measured directly: the leaker exits in 0s with status 0, the marker is
never written, and the child is still alive.

The mechanism is nastier than "cleanup is late". CPython's _asyncgen_finalizer_hook discards the generator from loop._asyncgens
and then schedules agen.aclose() as a task. asyncio.run() calls _cancel_all_tasks() before shutdown_asyncgens(), so that task is
cancelled before its first step — kill_proc() never runs, no SIGINT is ever sent — and shutdown_asyncgens() then finds an empty
set. The safety net is removed before it can catch anything.

Three runners, isolated:

┌────────────────────────────────────┬────────────────┐
│               runner               │     result     │
├────────────────────────────────────┼────────────────┤
│ asyncio.run(main())                │ child survived │
├────────────────────────────────────┼────────────────┤
│ manual loop + shutdown_asyncgens() │ cleaned up     │                                                        
├────────────────────────────────────┼────────────────┤
│ manual loop, no extra turn         │ child survived │
└────────────────────────────────────┴────────────────┘

Row 2 passes because the loop simply runs once more and lets the pending aclose task take its step — not because
shutdown_asyncgens found anything. I made that a separate test (..._when_the_loop_runs_on) so the contrast is visible.

Worth noting: entry_point.run_coro has the same shape — cancel pending tasks, then shutdown_asyncgens (entry_point.py:97-104).
The comment there says it settles tasks first "exactly as asyncio.run() does", which is accurate and is exactly the problem.

2. test_nothing_outlives_the_parent_with_a_bare_loop — same requirement with every async route removed. An async generator cannot
be finalized without a loop, so nothing asynchronous can ever help here. Only a synchronous backstop can: atexit, or __del__ on
AsyncIterator. This is where my earlier "atexit is unnecessary" conclusion stops applying — that held for the sync path only.

3. test_a_failing_child_is_reported — a sync/async divergence, not a lifetime issue. each() raises CmdError on a non-zero exit
(iter_sync.next_step); each_async() never looks at the return code. The sync half of that test raises; the async half doesn't.

Two test defects I hit and fixed along the way, both worth knowing because they hid real failures: CHILD_MARKER prints every
0.2s, so it dies of BrokenPipeError when its parent goes — the lifetime tests were passing without any cleanup running, so they
now use a silent child. And capture_output=True made a surviving child hang the test, because the orphan inherits the captured
stdout pipe and communicate() waits on it; the leaker's stdio now goes to files.