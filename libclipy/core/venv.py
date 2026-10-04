
class Venv():
    ''' This represents a desired virtual environment for a command.
    '''
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


    def hash(self):
        import hashlib
        python, req, system_packages, system = self.computed()
        fingerprint = ';'.join(sorted(python)) + ';'.join(sorted(req)) + ';'.join(sorted(system)) + f';{system_packages}'
        return hashlib.sha256(fingerprint.encode()).hexdigest()[:40]


    def __call__(self, cmd):
        ''' This venv can be used as a decorator to a `Command`
        '''
        cmd.venv.insert(0, self)
        return cmd
    

    def venv_path(self, path=''):
        try:
            return self._venv_path/path
        except AttributeError:
            import json, random
            from .config import work_root
            with open('libclipy/core/info.json', 'r', encoding='utf8') as f: info = json.load(f)
            hash = self.hash()
            if hash not in info['venvs']:
                info['venvs'][hash] = {'folder':random.randbytes(16).hex()}
            self._venv_path = work_root.path('.python') / info['venvs'][hash]['folder']
            assert(self._venv_path.is_absolute()), f"bad work_root: {work_root.v}"
            if not self._venv_path.exists():
                python, req, system_packages, system = self.computed()
                print(f"Create venv: {self._venv_path} system:{system} python:{python} system_packages?{system_packages} req:{' '.join(req)}")
                self.uv('venv', '-p', ','.join(python), *('--system-site-packages',)*system_packages, self._venv_path)
                if 'req' in info['venvs'][hash]:
                    self.uv('pip', 'install', '--python', self._venv_path, '-r', '-', stdin='\n'.join(info['venvs'][hash]['req']))
                else:
                    self.uv('pip', 'install', '--python', self._venv_path, '-r', '-', stdin='\n'.join(req))
                    out = self.uv('pip', 'freeze', '--python', self._venv_path, read=True)
                    info['venvs'][hash]['req'] = [o.strip() for o in out.split('\n') if o.strip()]
                    with open('libclipy/core/info.json', 'w', encoding='utf8') as f: json.dump(info, f, ensure_ascii=False, indent=4)
        return self._venv_path/path
    

    def uv(self, *args, read=None, stdin=None):
        # FIXME: Change to Cmd
        import subprocess
        try:
            proc = subprocess.Popen(['uv']+ list(map(str, args)), stdout=None if read is None else subprocess.PIPE, stderr=subprocess.PIPE, stdin=None if stdin is None else subprocess.PIPE )
        except OSError:
            raise ValueError("Install uv and try again: https://docs.astral.sh/uv/getting-started/installation/")
        stdout, stderr = proc.communicate(input=stdin and stdin.encode('utf8'))
        if proc.returncode != 0: raise ValueError(stderr.decode('utf-8'))
        return stdout and stdout.decode()
