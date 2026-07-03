from . import CLI

@CLI.cmd()
def new_(project, tool__t=[]):
    ''' Create a new project

    Parameters:
        --tool <name>, -t <name>
            We need this tool from tools
    '''
    import shutil
    from pathlib import Path
    from libclipy.tools.git import Git
    dest = Path(project).resolve()
    if dest.exists(): raise ValueError(f"Project already exists: {dest}")
    dest.mkdir()
    def _cp(files):
        for f in [Path(f) for f in files]:
            if f.name.startswith('_'): continue
            d = dest/(f.with_suffix('') if f.suffix == '.tmpl' else f)
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, d)
# Copy files
    _cp(list(Git().ls('libclipy/core')))
    _cp(list(Git().ls('libclipy/docs')))
    _cp(f"libclipy/tools/{f}" for f in ['__init__.py', 'grep.py', 'sys_tool.py', 'run.py', 'git.py'])
    _cp(['libclipy/main.py.tmpl', 'libclipy/CLI.py', 'cli.py', 'config.py', 'README.rst.tmpl', '.gitignore.tmpl'])
    _cp(f"docs/{f}" for f in ['_static/.gitkeep','_static/favicon.png','issues.rst.tmpl','conf.py'])
# Init git
    git = Git(repo=dest)
    git('init', '-b', 'main')
    git('add', '.')
    git('commit', '-m', 'Boilerplate clipy code')



@CLI.cmd()
def diff(project):
    ''' Compare the files in this reference implementation to the files in a derived project
    '''
    import os, shutil
    from libclipy.tools.git import Git
    from libclipy.tools.run import run
    ref = set([f for f in Git().ls('libclipy') if not os.path.split(f)[1].startswith('_test')])
    proj = set(Git(repo=project).ls('libclipy'))
# Look for files in project that are missing in the reference
    for f in proj-ref:
        print(f"Copy {f!r} from {project} to reference?")
        if input("[y/N]: ").lower() == 'y': shutil.copy(os.path.join(project, f), f)
# Look for files in reference that are missing in the project
    for f in ref-proj:
        print(f"Copy {f!r} from reference to {project}?")
        if input("[y/N]: ").lower() == 'y': shutil.copy(f, os.path.join(project, f))
# Look for differences in individual files
    #print(f"in reference but not in {project}: {' '.join(ref-proj)}")
    for f in ref&proj:
        out = run(['diff', '-u', '--color=always', os.path.join(project,f), f], msg=None, if_0='null,null,', if_1='utf8,,')
        if out is None or f in ['libclipy/main.py']: continue
        print(out)
        print(f)
        c = input('Keep the (p)roject file or the (r)eference file? ')
        if c == 'p': shutil.copy(os.path.join(project, f), f)
        if c == 'r': shutil.copy(f, os.path.join(project, f))



@CLI.cmd(new_, diff, 'libclipy.tools.grep', 'libclipy.core.docs', 'libclipy.test_cli', need=CLI.pip('PyYAML'))
def main(*, target__t=None, verbose__v=False, quiet__q=False):
    ''' The universal command line interface for all functionality contained in this project.

    Parameters:
        --target <target>, -t <target>
            Set the target, overriding the environment variable.
        --verbose, -v
            Set the output to be more verbose.
            Use this flag more than once ``-vvv`` to become more and more verbose.
        --quiet, -q
            The opposite of verbose.  Can be used repeatedly.
    '''
    if target__t is not None: CLI.env.target = target__t
    CLI.env.verbosity = int(verbose__v) - int(quiet__q)
