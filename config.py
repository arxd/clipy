from cli import Target, ConfigVar, Venv
from libclipy.cli_grep import grep_groups
from libclipy.cli_workflow import codes
from libclipy.core.config import verbosity, local_root, format_out, system, target
venv_root = Venv.root

@Target()
def local():
    grep_groups.v = {'tests':r'.*/_test.*', 'docs':r'docs/.*', 'core':r'libclipy/core/.*', 'web':r'(libclipy/)?web/.*', 'tools':r'libclipy/tools/.*', 'libclipy':r'libclipy/.*'}
    
    codes.v = {
        '': ('', ['local', 'config.py']),
        'd': ('documentation', ['docs', 'README.rst']),
        'c': ('libclipy', ['libclipy', 'cli.py']),
        'w': ('web', ['web']),
    }
