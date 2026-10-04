import os, sys, subprocess, signal
from pathlib import Path
from .channels import ReadLine, Write, ReadBin, Read, Channel, ReadPickle, Mem, _NULL
from ..errors import CmdError

class Exec():
    ''' When this is returned as an output of a Command it triggers an os.exec()
    '''
    def __init__(self, **kwargs):
        for k,v in kwargs.items(): setattr(self, k, v)

    def __call__(self):
        sys.stdout.flush()
        sys.stderr.flush()
        if self.env is None: (os.execv if self.cmd.startswith(os.path.sep) else os.execvp)(self.cmd, self.args)
        (os.execve if self.cmd.startswith(os.path.sep) else os.execvpe)(self.cmd, self.args, self.env)            



class _Conditions():
    ''' handle accumulation of conditions for a call() or call_async()
    '''
    FMTS = ('', 'pass', 'null', 'utf8', 'bin', 'json')
    ACTIONS = ('', 'raise', 'code', 'value')

    def __init__(self):
        self.channels = {'stdout':'', 'stderr':''}
        self.conditions = []


    def parse(self, condition, fmt, value):
    # Verification
        code = (*fmt.split(','), '', '')[:3]
        def _assert(msg, x, xs):
            if x not in xs: raise ValueError(f"Illegal {msg} {x!r}, must be one of: {' '.join(map(repr, xs))}")
        _assert('stdout', code[0], _Conditions.FMTS)
        _assert('stderr', code[1], _Conditions.FMTS)
        _assert('action', code[2], _Conditions.ACTIONS)
    # Do we need to capture stdout/stderr?
        def _channels(key, fmt):
            if fmt not in ('','pass','null'): fmt = 'buf'
            self.channels[key] = fmt if not (k:=self.channels[key]) else k if not fmt else k if k==fmt else 'buf'
        _channels('stdout', code[0])
        _channels('stderr', code[1])
        self.conditions.append((condition, code, value))


    def return_value(self, cmd, returncode, channels):
        keep = []
        def _fmt(src, fmt):
            if not isinstance(channels[src], Read): return
            data = channels[src].data
            if fmt in ('','pass'): getattr(sys, src).buffer.write(channels[src].data)
            elif fmt == 'null': pass
            elif fmt == 'bin': keep.append(data)
            elif fmt == 'utf8': keep.append(data.decode('utf8'))
            elif fmt == 'json':
                import json
                keep.append(json.loads(data.decode('utf8')))
    # Execute the action
        def _do(stdout, stderr, action, value):
            _fmt('stdout', stdout)
            _fmt('stderr', stderr)
            if action == 'code': keep.append(returncode)
            elif action == 'value': keep.append(value)
            v = None if not keep else keep[0] if len(keep) == 1 else keep
            if action == 'raise': raise CmdError(keep=v, cmd=cmd, returncode=returncode, channels=channels, **({'msg':value} if value is not None else {}))
            return v
    # Find the first matching condition
        for condition, code, value in self.conditions:
            if isinstance(condition, int):
                if condition == returncode: return _do(*code, value)
            elif isinstance(condition, (list, tuple)):
                if returncode in condition: return _do(*code, value)
            elif condition(returncode): return _do(*code, value)



