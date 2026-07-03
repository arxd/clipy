import shutil
from . import CLI
from pathlib import Path


class Project():
    def __init__(self, path='.'):
        from libclipy.tools.git import Git 
        self.git = Git(repo=Path(path).resolve())

    def __str__(self):
        return str(self.git.repo)
    
    def __eq__(self, other):
        return str(self) == str(other)
    
    def copy_here(self, path, src):
        ''' copy a file from this project to the given project '''
        d = self.git.repo/(path.with_suffix('') if path.suffix == '.tmpl' else path)
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src.git.repo/path, d)

    def core_files(self, tools=None):
        if tools == 'all': tools = ['gcloud', 'rsync']
        tools = [f'{f}.py' for f in (tools or [])]
        all = ['libclipy/main.py.tmpl', 'libclipy/CLI.py', 'libclipy/test_cli.py', 'cli.py', 'config.py', 'README.rst.tmpl', '.gitignore.tmpl']
        all += self.git.ls('libclipy/core')
        all += self.git.ls('libclipy/docs')
        all += [f"libclipy/tools/{f}" for f in tools + ['__init__.py', 'grep.py', 'sys_tool.py', 'run.py', 'git.py']]
        all += [f"docs/{f}" for f in ['_static/.gitkeep','_static/favicon.png','issues.rst.tmpl','conf.py']]
        return [Path(f) for f in all]


    def file(self, f):
        return self.git.repo / f




class Projects(list):
    def __init__(self):
        with open('local/projects') as f:
            super().__init__([Project(p) for p in f.readlines()])

    def ensure(self, p):
        if p not in self: self.append(p)
        self.save()

    def save(self):
        with open('local/projects', 'w') as f:
            f.write(''.join(f"{p}\n" for p in self))



@CLI.cmd()
def new_(project, tool__t=[]):
    ''' Create a new project

    Parameters:
        --tool <name>, -t <name>
            We need this tool from tools
    '''    
    clipy = Project()
    project = Project(project)
    Projects().ensure(project)

    if project.git.repo.exists(): raise ValueError(f"Project already exists: {project}")
    project.git.repo.mkdir()
    # Copy files
    for f in clipy.core_files(tool__t): project.copy_here(f, clipy)
    # Init git
    project.git('init', '-b', 'main')
    project.git('add', '.')
    project.git('commit', '-m', 'Boilerplate clipy code')



@CLI.cmd()
def diff(project):
    ''' Compare the files in this reference implementation to the files in a derived project
    '''
    import os, shutil
    from libclipy.tools.run import run

    clipy = Project()
    project = Project(project)
    # copy missing
    for f in clipy.core_files():
        fto = (f.with_suffix('') if f.suffix == '.tmpl' else f)
        if not project.file(fto).exists():
            print(f"Copy {fto!r} from to {project}?")
            if input("[y/N]: ").lower() == 'y': shutil.copy(clipy.file(f), project.file(fto))
    # diff
    for f in clipy.core_files('all'):
        if f.suffix == '.tmpl' or not project.file(f).exists(): continue
        out = run(['diff', '-u', '--color=always', project.file(f), clipy.file(f)], msg=None, if_0='null,null,', if_1='utf8,,')
        if out is None: continue
        print(out)
        c = input('Make changes to the (p)roject file or the (r)eference clipy file? ')
        if c == 'p': shutil.copy(clipy.file(f), project.file(f))
        if c == 'r': shutil.copy(project.file(f), clipy.file(f))



@CLI.cmd(new_, diff, 'libclipy.tools.grep', 'libclipy.core.docs.docs', 'libclipy.test_cli', need=CLI.pip('PyYAML'), sub='?')
def main(*, version=False, target__t=None, verbose__v=False, quiet__q=False):
    ''' The universal command line interface for all functionality contained in this project.

    Parameters:
        --version
            Print the program version and exit
        --target <target>, -t <target>
            Set the target, overriding the environment variable.
        --verbose, -v
            Set the output to be more verbose.
            Use this flag more than once ``-vvv`` to become more and more verbose.
        --quiet, -q
            The opposite of verbose.  Can be used repeatedly.
    '''
    if version:
        from config import name, version
        print(f"{name} {version}")
        return
    from libclipy.core.config import initialize_config_vars
    if target__t is not None: CLI.clipy_env.target = target__t
    if verbose__v or quiet__q: CLI.clipy_env.verbosity = int(verbose__v) - int(quiet__q)
    initialize_config_vars()
