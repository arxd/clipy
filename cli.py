#!/usr/bin/env python3
import sys, os, pathlib

# Program constants
name = 'clipy'
version = '1.1.0'
env_prefix = 'CLIPY_'

# Move to the project root and add the project root to sys.path
project_root = pathlib.Path(os.path.dirname(os.path.abspath(sys.modules['cli' if 'cli' in sys.modules else '__main__'].__file__)))
if __name__ == '__main__':
    sys.path.insert(0, str(project_root))
    os.chdir(project_root)
    from libclipy.core.config import system
    system.v = os.environ.get(f'{env_prefix}SYSTEM', 'dev')

from libclipy.core.command.command import Command
from libclipy.core.venv import Venv
from libclipy.core.command.cmd import Cmd

@Venv(python="3.9", req='wcwidth')
@Command('libclipy.cli_install', 'libclipy.cli_project', 'libclipy.cli_web', 'libclipy.cli_grep', 'libclipy.cli_workflow', 'libclipy.cli_docs::docs', 'libclipy.cli_testing', sub_required=False)
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
    from libclipy.core.config import format_out
# target
    if target__t is not None: config.target.v = target__t
# verbosity
    if verbose__v or quiet__q: config.verbosity.v = int(verbose__v) - int(quiet__q)
# output format
    if format__f is not None: format_out.v = format__f
    format_kinds = {'pretty', 'json', 'pickle'}
    if format_out.v not in format_kinds: raise UsageError('Invalid format: "%s" is not one of [ %s ]'%(format_out.v, ' | '.join(format_kinds)))
# Run the sub command
    if _sub_cmd is not None: return _sub_cmd.exec()
# No sub command
    if version:
        from cli import version, name
        return dict(name=name, version=version)
    from libclipy.core.errors import HelpWanted
    raise HelpWanted(cmd=main())

if __name__ == '__main__': Cmd.entry_point(main.bin_path/'python', argv=sys.argv[1:])[0].exec()()
# Everything below here is only called when cli is imported (not executed)
from libclipy.core.config import ConfigVar, Target
from libclipy.core.errors import UsageError, PrettyException
from libclipy.core.pretty import print, CLR