class Cmd():
    '''
    FIXME: write this docstring
    FIXME: say should record the message so that it can be attached to a CmdError
    '''

    def __init__(self, *args):
        if isinstance(args[0], (list, tuple)): args = (*args[0], *args[1:])
        elif not isinstance(args[0], (str, Path)): raise NotImplementedError() # FIXME: Pass a Command
        self.args = list(map(str, args))
        if not isinstance(self.args, list): raise ValueError(f"Only a list of args is currently supported")
        self._env = {}
        self._conditions = None


    def __repr__(self):
        return f"Cmd({', '.join(map(repr, self.args))})"


    def __call__(self, *args):
        ''' Clone this Cmd and add additional arguments.
        '''
        cmd = Cmd(*self.args, *args)
        cmd._env = self._env.copy()
        return cmd
    

    def say(self, msg=''):
        import shlex
        if self._env:
            env = 'env -i ' if '!' in self._env else 'env '
            env += ' '.join(f'{k}={shlex.quote(v)}' for k,v in self._env.items() if k!='!') + ' '
        else:
            env = ''
        if msg: print(msg)
        print(f'  $ {env}{shlex.join(self.args)}')
        return self


    def env(self, **kwargs):
        for k,v in kwargs.items(): self._env[k] = str(v)
        return self


    def env_set(self, **kwargs):
        self._env['!'] = True
        return self.env(**kwargs)


    def env_clear(self, **kwargs):
        self._env = {}
        return self.env(**kwargs)


    @property
    def environ(self):
        if '!' in self._env:
            e = self._env.copy()
            del e['!']
        elif self._env:
            e = os.environ.copy()
            e.update(self._env)
        else: return None
        return e


    def exec(self, **data):
        return Exec(cmd=self.args[0], args=self.args, env=self.environ)


    def _channels(self, stdout=None, stderr=None, stdin=None, **channels):
        ''' ``None`` | '' | pass | line | bin | buf | null | stdout
        '''
        def _build(src, kind):
            if isinstance(kind, Channel): return kind
            kinds = {None:None, 'pass':None, '':None, 'stdout':subprocess.STDOUT, 'null':subprocess.DEVNULL}
            chan = Channel(src=src, child_fd=kinds.get(kind, subprocess.PIPE))
            if src == 'stdin' and kind is not None:
                chan = Write(src=src)
                chan.child_fd, chan.fd = os.pipe()
                if isinstance(kind, (str, bytes)):
                    chan.send(kind)
                    chan.send(None)
            if src != 'stdin' and chan.child_fd is subprocess.PIPE:
                p = os.pipe()
                chan = {'line':ReadLine, 'bin':ReadBin, 'pickle':ReadPickle, 'buf':Read}[kind](src=src, fd=p[0], child_fd=p[1])
            return chan
        return {
            'stdout': _build('stdout', stdout),
            'stderr': _build('stderr', stderr),
            'stdin': _build('stdin', stdin),
            **channels
        }


    def _get_conditions(self, fmt, value):
    # If there has not been any call to `on()` then the final condition is for a zero return code that, by default, does nothing.  It raises on any other returncode
        if not (c:=self._conditions):
            c = _Conditions()
            c.parse(0, fmt or '', value)
            fmt = None
        c.parse(lambda _:True, ',,raise' if fmt is None else fmt, 'Non-zero returncode' if fmt is None else value)
        # Reset conditions so that the Cmd object can be used for another call
        self._conditions = None
        return c
    

    def on(self, condition, fmt='', value=None):
        ''' If the given condition matches the return value then the `fmt` rule will be applied.  See: call()
        '''
        if self._conditions is None: self._conditions = _Conditions()
        self._conditions.parse(condition, fmt, value)
        return self
    

    def call(self, fmt=None, value=None, *, stdin=None, kill=signal.SIGTERM):
        ''' This executes the command and supplies default case if none of the other cases match.

        Parameters:
            fmt :str = "stdout,stdin,action"
                Where stdout/stdin tells you what to do with those streams:

                * ''   : We don't care what happens (defer to a different on())
                * pass : Send the stream to stdout (or stderr)
                * null : Supress it with ``subprocess.DEVNULL``
                * json : Keep it and parse it as json
                * bin  : Keep it as binary
                * utf8 : Keep it as utf8 text

                The action tells you what to return in addition to what you kept from stdin/stdout.

                * ''      : Return only what was kept from stdout, stderr
                * 'raise' : Raise a `CmdError` with you kept, the returncode, and the `value` you supplied as the msg.
                * 'code'  : Return the returncode
                * 'value' : Return the `value` you supplied

                The resulting return value of the call will be a tuple of all of the values ``(stdout, stderr, action)`` that you kept.
                If there is only a single value to return then it is returned by itself without the tuple.
                If there are no values to return then ``None`` is returned.

            value
                If `fmt`'s action is 'value' then this value is returned.
                If the action is 'raise' then this value is the text of the `CmdError` object.

            stdin
                What data do you want to send to stdin?  It can be a string, bytes, or ``None``.

            kill
                What signal will be used to kill the child (if killing is required).
        '''
        from .iter_sync import SyncIterator
        c = self._get_conditions(fmt, value)
        with SyncIterator(cmd=self, kill=kill, channels=self._channels(stdin=stdin, **c.channels)) as iter:
            iter.wait()
        return c.return_value(self, iter.returncode, iter.channels)


    async def call_async(self, fmt=None, value=None, *, stdin=None, kill=signal.SIGTERM):
        ''' async version of `call()`
        '''
        from .iter_async import AsyncIterator
        c = self._get_conditions(fmt, value)
        async with AsyncIterator(cmd=self, kill=kill, channels=self._channels(stdin=stdin, **c.channels)) as iter:
            await iter.wait()
        return c.return_value(self, iter.returncode, iter.channels)


    def each(self, kill=signal.SIGTERM, **channels):
        from .iter_sync import SyncIterator
        iter = SyncIterator(cmd=self, kill=kill, channels=self._channels(**channels))
        try:
            for item in iter: yield item
        except GeneratorExit:
            iter.close()


    async def each_async(self, kill=signal.SIGTERM, **channels):
        from .iter_async import AsyncIterator
        iter = AsyncIterator(cmd=self, kill=kill, channels=self._channels(**channels))
        try:
            async for item in iter: yield item
        except GeneratorExit:
            await iter.close()


    # FIXME Move this to a better location
    @classmethod
    def entry_point(self, venv_path, *, pipe=False, **cmd_info):
        from libclipy.core.config import ConfigVar, out_fd
        from .channels import ReadPickle
        from cli import project_root
        if pipe:
            p = os.pipe()
            cmd = ReadPickle(src='cmd', fd=p[0], child_fd=p[1])
            out_fd.for_child(cmd.child_fd)
        mm = Mem(src='mm', data=({var.path:(var.v_child if hasattr(var, 'v_child') else var.v) for var in ConfigVar._set}, cmd_info))
        each_args = {} if not pipe else dict(cmd=cmd, mm=mm)
        return Cmd(venv_path, '-I', 'libclipy/core/entry_point.py', mm.size, mm.child_fd, project_root), each_args
