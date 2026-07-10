.. _page-issues:

========
Issues
========

* ./cli.py is showing the full depth of commands
* logging / logger class
* env passed through dict
* pyml

  * print/log object streaming
  * pretty formatting
  * docstring parsing

* vault
* async Venv.each_async()
* async generator commands
* test-file specific venv

  * consolidate the different test runs into a single coverage report

* Maybe make the initialization code of entry_point more flexable (override-able?)


docs/commands.rst review
========================

Cross-checked against ``libclipy/core/command/{command,dfn,param,errors}.py`` and ``entry_point.py``.
Findings ordered roughly by severity.


Correctness (wrong or currently false)
--------------------------------------

3. “Empty list” examples: second case errors (lines 559–565)

   ::

       $ ./cli.py foo -y -
       x=1  y=[2,3]

   With ``y=[2,3]``, ``-y -`` raises ``MissingArgument``, not “keep default”.
   ``foo - -`` is fine (skip both positionals → defaults). The claim that there is no CLI way to set an
   empty list is still true; the second example is simply wrong.


18. Generators nested only under Sub-commands

    Generators work without children. A top-level “Generators” section (with a subsection on mapping
    over implicit children) would scan better.


19. Missing from Types

    * Custom types via ``@ParamType()`` / subclass (supported and tested).
    * Annotation wins over default for type inference (``a:int=None`` is int, not “unknown”).
    * Mutable defaults like ``c=[]`` work for typing empty lists as ``list[str]`` but are a Python
      footgun worth a caution.




Suggested priority for edits
----------------------------

1. **Fix wrong examples**: hello invocation/flags; ``-y -`` empty-list case; hidden-params syntax +
   expected errors/output; generator CLI/``wait``/``each_async`` claims.
2. **Fix bool keyword value docs** to match ``Bool.parse``.
3. **Fix reST** on the flag-group ref; grammar/period; ``./cli.py`` consistency.
4. **Add short clarifications**: dashed command names, reserved help, prefix subcommands,
   annotation-vs-default typing, ``sub_required`` default rule.
5. **Restructure lightly**: promote Generators; separate “CLI convention for docstrings” from
   “signature is the interface.”
