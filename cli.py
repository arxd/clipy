#!/usr/bin/env python3
import sys
from pathlib import Path

# Program constants
name = 'clipy'
version = '1.3.2'
env_prefix = 'CLIPY_'
project_root = Path(sys.modules['cli' if 'cli' in sys.modules else '__main__'].__file__).resolve().parent

if __name__ == '__main__':
    sys.path.insert(0, str(project_root))
    # system and local_root are needed early for Venv selection and initalization, and must be passed down to sub-commands
    from libclipy.core.config import set_env_vars
    set_env_vars(env_prefix)
    
from libclipy.core.command.command import Command
from libclipy.core.venv import Venv
from libclipy.core.command.cmd import Cmd

@Venv(python="3.9", req='wcwidth')
@Command('libclipy.cli_install', 'libclipy.cli_config', 'libclipy.cli_lifecycle', 'libclipy.tools.nvm::nvm', 'libclipy.cli_gcp::gcp', 'libclipy.cli_project', 'libclipy.cli_web', 'libclipy.cli_grep', 'libclipy.cli_workflow', 'libclipy.cli_docs::docs', 'libclipy.cli_testing', sub_required=False)
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
    from libclipy.core.config import output
    if target__t is not None: config.target.v = target__t
    if verbose__v or quiet__q: config.verbosity.v = int(verbose__v) - int(quiet__q)
    if format__f is not None: output.v = format__f
# Run the sub command
    if _sub_cmd is not None: return _sub_cmd.exec()
# No sub command
    if version:
        from cli import version, name
        return print(f"{name} {version}")
    from libclipy.core.errors import HelpWanted
    raise HelpWanted(cmd=main())

if __name__ == '__main__': Cmd.entry_point(main.bin_path/'python', argv=sys.argv[1:])[0].exec()()
# Everything below here is only called when cli is imported (not executed)
from libclipy.core.config import ConfigVar, Target
from libclipy.core.errors import UsageError, PrettyException
from libclipy.core.pretty import print, CLR
