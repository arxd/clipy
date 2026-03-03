#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# This file may be executed with python 2.7 if the user's system is old.
# So its syntax must be python2 compatible.
if __name__ == '__main__':
    import sys
    from libclipy.setup import ensure_environment
    
    # First make sure we are running a version of python compatible with this project.
    # If a specific pip package version changes, and thereby causes a package conflict with a different branch, change venv to a different subdirectory
    # You can also choose None if you don't need a virtual environment, and you want to rely on the system packages
    ensure_environment(r'3.10.\d+$', 'v1')

    from libclipy.main import main
    main.prepare()
    result = main.bind(*sys.argv[1:])()
    if result is not None: print(result)
