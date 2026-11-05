from .config import ConfigVar
from pathlib import Path


class Venv():
    ''' This represents a desired virtual environment for a command.
    '''
    root = ConfigVar('Venv.root The path where the python virtual environments will be kept.  A relative path will be relative to local_root.', default='.python', cast=Path)

    @classmethod
    def all(self, *patterns):
        from cli import main
        venvs = {}
        for name, cmd in main.sub_command_tree(*patterns):
            for venv in cmd.venv or main.venv:
                venvs.setdefault(hash := venv.hash(), (venv,[]))
                venvs[hash][1].append((name,cmd))
        return dict(venvs.values())


    def __init__(self, parent=None, *, python=None, req=None, system_packages=None, system=None):
        ''' Define a virtual environment.

        All parameters can be strings using space-separation, or lists.

        Parameters:
            python | default None
                The required python version. e.g. '3.10' or '>=3.10 <3.13'
                If `None` then the current executing python is used.

            req | default None
                Packages that need to be installed in this virtual environment.

            system_packages
                Allow system packages to be visible from the virtual environment.
            
            system
                The external system environment (or a list of environments) that this virtual environment is valid for.
        '''
        _to_list = lambda v: [x.strip() for x in v.split(' ') if x.strip()] if isinstance(v, str) else list(v)
        self.parent = parent
        self.python = python and _to_list(python)
        self.req = req and set(_to_list(req))
        self.system_packages = system_packages
        self.system = system and set(_to_list(system))


    def __repr__(self):
        args = ', '.join(f'{k}={v!r}' for k,v in self.__dict__.items())
        return f"Venv#{self.hash()}({args})"

    
    def computed(self):
        import sys
        try: return self._computed
        except AttributeError: pass
        base = None
        if isinstance(self.parent, Venv): base = self.parent
        elif hasattr(self.parent, 'get_venv'): base = self.parent.get_venv(self.system)
        elif isinstance(self.parent, str):
            import importlib
            module, name = self.parent.split('::')
            base = getattr(importlib.import_module(module), name).get_venv(self.system)
        elif self.parent is not None: raise ValueError(f"Invalid parent: {self.parent}")
        python, req, system_packages, system = base.computed() if base else (["%d.%d.%d"%sys.version_info[:3]], set(), False, set()) 
        # FIXME: Merge reqs better even if there are versions attached
        self._computed = (self.python or python, req | (self.req or set()), system_packages if self.system_packages is None else self.system_packages, system if self.system is None else self.system)
        return self._computed


    def for_system(self, systems):
        self_systems = self.computed()[3]
        return not self_systems or not (systems - self_systems)


    def hash(self, system=''):
        if not hash:
            from .config import system as sys
            system = sys.v
        import hashlib
        python, req, system_packages, _ = self.computed()
        fingerprint = ';'.join(sorted(python)) + ';'.join(sorted(req)) + f';{system_packages};{system}'
        return hashlib.sha256(fingerprint.encode()).hexdigest()[:40]


    def __call__(self, cmd):
        ''' This venv can be used as a decorator to a `Command`
        '''
        cmd.venv.insert(0, self)
        return cmd
    

    def venv_path(self, path='', system=''):
        try: return self._venv_path/path
        except AttributeError: pass 
        import json, random
        from cli import project_root
        from config import local_root
        info_path = project_root/'libclipy'/'core'/'info.json'
        info = json.loads(info_path.read_text(encoding='utf8'))
        hash = self.hash(system)
        if hash not in info['venvs']:
            info['venvs'][hash] = {'folder':random.randbytes(16).hex()}
        self._venv_path = local_root.path(Venv.root.v.expanduser() / info['venvs'][hash]['folder'])
        if not self._venv_path.exists():
            python, req, system_packages, _ = self.computed()
            print(f"Create {self!r}")
            from libclipy.tools.uv import Uv
            from libclipy.core.errors import MissingTool
            try:
                uv = Uv()
            except MissingTool as e:
                import sys
                from libclipy.core.pretty import print as p
                p.pretty(e)
                sys.exit(1)
            uv.venv('-p', ','.join(python), *('--system-site-packages',)*system_packages, self._venv_path).say().call()
            if 'req' in info['venvs'][hash]:
                uv.pip('install', '--python', self._venv_path, '-r', '-').say().call(stdin='\n'.join(info['venvs'][hash]['req']))
            else:
                uv.pip('install', '--python', self._venv_path, '-r', '-').say().call(stdin='\n'.join(req))
                out = uv.pip('freeze', '--python', self._venv_path).say().call('utf8')
                info['venvs'][hash]['req'] = [o.strip() for o in out.split('\n') if o.strip()]
                info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf8')
        return self._venv_path/path
