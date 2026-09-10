from pathlib import Path
from cli import Target, env_prefix, default_venv_path, Env
from libclipy.cli_grep import grep_groups
from libclipy.cli_workflow import codes

# Constants
name = 'clipy'
version = '0.1.0'

# Environment variables
env = Env(env_prefix, system='dev', target='local', verbosity=0, work=Path('local'), venv=Path(default_venv_path), format='pretty')

# Config variables
@Target()
def local():
    grep_groups.v = {'tests':r'.*/_test.*', 'docs':r'docs/.*', 'core':r'libclipy/core/.*', 'tools':r'libclipy/tools/.*', 'libclipy':r'libclipy/.*'}
    codes.v = {
        '': ('', ['local', 'config.py']),
        'd': ('documentation', ['docs', 'README.rst']),
        'c': ('libclipy', ['libclipy', 'cli.py']),
    }
