import shutil, json, hashlib
from pathlib import Path
from config import env
from collections import namedtuple
from libclipy.tools.git import Git
from cli import UsageError
from libclipy.core.pretty import CLR

DFile = namedtuple('DFile', ('path', 'status', 'ref_hash', 'proj_hash', 'proj_hash_cached'))

class Project():
    info_file = 'libclipy/core/info.json'

    def __init__(self, path='.', sync_hashes=None):
        self.git = Git(repo=Path(path).resolve())
        self.sync_hashes = sync_hashes or {}

    def __str__(self):
        return str(self.git.repo)
    
    def __eq__(self, other):
        return str(self) == str(other)


    @classmethod
    def all(self):
        yield from Projects().all.values()


    @classmethod
    def lookup(self, name):
        return Projects()[name]
    

    @property
    def info(self):
        ''' Read the info metadata from the top comment of cli.py
        '''
        if not hasattr(self, '_info'):
            with open(self.file(Project.info_file)) as f:
                self._info = json.load(f)
        return self._info
    

    def set_info(self, **kwargs):
        self.info.update(kwargs)
        with open(self.file(Project.info_file),'w') as f:
            json.dump(self._info, f)

    
    def copy_to(self, path, proj):
        ''' Copy a file `path` from this (clipy) project to `proj`.
        '''
        dest = proj.file(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.file(path), dest)


    def _feature_files(self, feature):
        ''' Yields files (relative paths) needed for the given feature.
        This only works when Project('.') is the clipy repository.
        '''
        clipy = Project()
        if feature == 'core':
            yield from ['cli.py', 'libclipy/__init__.py', ]
            yield from [f"libclipy/tools/{f}" for f in ['__init__.py', 'sys_tool.py', 'run.py', 'git.py']]
            yield from [f for f in clipy.git.ls('libclipy/core') if not f.name.startswith('_test') and f.name!='info.json']
        elif feature == 'web':
            yield from self._feature_files('nginx')
            yield from self._feature_files('openssl')
            yield 'libclipy/cli_web.py'
            yield from [f for f in clipy.git.ls('web')]
            yield from [f for f in clipy.git.ls('libclipy/web')]
        elif feature == 'docs':
            yield from [f for f in clipy.git.ls('libclipy/docs') if not f.name.startswith('_test')]
            yield from [f"docs/{f}" for f in ['_static/.gitkeep','_static/favicon.png','issues.rst.tmpl','conf.py']]
        elif feature.startswith('lib.'):
            yield f'libclipy/{feature[4:]}.py'
        elif feature.startswith('cli.'):
            yield f'libclipy/cli_{feature[4:]}.py'
        elif not Path(f'libclipy/tools/{feature}.py').exists():
            raise ValueError(f"Unknown Feature: {feature}")
        else:
            yield f'libclipy/tools/{feature}.py'


    def files(self, *features):
        ''' Returns a list of file Paths matching the features this project subscribes to
        '''
        files = set()
        for feature in ['core', *(features or self.info['features'])]:
            files.update(set(self._feature_files(feature)))
        return set([Path(f) for f in files])


    def file(self, f):
        p = self.git.repo / f
        return p.with_suffix('') if not p.exists() and p.suffix == '.tmpl' else p


    def diff(self):
        ''' Figure out what files differ between this project and the clipy reference.
        '''
        clipy = Project()
        files = set(map(str, clipy.files(*self.info['features'])))
        dfs = {}
        # Deprecated files
        for f in set(self.info['hashes'].keys()) - files:
            dfs[f] = DFile(f, 'd', None, None, None)
        # Expected files
        for f in files:
            hs = clipy.hash(f), self.hash(f)
            proj_hash_cached = self.sync_hashes.get(f)
            status = 'r'*(hs[0] != self.info['hashes'].get(f))
            status += 'p'*(hs[1] != proj_hash_cached)
            dfs[f] = DFile(f, status, *hs, proj_hash_cached)
        return dfs


    def hash(self, path):
        try:
            with open(self.file(path), 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return ''


    def description(self):
        desc = []
        with open(self.file('README.rst')) as f:
            while (line:=f.readline()).strip(): pass
            while (line:=f.readline()).strip(): desc.append(line)
        return ''.join(desc)


    def set_sync_hashes(self, hashes):
        self.sync_hashes = hashes
        p = Projects()
        p[str(self)].sync_hashes = hashes
        p.save()


    def verify_features(self, features):
        for f in features:
            if f not in self.info['features']:
                raise UsageError(f"Invalid feature: {CLR.r}{f}{CLR.x}\nMust be one of: {CLR.m}{' '.join(self.info['features'])}{CLR.x}")



class Projects():
    ''' A cached list of known clipy projects
    '''
    @property
    def all(self):
        if not hasattr(self, '_all'):
            try:
                with open(env.work/'projects.json','rb') as f:
                    self._all = {p:Project(p, sync_hashes=s) for p,s in json.load(f).items()}
            except Exception:
                self._all = {}
        return self._all


    def __getitem__(self, name):
    # If it is a pathname make it a full path.
        if isinstance(name, Path) or Path(name).exists():
            name = str(Path(name).resolve())
    # Is name just the project name?
        match = [p for p in self.all if p.endswith('/'*(name[0]!='/') + name)]
        if len(match) == 1: return self.all[match[0]]
        if len(match) > 1: raise ValueError(f"Multiple projects matching {name!r}: {[str(m) for m in match]}")
    # A new project
        if name[0] != '/': raise ValueError(f"Project not found: {name!r}")
        p = Project(name)
        if not p.info.get('version'): raise ValueError(f"Not a clipy project: {p}")
        self._all[str(p)] = p
        self.save()
        return p


    def save(self):
        with open(env.work/'projects.json', 'w') as f:
            json.dump({str(p):p.sync_hashes for p in self._all.values()}, f)
    