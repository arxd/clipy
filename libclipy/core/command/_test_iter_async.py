''' <written by Claude Opus 5>

Cleanup guarantees for the async iterator.

The async counterpart of _test_iter_sync.py, and a harder problem.  A sync generator can be
finalized by refcount the moment it is abandoned, so `for _ in each(): break` kills the child
before the next statement.  An async generator cannot: aclose() is a coroutine, so CPython hands
it to the asyncgen finalizer hook, which schedules it as a *task*.  Nothing can run it without a
live event loop.

That gives four routes, and only the first two are prompt:

  1. normal exhaustion       -- __anext__'s `except BaseException: await self.close()`
  2. `await agen.aclose()`   -- but only if every layer links to the next one
  3. abandoned, loop alive   -- the finalizer task runs at the next opportunity
  4. loop shutdown           -- loop.shutdown_asyncgens() closes whatever is still live

and route 4 is the last one there is: once the loop is gone an async generator can never be
finalized, so anything still holding a child at that point needs a *synchronous* backstop.

The hard requirement, which these tests exist to pin down:

    async for _ in Cmd('my_cmd').each_async(): break

must never leave my_cmd running after the calling process exits.  Still running immediately after
the break is fine -- routes 3 and 4 are asynchronous by construction.
'''
import os, sys, time, signal, asyncio, subprocess, pytest
from cli import project_root
from .cmd import Cmd


CHILD_MARKER = '''
import sys, os, time, pathlib
marker, pidfile = sys.argv[1], sys.argv[2]
pathlib.Path(pidfile).write_text(str(os.getpid()))
try:
    for i in range(300):
        print(f"line {i}", flush=True)
        time.sleep(0.2)
finally:
    pathlib.Path(marker).write_text('cleaned up')
'''

CHILD_QUIET = '''
import sys
for i in range(3): print(f"line {i}", flush=True)
'''

# Says one thing and then goes quiet for a long time.  Nothing to leak-test with CHILD_MARKER:
# that one prints every 0.2s, so when its parent dies it takes an EPIPE on the next print and
# cleans itself up -- which would let "nothing outlives the parent" pass without the parent ever
# having done anything.  This child can only be stopped by actually being signalled.
CHILD_SILENT = '''
import sys, os, time, pathlib
marker, pidfile = sys.argv[1], sys.argv[2]
pathlib.Path(pidfile).write_text(str(os.getpid()))
try:
    print("line 0", flush=True)
    time.sleep(30)
finally:
    pathlib.Path(marker).write_text('cleaned up')
'''

CHILD_PACED = '''
import sys, time
for i in range(3):
    time.sleep(0.1)
    print(f"line {i}", flush=True)
'''

# One line far wider than a pipe buffer, so its value is reassembled from many reads
CHILD_BIG = '''
import sys
print("x" * 100_000, flush=True)
'''

CHILD_FAILS = '''
import sys
print("line 0", flush=True)
sys.exit(3)
'''

# More to say than a pipe can hold, with a SIGINT handler that raises nothing -- exactly what
# entry_point.handle_signal does on the async path, where it only schedules task.cancel().  PEP 475
# then retries the interrupted write, so SIGINT alone can never free this child.
#
# Its cleanup prints before writing the marker, which pins the other half: a parent that dropped
# the read end instead of draining would give that print an EPIPE and the marker would never land.
CHILD_CHATTY = '''
import sys, os, signal, pathlib
marker, pidfile = sys.argv[1], sys.argv[2]
pathlib.Path(pidfile).write_text(str(os.getpid()))
signal.signal(signal.SIGINT, lambda *a: None)
try:
    print("ready", flush=True)
    sys.stdout.write("x" * 10_000_000)
    sys.stdout.flush()
finally:
    print("cleaning up", flush=True)
    pathlib.Path(marker).write_text('cleaned up')
'''


def _script(tmp_path, source, name):
    ''' Children are real files so the pid in `ps` is readable when one of these tests hangs '''
    path = tmp_path/f'{name}.py'
    path.write_text(source)
    return path


def _child(tmp_path, source, name='child'):
    ''' A Cmd for one of the child scripts above, plus the marker and pid files it will write '''
    marker, pidfile = tmp_path/'marker', tmp_path/'pid'
    return Cmd(sys.executable, _script(tmp_path, source, name), marker, pidfile), marker, pidfile


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


async def _wait_gone(pid, timeout=3.0):
    ''' Routes 3 and 4 are asynchronous, so a child is allowed a moment to die '''
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _alive(pid): return True
        await asyncio.sleep(0.02)
    return not _alive(pid)


