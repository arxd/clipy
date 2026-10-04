import os, subprocess, selectors
from .channels import Read, Write, ReadGen, _NULL
from ..errors import CmdError



class SyncIterator():
    def __init__(self, *, cmd, channels, kill):
        self.cmd = cmd
        self.kill_signal = kill
        self.channels = channels
        self.done = False
        self.popen_args = {'env': cmd.environ, 'pass_fds': []}
        for chan in channels.values():
            if chan.src in ('stdin', 'stdout', 'stderr'):
                self.popen_args[chan.src] = chan.child_fd
            else:
                self.popen_args['pass_fds'].append(chan.child_fd)


    def __enter__(self):
        return iter(self)


    def __exit__(self, *_):
        self.close()


    def wait(self):
        try:
            while True: next(self)
        except (StopIteration, CmdError):
            pass


    def __iter__(self):
        self.proc = self.guard_popen(subprocess.Popen, self.cmd.args, **self.popen_args)
        self.sel = selectors.DefaultSelector()
    # Register necessary the channels
        for chan in self.channels.values():
            if not (mask := selectors.EVENT_WRITE*isinstance(chan, Write) | selectors.EVENT_READ*isinstance(chan, Read)): continue
            os.set_blocking(chan.fd, False)
            self.sel.register(chan.fd, mask, chan)
    # Find channels returning data
        self._read_gen = [c for c in self.channels.values() if isinstance(c, ReadGen)]
        self._events = None
        return self


    @property
    def returncode(self):
        try:
            return self.proc.returncode
        except AttributeError:
            return None
    

    def send(self, data=None, src='stdin'):
        self.channels[src].send(data)
    

    def guard_popen(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except BaseException as e:
            for chan in self.channels.values(): chan.close()
            raise e from None
        finally:
            # We have sent these to the child, so close them on our side
            for chan in self.channels.values(): chan.close_child()

    
    def __next__(self):
        try:
            while (v:=self.next_step()) is _NULL: continue
            return v
        except BaseException:
            self.close()
            raise

    
    def next_step(self):
    # Can we yield something from the data we have?
        for chan in self._read_gen:
            if (v:=chan.parse()) is _NULL: continue
            return (chan, v) if len(self._read_gen)>1 else v
    # Are we done?
        if self.done:
            self.proc.wait()
            if self.proc.returncode != 0:
                raise CmdError(msg="Non-zero returncode", cmd=self.cmd, returncode=self.proc.returncode, channels=self.channels)
            raise StopIteration()
    # Make sure we have an iterator for the selector events
        if self._events is None:
            if not self.sel.get_map(): # No more events. Just keep parsing our data.
                self.done = True 
                return _NULL
            self._events = iter(self.sel.select())
    # Read the next event
        try:
            e = next(self._events)
            mask, chan = e[1], e[0].data
        except StopIteration:
            self._events = None
            return _NULL
    # Can we write anything?
        if mask & selectors.EVENT_WRITE:
            raise NotImplementedError() # Need to register / unregister as writable data is available or not        
    # Can we read data?
        if mask & selectors.EVENT_READ:
            if not chan.read_some_data():
                self.sel.unregister(chan.fd)
                chan.close()
        return _NULL


    def close(self):
        self.sel.close() # Done iterating, so drop the selector and every registration with it
        self.kill_proc()
        for chan in self.channels.values(): chan.close()


    def kill_proc(self):
        if self.proc.returncode is not None: return
        try:
            os.kill(self.proc.pid, self.kill_signal) # Let the subprocess clean-up
        except ProcessLookupError: pass # FIXME Find an actual test case where this is needed
        self._drain()
        try:
            self.proc.wait()
        except ChildProcessError: pass # FIXME Find an actual test case where this is needed


    def _drain_fds(self):
    # The read ends still worth draining: whatever the child could still be blocked writing to.
    # Channels that already hit EOF are done and their fd is closed, so they are not in the list.
        return [c.fd for c in self.channels.values() if isinstance(c, Read) and not c.done and c.fd is not None]


    def _drain(self):
    # Consume the child's output while it shuts-down to prevent a deadlock
        if not (fds := self._drain_fds()): return
        with selectors.DefaultSelector() as sel:
            for fd in fds: sel.register(fd, selectors.EVENT_READ)
            while self.proc.poll() is None:
                for key, _ in sel.select(0.05):
                    try:
                        if not os.read(key.fd, 65536): sel.unregister(key.fd)
                    except BlockingIOError:
                        pass
                if not sel.get_map(): return # Every pipe is at EOF; nothing left that could block it
