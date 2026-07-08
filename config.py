from pathlib import Path
from cli import Target, env_prefix, default_venv_path, Env
from libclipy.grep import grep_groups

# Constants
name = "clipy"
version = "0.0.1"

# Environment variables
env = Env(env_prefix, system='dev', target='local', verbosity=0, work=Path('local'), venv=Path(default_venv_path), format='pretty')

# Config variables

@Target()
def local():
    grep_groups.v = {'tests':r'.*/_test.*', 'docs':r'docs/.*', 'core':r'libclipy/core/.*', 'tools':r'libclipy/tools/.*', 'libclipy':r'libclipy/.*'}


