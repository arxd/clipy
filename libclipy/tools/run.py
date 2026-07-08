import json, sys, shlex, os, subprocess
from ..core.errors import PrettyException


def _show_msg(msg, cmd, env):
    if msg == True: msg = 'Running...'
    if not msg: return
    
    if env is not None:
        env = dict(env)
        if not (set(os.environ) - env.keys()):
            for k,v in os.environ.items():
                if env[k] == v: env.pop(k)
    env = ' '.join(f'{k}="{v}"' for k,v in (env or {}).items())
    print(msg, '\n  $',env, cmd if isinstance(cmd, str) else shlex.join(cmd))



class Exec():
    def __init__(self, **kwargs):
        kw = dict(env=None, msg=True, venv=None)
        kw.update(kwargs)
        for k,v in kw.items(): setattr(self, k, v)

    def __call__(self):
        if not self.venv:
            _show_msg(self.msg, [self.cmd, *self.args[1:]], self.env)
        sys.stdout.flush()
        sys.stderr.flush()
        if self.venv: self.venv.exec(self.data)
        if self.env is None: (os.execv if self.cmd.startswith(os.path.sep) else os.execvp)(self.cmd, self.args)
        (os.execve if self.cmd.startswith(os.path.sep) else os.execvpe)(self.cmd, self.args, self.env)            
            


class RunException(PrettyException):
    def __init__(self, **kwargs):
        for k,v in kwargs.items(): setattr(self, k, v)



def run(cmd, *, msg=True, env=None, stdin=None, **kwargs):
    '''
    What to print to the terminal before running the command?

        msg == True
            Running...
            $ cmd
        msg == 'Hello"
            Hello
            $ cmd
        msg == None or msg == False
            <nothing>

    In order to decide what to return the special keyword arguments 'if_{code}' and 'or_else' are consulted.
    The returncode is used choose the correct keyword argument and its value is used to control the output.
    The values are a 3-tuple in string form '{stdout},{stderr},{action}'.

    The first two elements (stdout and stderr) are one of the following values that decide how stdout and stderr should be formatted.

    ''     : Show it on the console
    'null' : Hide it
    'json' : Keep it and parse it as json
    'bin'  : Keep it as binary
    'utf8' : Keep it as utf8 text
    
    The last element (action) is what gets returned (or thrown).

    '' : return stdout or stderr depending on which one was kept.  If they were both kept then a tuple (stdout,stderr) is returned.  If neither was kept then return None.
    'code' : return the integer returncode
    'raise msg text' : Raise a RunException(msg="msg text", stdout, stderr, returncode)

    '''
    if not isinstance(cmd, str): cmd = list(map(str, cmd))
    _show_msg(msg, cmd, env)
    
    if not kwargs: kwargs = {'if_0':',,'}
    # Figure out if we need to capture stdout
    def _mode(i):
        mode = 0
        for k, v in kwargs.items():
            if not (k == 'or_else' or k.startswith('if_')): raise ValueError(f"Invalid run parameter {k}={v!r}")
            code = v.split(',')[i]
            want = subprocess.DEVNULL if code == 'null' else None if code == '' else subprocess.PIPE
            mode = want if mode == 0 or mode == want else subprocess.PIPE
        return mode
    try:
        cmd_kwargs = dict(stdout=_mode(0), stderr=_mode(1), stdin=subprocess.PIPE if stdin else None)
        if env is not None: cmd_kwargs['env'] = env
        resp = subprocess.Popen(cmd, shell=isinstance(cmd,str), **cmd_kwargs)
        if stdin and not isinstance(stdin, bytes): stdin = stdin.encode('utf8')
        outs = resp.communicate(input=stdin)
        code = resp.returncode
    except Exception as e:
        err = (str(e) + '\n').encode('utf8')
        code = 1001 if isinstance(e, FileNotFoundError) else 1000
        if _mode(1) == None: os.write(sys.stderr.fileno(), err)
        outs = (b'' if _mode(0) == subprocess.PIPE else None, err if _mode(1) == subprocess.PIPE else None)
    # Figure out the codes that match our returncode
    ret = []
    codes = kwargs.get(f'if_{code}', kwargs.get('or_else', ',,raise')).split(',')
    for i,c in enumerate(codes[:2]):
        if c == '':
            if outs[i] != None: os.write((sys.stderr if i else sys.stdout).fileno(), outs[i])
        elif c == 'json':
            ret.append(json.loads(outs[i].decode('utf8')))
        elif c == 'bin':
            ret.append(outs[i])
        elif c == 'utf8':
            ret.append(outs[i].decode('utf8'))
    if codes[2].startswith('raise'):
        raise RunException(msg=codes[2][5:].lstrip(), code=code, value=None if len(ret)==0 else ret[0] if len(ret)==1 else tuple(ret))
    if codes[2] == 'code':
        ret.append(code)
    return None if len(ret)==0 else ret[0] if len(ret)==1 else tuple(ret)
