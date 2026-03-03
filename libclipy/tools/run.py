

def _run_init(cmd, msg, env):
    if not isinstance(cmd, str): cmd = list(map(str, cmd))
    if msg == True: msg = Text('Running...')
    if msg:
        print.ln(msg, ['']*2, '   $ ', cmd if isinstance(cmd, str) else shlex.join(cmd))
        print.stream.flush()
    if env:
        e = dict(os.environ)
        e.update(env)
        env = e
    return cmd, env
    

def exec(cmd, msg=True, env=None):
    cmd, env = _run_init(cmd, msg, env)
    assert(isinstance(cmd, list)), f"Can't exec with a shell string"
    if env: os.execvpe(cmd[0], cmd, env)
    os.execvp(cmd[0], cmd)


def run(cmd, msg=True, env=None, stdin=None, **kwargs):
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

    The command produces three things: stdout, stderr, returncode.
    
    How should we handle stdout and stderr?

    ''     : Show it on the console
    'null' : Hide it
    'json' : Parse it as json
    'bin'  : Keep it as binary
    'utf8' : Keep it as utf8 text
    
    What should be returned?

    '' : Nothing special, whatever we captured in stdout and stderr
    'raise msg text' : Raise a RunException(msg="msg text", stdout, stderr, returncode)
    'code' : Returncode
    '''
    cmd, env = _run_init(cmd, msg, env)
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
        resp = subprocess.Popen(cmd, shell=isinstance(cmd,str), stdout=_mode(0), stderr=_mode(1), stdin=subprocess.PIPE if stdin else None, env=env)
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




class PrettyException(Exception):
    ''' This implements the pretty() method to show a pretty version of the exception.
    
    __str__ and __repr__ return normal, not-pretty, strings.
    '''
    def __init__(self, **kwargs):
        for k,v in kwargs.items(): setattr(self, k, v)


    def __str__(self):
        #print = Printer.using(StringIO)(ascii=True, color=False)
        if hasattr(self, 'msg'):
            return self.msg
            #print(self.msg)
        else:
            return repr(self)
            #print(repr(self))
        #return str(print).rstrip()


    def __repr__(self):
        s = f"{self.__class__.__name__}("
        args = [f'{k}={v!r}' for k,v in self.__dict__.items()]
        return s+ ', '.join(args) + ')'




class UsageError(PrettyException):
    def __init__(self, *msg, **kwargs):
        super().__init__(msg=msg)
        for k,v in kwargs.items(): setattr(self, k,v)



class RunException(PrettyException):
    pass


import json, sys, shlex, os, subprocess
from libclipy.print import print, Text, CLR, Pretty, Table
