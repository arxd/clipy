.. _page_config:

#############
Configuration
#############

.. contents::
    :local:


Targets
*******

Configuration values are grouped into **targets**.  A target is a function that sets some configuration
values.  Targets are defined with the ``@Config.target`` annotation.  There are three locations where targets
can be defined:

* ``config.py``  This is for deployment agnostic targets like ``local`` and ``test``
* ``local/config.py``  This is for defining custom targets that can be used for testing/debugging but won't be pushed to git.
* ``vault/config.py``  Targets in here are only relevant for deployments like ``prod`` and ``client``

Targets can be chained ``local.sub1``, ``local.sub1.sub2``.  
The target functions are just called in order so subsequent targets can override variables from the parents.

Set the target with ``-t`` when calling `cli`.


Secrets
*******

No secret (passwords, keys) should be stored in configuration variables.  They should be stored in files (in the vault)
and the file path should be given in a configuration variable.  One text file for each variable.  Don't put them
all together in one json file.

``vault/config.py`` is not really a secret.  It just isn't generically applicable to the application.  Semi-secret.


Variables
*********