def _wait_gone_sync(pid, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _alive(pid): return True
        time.sleep(0.02)
    return not _alive(pid)


async def _finishes(coro, timeout=3.0, msg='call did not return'):
    ''' Run a coroutine that is supposed to return, and fail the test cleanly if it blocks.

    asyncio.wait() rather than wait_for(), because wait_for cancels on timeout and kill_proc()
    deliberately keeps waiting through a CancelledError -- so a cancel would hang us too.
    '''
    task = asyncio.ensure_future(coro)
    done, _ = await asyncio.wait([task], timeout=timeout)
    assert(task in done), msg
    return task.result()


def _open_fd_count():
    return len(os.listdir('/dev/fd' if os.path.isdir('/dev/fd') else '/proc/self/fd'))


# ===================
# Iteration behaviour
# ===================

@pytest.mark.asyncio
async def test_each_async_agrees_with_each(tmp_path):
    ''' The async path yields the same values in the same order as the sync path '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_QUIET, 'quiet')
    assert([l async for l in cmd.each_async(stdout='line')] == list(cmd.each(stdout='line')))


@pytest.mark.asyncio
async def test_values_arrive_incrementally(tmp_path):
    ''' The point of each_async(): values arrive as produced, not batched at child exit.
    This is what fails if the child's output is left buffered without a flush.
    '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_PACED, 'paced')
    arrivals = []
    async for line in cmd.each_async(stdout='line'):
        arrivals.append(time.monotonic())
    assert(len(arrivals) == 3)
    assert(arrivals[-1] - arrivals[0] > 0.1) # Batched delivery would make this ~0


@pytest.mark.asyncio
async def test_a_value_wider_than_the_pipe_is_reassembled(tmp_path):
    ''' A record larger than the pipe buffer arrives over many reads and is put back together '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_BIG, 'big')
    assert([l async for l in cmd.each_async(stdout='line')] == ['x'*100_000 + '\n'])


@pytest.mark.asyncio
async def test_exhaustion_closes_everything(tmp_path):
    ''' Running the iterator dry reaps the child and closes our fds '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_QUIET, 'quiet')
    assert([l.rstrip('\n') async for l in cmd.each_async(stdout='line')] == ['line 0','line 1','line 2'])
    before = _open_fd_count()
    assert([l.rstrip('\n') async for l in cmd.each_async(stdout='line')] == ['line 0','line 1','line 2'])
    assert(_open_fd_count() == before)


@pytest.mark.asyncio
async def test_break_closes_our_fds(tmp_path):
    ''' Abandoning the iterator must not leak the read end of the pipe we handed the child '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_MARKER)
    agen = cmd.each_async(stdout='line')
    async for line in agen: break
    await agen.aclose()
    before = _open_fd_count()
    for _ in range(3):
        agen = cmd.each_async(stdout='line')
        async for line in agen: break
        await agen.aclose()
    assert(_open_fd_count() == before)


# ========================
# Route 2: explicit aclose
# ========================

@pytest.mark.asyncio
async def test_break_then_aclose_cleans_up_immediately(tmp_path):
    ''' aclose() is the one prompt handle a caller has.  By the time it returns the child must be
    gone and its own finally must have run -- which needs every generator layer between us and the
    AsyncIterator to pass the close along rather than just being abandoned.
    '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_MARKER)
    agen = cmd.each_async(stdout='line', kill=signal.SIGINT)
    async for line in agen:
        assert(line == 'line 0\n')
        break
    child = int(pidfile.read_text())
    await _finishes(agen.aclose(), msg='aclose() did not return')
    assert(not _alive(child))
    assert(marker.read_text() == 'cleaned up') # SIGINT, not SIGKILL: the child cleaned up


@pytest.mark.asyncio
async def test_aclose_does_not_deadlock_on_a_chatty_child(tmp_path):
    ''' The child is blocked writing more than the pipe can hold and its SIGINT handler raises
    nothing, so it only reaches its finally once somebody reads.  Dropping the read end instead
    would free us but give its cleanup print an EPIPE, and the marker would never be written.
    '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_CHATTY, 'chatty')
    agen = cmd.each_async(stdout='line', kill=signal.SIGINT)
    async for line in agen:
        assert(line == 'ready\n')
        break
    child = int(pidfile.read_text())
    await _finishes(agen.aclose(), msg='aclose() blocked on a child that still has a pipe-full to write')
    assert(not _alive(child))
    assert(marker.read_text() == 'cleaned up')


# =========================================
# Route 3: abandoned, with the loop running
# =========================================

@pytest.mark.asyncio
async def test_break_without_aclose_cleans_up_once_the_loop_runs_on(tmp_path):
    ''' No aclose() at all.  CPython schedules the generator's finalizer as a task, so the child
    is allowed to still be alive the instant after the break -- but it must not stay that way
    while the loop keeps running.
    '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_MARKER)
    async for line in cmd.each_async(stdout='line', kill=signal.SIGINT):
        break
    child = int(pidfile.read_text())
    assert(await _wait_gone(child))
    assert(marker.read_text() == 'cleaned up')


# ==========================================================
# Route 4: the hard requirement -- nothing outlives the parent
# ==========================================================

@pytest.fixture
def reaper():
    ''' SIGKILLs anything a failing leak test left behind, so one failure does not strand a child
    for the rest of the run.
    '''
    pids = []
    yield pids
    for pid in pids:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass


def _leak_and_exit(tmp_path, reaper, runner, name):
    ''' Run a whole python that abandons an each_async() mid-iteration and then exits.

    Returns the child's pid once the parent is gone, so the caller can check it went with it.
    Its stdio goes to files rather than pipes on purpose: a leaked child inherits the parent's
    stdout, so capture_output=True would block in communicate() until that child exits -- turning
    "the child outlived its parent" into a test that hangs instead of one that says so.
    '''
    marker, pidfile = tmp_path/'marker', tmp_path/'pid'
    child_py = _script(tmp_path, CHILD_SILENT, 'child')
    leaker = _script(tmp_path, f'''
import sys, asyncio, signal
sys.path.insert(0, {str(project_root)!r})
from libclipy.core.command.cmd import Cmd

async def main():
    async for line in Cmd(sys.executable, {str(child_py)!r}, {str(marker)!r}, {str(pidfile)!r}).each_async(stdout='line', kill=signal.SIGINT):
        break # Abandoned: no aclose(), no close of any kind
{runner}
''', name)
    err = tmp_path/f'{name}.err'
    with open(tmp_path/f'{name}.out','w') as out, open(err,'w') as e:
        r = subprocess.run([sys.executable, str(leaker)], stdout=out, stderr=e, timeout=30)
    assert(r.returncode == 0), f"the leaker itself failed:\n{err.read_text()}"
    child = int(pidfile.read_text())
    reaper.append(child)
    return child, marker


@pytest.mark.xfail(reason='We will always be running with entry_point.py::run_coro() so this runner is not supported')
def test_nothing_outlives_the_parent(tmp_path, reaper):
    '''
    asyncio.run() calls shutdown_asyncgens(), so this ought to be the safe case -- but it runs
    _cancel_all_tasks() first.  Abandoning the generator made CPython's finalizer hook discard it
    from loop._asyncgens and schedule aclose() as a task; that task is cancelled before its first
    step, so kill_proc() never runs and no SIGINT is ever sent, and shutdown_asyncgens() then finds
    an empty set.  Nothing is left that could clean up.
    '''
    child, marker = _leak_and_exit(tmp_path, reaper, 'asyncio.run(main())', 'leaker_run')
    assert(_wait_gone_sync(child))
    assert(marker.read_text() == 'cleaned up')


def test_nothing_outlives_the_parent_when_the_loop_runs_on(tmp_path, reaper):
    ''' The case that already works, kept to show what the difference is.

    No _cancel_all_tasks(), so the loop gets to run once more and the pending aclose() task takes
    its step.  It is the extra turn of the loop that saves the child here, not shutdown_asyncgens()
    finding anything -- the hook already removed the generator from the set.
    '''
    child, marker = _leak_and_exit(tmp_path, reaper, '''
loop = asyncio.new_event_loop()
loop.run_until_complete(main())
loop.run_until_complete(loop.shutdown_asyncgens())
loop.close()
''', 'leaker_shutdown')
    assert(_wait_gone_sync(child))
    assert(marker.read_text() == 'cleaned up')


@pytest.mark.xfail(reason='We will always be running with entry_point.py::run_coro() so this runner is not supported')
def test_nothing_outlives_the_parent_with_a_bare_loop(tmp_path, reaper):
    ''' The same requirement with every async route taken away.

    A caller that closes its own loop without running it again leaves the generator unfinalizable:
    there is no loop left to run aclose() on, and an async generator cannot be finalized without
    one.  Only a synchronous backstop -- atexit, or __del__ on the iterator -- can keep the promise
    here.
    '''
    child, marker = _leak_and_exit(tmp_path, reaper, '''
loop = asyncio.new_event_loop()
loop.run_until_complete(main())
loop.close() # No further turn of the loop: the pending aclose() task can never run
''', 'leaker_bare')
    assert(_wait_gone_sync(child))


# ==========================
# Divergence from the sync path
# ==========================

@pytest.mark.asyncio
async def test_a_failing_child_is_reported(tmp_path):
    ''' each() raises CmdError when the child exits non-zero (iter_sync.next_step).  each_async()
    never looks at the return code, so the same failure passes silently.
    '''
    from ..errors import CmdError
    cmd, marker, pidfile = _child(tmp_path, CHILD_FAILS, 'fails')
    with pytest.raises(CmdError):
        list(cmd.each(stdout='line', kill=signal.SIGINT))
    with pytest.raises(CmdError):
        [l async for l in cmd.each_async(stdout='line', kill=signal.SIGINT)]
