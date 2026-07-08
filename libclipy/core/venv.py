import subprocess, hashlib, sys, os, pickle

class Venv():
    ''' This represents a desired virtual environment for a command.
    '''
    def __init__(self, python=None, requirements=None, system_packages=None, system=None, base=None):
        ''' Define a virtual environment.

        All parameters can be strings using space-separation, or lists.

        Parameters:
            python | default None
                The required python version. e.g. '3.10' or '>=3.10 <3.13'
                If `None` then the current executing python is used.

            requirements | default None
                Packages that need to be installed in this virtual environment.

            system_packages
                Allow system packages to be visible from the virtual environment.
            
            system
                The external system environment (or a list of environments) that this virtual environment is valid for.
        '''
        _to_list = lambda v: [x.strip() for x in v.split(' ') if x.strip()] if isinstance(v, str) else list(v)
    # A blank venv should just use the venv of its parent
        self.use_parent = (python, requirements, system_packages, system) == (None,)*4
        self.python = _to_list(python or "%d.%d.%d"%sys.version_info[:3])
        if not self.use_parent:
            self.system = sorted(_to_list(system or []))
            self.requirements = sorted(_to_list(requirements or []))
            self.b_requirements = '\n'.join(self.requirements).encode('utf-8')
            self.system_packages = system_packages
        if base is None:
            from cli import env
            base = env.venv
        self.venv_base = base


    def __str__(self):
        args = [k + '=' + str(getattr(self,k)) for k in ['python'] + ['system_packages','system','requirements']*(not self.use_parent)]
        return 'Venv(' + ', '.join(args) + ')'


    def hash(self):
        if self.use_parent: return sys.executable.rsplit(os.path.sep, 3)[1]
        fingerprint = '\\'.join(map(str, [self.system, self.python, bool(self.system_packages)])).encode('utf-8')
        return hashlib.sha256(fingerprint + self.b_requirements).hexdigest()[:40]


    def __call__(self, cmd):
        ''' This venv can be used as a decorator to a `Command`
        '''
        cmd.venv.append(self)
        return cmd
    

    def venv_path(self, suffix=''):
        try:
            return os.path.join(self._venv_path, suffix)
        except AttributeError:
            self._venv_path = os.path.join(self.venv_base, self.hash())
            if not os.path.exists(self._venv_path):
                print('Create venv', self.hash(), 'for', self)
                self.uv('venv', '-p', ','.join(self.python), *(['--system-site-packages'] if self.system_packages else []), self._venv_path)
                if self.b_requirements:
                    self.uv('pip', 'install', '--python', self._venv_path, '-r', '-', stdin=self.b_requirements)
        return os.path.join(self._venv_path, suffix)
    

    def freeze(self):
        out = self.uv('pip', 'freeze', '--python', self.venv_path(), read=True)
        return [o.strip().decode() for o in out.split('\n') if o.strip()]


    def uv(self, *args, read=None, stdin=None):
        try:
            proc = subprocess.Popen(['uv']+ list(map(str, args)), stdout=None if read is None else subprocess.PIPE, stderr=subprocess.PIPE, stdin=None if stdin is None else subprocess.PIPE )
        except OSError:
            raise ValueError("Install uv and try again: https://docs.astral.sh/uv/getting-started/installation/")
        stdout, stderr = proc.communicate(input=stdin)
        if proc.returncode != 0: raise ValueError(stderr.decode('utf-8'))
        return stdout and stdout.decode()
    

    def exec(self, data):
        read_fd = ''
        if isinstance(data, dict):
            read_fd, write_fd = os.pipe()
            os.set_inheritable(read_fd, True)
            os.write(write_fd, pickle.dumps(data, protocol=5))
            os.close(write_fd)
            data = []
        os.execv(self.venv_path('bin/python'), ['python', '-I', 'libclipy/core/entry_point.py', str(read_fd)]+data)
