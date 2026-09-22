#!/usr/bin/env python3
import sys, os, logging

env_prefix = 'CLIPY_'
default_venv_path = '.python'

# Move to the project root and add the project root to sys.path
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__)))
    os.environ['_CLIPY_ROOT'] = sys.path[0]
    os.chdir(sys.path[0])

# Setup the default environment used to import main (and all commands)
from libclipy.core.venv import Venv
default_venv = Venv(base=os.environ.get(env_prefix+'VENV', default_venv_path), python='>=3.9', requirements='wcwidth')

# Get into the default virtual environment and execute main().  Execution in script-mode stops here with an os.exec() call.
if __name__ == '__main__': default_venv.exec(sys.argv[1:])


# Everything below here is only called when cli is imported (not executed)
from libclipy.core.command.command import Command
from libclipy.core.config import ConfigVar, Target, Env
from libclipy.core.errors import UsageError, PrettyException
from libclipy.tools.run import Exec, run, RunException
from libclipy.core.pretty import print, CLR


@Command('libclipy.cli_project', 'libclipy.cli_web', 'libclipy.cli_grep', 'libclipy.cli_workflow', 'libclipy.docs', 'libclipy.cli_testing', sub_required=False)
def main(*, _sub_cmd, version=False, target__t=None, verbose__v=False, quiet__q=False, format__f=None):
    ''' The universal command line interface for all functionality contained in this project.

    Parameters:
        --version
            Print the program version and exit
        --target -t <target>
            Set the target, overriding the environment variable.
        --verbose -v
            Set the output to be more verbose.
            Use this flag more than once ``-vvv`` to become more and more verbose.
        --quiet -q
            The opposite of verbose.
        --format -f <json|pretty|pickle>
            How should objects returned from commands be formatted for stdout?
    '''
    import config
# target
    if target__t is not None: config.env.target = target__t
    targets = [k for k in dir(config) if isinstance(getattr(config,k), Target)]
    if config.env.target not in targets: raise UsageError('Invalid target: "%s" is not one of [ %s ]'%(config.env.target, ' | '.join(targets)))
# verbosity
    if verbose__v or quiet__q: config.env.verbosity = int(verbose__v) - int(quiet__q)
# output format
    if format__f is not None: config.env.format = format__f
    format_kinds = {'pretty', 'json', 'pickle'}
    if config.env.format not in format_kinds: raise UsageError('Invalid format: "%s" is not one of [ %s ]'%(config.env.format, ' | '.join(format_kinds)))
# Run the sub command
    if _sub_cmd is not None: return _sub_cmd.exec()
# No sub command
    if version: return dict(name=config.name, version=config.version)
    from libclipy.core.command.errors import HelpWanted
    raise HelpWanted(cmd=main.instance())
