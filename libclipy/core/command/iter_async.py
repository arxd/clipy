
import os, asyncio
from .iter_sync import SyncIterator
from .channels import Read, Write, ReadGen, _NULL
from ..errors import CmdError



class AsyncIterator(SyncIterator):

    @property
    def returncode(self):
        try:
            return self.transport.get_returncode()
        except AttributeError:
            return None


    async def __aenter__(self):
        return self.__aiter__()
    

    async def __aexit__(self, *_):
        await self.close()


    async def wait(self):
        try:
            while True: await self.__anext__()
        except (StopAsyncIteration, CmdError):
            pass

        
    def __aiter__(self):
        self.loop = asyncio.get_running_loop()
        self._q = asyncio.Queue()
    # A SubprocessProtocol to collect the exit status
        self._exited = asyncio.Event()
        class _Protocol(asyncio.SubprocessProtocol):     
            def process_exited(_): self._exited.set()
    # Run this as a task because __aiter__ is sync
        async def _create_proc():
            self.transport, protocol = await self.loop.subprocess_exec(_Protocol, *self.cmd.args, **self.popen_args)
            protocol._q = self._q
            self.proc = self.transport.get_extra_info('subprocess')
        self._create_proc_task = asyncio.create_task(_create_proc())
        return self


    async def init(self):
        await asyncio.wait([self._create_proc_task])
        self.guard_popen(self._create_proc_task.result)
        self._create_proc_task = None
    # Attach readers and writers
        self._read_gen = asyncio.Queue()
        self._n_read_gen = 0
        self._done_count = 0
        for chan in self.channels.values():
            if isinstance(chan, Read):
                self._done_count += 1
                self.loop.add_reader(chan.fd, self.guard_callback, self.ready_read, chan)
                if isinstance(chan, ReadGen): self._n_read_gen += 1
            elif isinstance(chan, Write):
                self.loop.add_writer(chan.fd, self.guard_callback, self.ready_write, chan)


    async def __anext__(self):
        # Make sure the process is running
        if self._create_proc_task is not None: await self.init()
        try:
            while (v:=await self.next_step()) is _NULL: continue
            return v
        except BaseException as e:
            await self.close()
            raise e from None


    async def next_step(self):
    # If we have recieved all of our '$' close events and the queue is empty, then we are done
        if self._q.empty() and self.done == self._done_count:
            # wait for the proess to exit and check the returncode
            await self._exited.wait()
            if self.returncode != 0:
                raise CmdError(msg="Non-zero returncode", cmd=self.cmd, returncode=self.returncode, channels=self.channels)
            raise StopAsyncIteration()
    # Wait for something in the queue
        result = await self._q.get()
        if result[0] not in ('!','$'):
            return result if self._n_read_gen > 1 else result[1]
    # Did our handler throw an exception?
        if result[0] == '!': raise result[1] from None
    # We got a close event.  We are expecting one from every Read channel
        self.done = int(self.done) + 1
        return _NULL


    def guard_callback(self, fn, chan):
        ''' the callback must not raise, so return the exception for next_step() to raise
        '''
        try:
            return fn(chan)
        except BaseException as e:
            self._q.put_nowait(('!', e))


    def ready_read(self, chan): 
        if done := not chan.read_some_data():
            self.loop.remove_reader(chan.fd)
            chan.close()
    # Parse as many values as we can if we are ReadGen
        if isinstance(chan, ReadGen):
            while (v:=chan.parse()) is not _NULL: self._q.put_nowait((chan, v))
    # Add the close code after we parsed as many values as we could
        if done: self._q.put_nowait(('$', chan))


    def ready_write(self, chan):
        raise NotImplementedError()


    async def kill_proc(self):
        import signal
    # Ask the child to stop, then wait however long it takes.  SIGINT only: no SIGTERM/SIGKILL
    # escalation and no timeout, so the child's own __exit__/finally blocks always get to run.
        if self.returncode is None:
            try:
                os.kill(self.transport.get_pid(), self.kill_signal)
            except ProcessLookupError:
                pass # Already gone, just not reaped yet
            try:
                await self._drain()
            except asyncio.CancelledError:
                # We are unwinding, but the child still gets to finish.  The cancellation has
                # been delivered by now, so this second wait suspends normally instead of
                # re-raising; a further cancel (a second ctl-C) does get through and gives up.
                await self._drain()
                raise
    # Only now that the child is gone is this safe: close() SIGKILLs a process still running.
    # It also lets asyncio's watcher be the one to reap, so the Popen never ends up collected
    # with returncode None -- which would park it in subprocess._active for the next Popen()
    # to reap, stealing the pid from that thread.
        self.transport.close()


    async def _drain(self):
        ''' Read and throw away whatever the child still has to say, until it is gone.

        Same job as SyncIterator._drain(), but it cannot borrow that one: a blocking select() loop
        would stall the whole event loop for as long as the child takes to shut down, and its
        proc.poll() would race asyncio's watcher thread for the reap.  The loop's own readers do
        the reading here instead -- swapped for a discard, so shutting down no longer depends on
        parse() and the normal read path still being healthy.  A child with more to say than the
        pipe can hold never reaches its own cleanup while nobody is reading.
        '''
        for fd in self._drain_fds():
            self.loop.remove_reader(fd)
            self.loop.add_reader(fd, self._discard, fd)
        await self._exited.wait()


    def _discard(self, fd):
        try:
            if not os.read(fd, 65536): self.loop.remove_reader(fd) # EOF: nothing more to bin
        except BlockingIOError:
            pass
        except OSError:
            self.loop.remove_reader(fd) # Closed under us; there is nothing left to drain


    async def close(self):
        await self.kill_proc()
        for chan in self.channels.values():
            if isinstance(chan, Read): self.loop.remove_reader(chan.fd)
            if isinstance(chan, Write): self.loop.remove_writer(chan.fd)
            chan.close()
