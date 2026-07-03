========
Issues
========

Missing functionality
----------------------

* pyml

  * print/log object streaming
  * pretty formatting
  * docstring parsing

* vault
* generator commands


venv building
----------------

We don't want to needlessly build a venv and install tools for simple commands that don't need anything (docs view).

We do want to ensure a consistent locked venv for certain environments.

We need to collect package requirements per-command
