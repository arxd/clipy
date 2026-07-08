import shutil
from config import env
from libclipy.tools.git import Git 
from cli import Command, UsageError, run
from pathlib import Path



class Project():
    @classmethod
    def lookup(self, name):
        all = Projects()
        if (Path(name)/'cli.py').exists():
            p = Project(name)
            all.ensure(p)
            return p
        return all.lookup(name)

    def __init__(self, path='.'):
        self.git = Git(repo=Path(path).resolve())

    def __str__(self):
        return str(self.git.repo)
    
    def __eq__(self, other):
        return str(self) == str(other)
    
    def copy_here(self, path, src):
        ''' copy a file `path` from the `src` project to this project '''
        d = self.git.repo/(path.with_suffix('') if path.suffix == '.tmpl' else path)
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src.git.repo/path, d)

    def core_files(self, tools=None):
        if tools == 'all': tools = ['gcloud', 'rsync', 'aws', 'docker']
        tools = [f'{f}.py' for f in (tools or [])]
        all = ['cli.py', 'config.py', 'README.rst.tmpl', '.gitignore.tmpl']
        all += [f"libclipy/{f}" for f in ['main.py.tmpl', 'grep.py', 'hide.py', 'testing.py', '__init__.py']]
        all += [f for f in self.git.ls('libclipy/core') if not f.name.startswith('_test')]
        all += [f for f in self.git.ls('libclipy/docs') if not f.name.startswith('_test')]
        all += [f"libclipy/tools/{f}" for f in tools + ['__init__.py', 'sys_tool.py', 'run.py', 'git.py']]
        all += [f"docs/{f}" for f in ['_static/.gitkeep','_static/favicon.png','issues.rst.tmpl','conf.py']]
        return [Path(f) for f in all]


    def file(self, f):
        return self.git.repo / f



class Projects(list):
    def __init__(self):
        try:
            with open(env.work/'projects') as f:
                super().__init__([Project(p.strip()) for p in f.readlines()])
        except:
            pass

    def lookup(self, prefix):
        for p in self:
            if p.git.repo.name.startswith(prefix): return p

    def ensure(self, p):
        if p not in self: self.append(p)
        self.save()

    def save(self):
        with open(env.work/'projects', 'w') as f:
            f.write(''.join(f"{p}\n" for p in self))



@Command()
def new_(project, tool__t=[]):
    ''' Create a new project

    Parameters:
        <project_path>
            A path to the new project root
        --tool -t [tool_name]
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



@Command()
def diff(project_name):
    ''' Compare the files in this reference implementation to the files in a derived project
    
    Parameters:
        <project>
            The path to the project to compare against.
            If you give just the project name then the local/projects file will be searched to find the path.
    '''
    if not (project:=Project.lookup(project_name)): raise UsageError(f"Couldn't locate {project_name!r}")
    clipy = Project()
    # copy missing
    for f in clipy.core_files():
        fto = (f.with_suffix('') if f.suffix == '.tmpl' else f)
        if not project.file(fto).exists():
            print(f"Copy missing {fto}")
            if input("[y/N]: ").lower() == 'y': project.copy_here(fto, clipy)
    # diff
    for f in clipy.core_files('all'):
        if f.suffix == '.tmpl' or not project.file(f).exists(): continue
        out = run(['diff', '-u', '--color=always', project.file(f), clipy.file(f)], msg=None, if_0='null,null,', if_1='utf8,,')
        if out is None: continue
        print(out)
        c = input('Make changes to the (p)roject file or the (r)eference clipy file? ')
        if c == 'p': shutil.copy(clipy.file(f), project.file(f))
        if c == 'r': shutil.copy(project.file(f), clipy.file(f))


@Command()
def cp(file, project_name):
    if not (project:=Project.lookup(project_name)): raise UsageError(f"Couldn't locate {project_name!r}")
    clipy = Project()
    project.copy_here(Path(file), clipy)
