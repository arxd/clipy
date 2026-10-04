''' <written by Claude Opus 5>

Cleanup guarantees for the sync iterator.

These drive SyncIterator through Cmd.each() with plain python children rather than through
Command/entry_point, so each test can control exactly how its child handles SIGINT -- which is
what decides whether close() succeeds or deadlocks.

The question behind the file: after `for _ in Cmd(...).each(): break`, is the child certainly
dead?  There are four routes that can finalize an abandoned generator, and they fire at very
different times:

  1. normal exhaustion     -- __next__'s `except BaseException: self.close()`
  2. refcount -> close()   -- break, or an exception in the loop body: before the next statement
  3. traceback / gc        -- generator held in a *named local*: only when that ref goes away
  4. interpreter shutdown  -- anything still alive when the process exits

Route 2 is the one that makes the common case safe, and it works because CPython cascades
GeneratorExit synchronously through intermediate generators that have no handler at all.
'''
import os, sys, gc, signal, time, contextlib, pytest
from cli import project_root
from .cmd import Cmd
from ..venv import Venv

__venv__ = Venv('libclipy.cli_testing::test')


# A child that cleans up after itself on SIGINT, the way entry_point's sync path does: the
# default handler raises KeyboardInterrupt, the finally runs, the marker lands.
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

# A child with more to say than a pipe can hold, whose SIGINT handler raises nothing -- exactly
# what entry_point.handle_signal does on the async path, where it only schedules task.cancel().
# PEP 475 then retries the interrupted write, so SIGINT alone can never free this child.
#
# Its cleanup prints before writing the marker, which pins the other half of the requirement: a
# parent that dropped the read end instead of draining would give that print an EPIPE, and the
# marker -- the rest of the cleanup -- would never be written.
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

CHILD_QUIET = '''
import sys
for i in range(3): print(f"line {i}", flush=True)
'''


def _script(tmp_path, source, name):
    ''' Children are real files so the pid in `ps` is readable when one of these tests hangs '''
    path = tmp_path/f'{name}.py'
    path.write_text(source)
    return path


def _child(tmp_path, source, name='child'):
    ''' A Cmd for one of the child scripts above, plus the marker and pid files it will write.

    Deliberately returns the *Cmd*, not cmd.each():  binding a generator to a named local is
    exactly what defers cleanup (see test_named_local_held_by_traceback_defers_cleanup), so the
    tests below that mean to exercise the prompt path must iterate it as a for-loop temp.
    '''
    marker, pidfile = tmp_path/'marker', tmp_path/'pid'
    return Cmd(sys.executable, _script(tmp_path, source, name), marker, pidfile), marker, pidfile


def _alive(pid):
    ''' Is the pid still there?  A reaped child is gone; an abandoned one answers signal 0. '''
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _wait_gone(pid, timeout=2.0):
    ''' Give a child a moment to die, so a pass does not depend on scheduling luck '''
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _alive(pid): return True
        time.sleep(0.02)
    return not _alive(pid)


@contextlib.contextmanager
def _deadline(seconds, msg):
    ''' A watchdog for calls that are supposed to return.

    Without it a blocking close() just sits there until pytest-timeout kills the run, and if the
    block happens inside a generator's finalizer the resulting exception is swallowed as
    "unraisable" -- so the test reports some unrelated later assert instead of the deadlock.
    pytest-timeout owns SIGALRM too, so its handler and remaining time are put back on the way out.
    '''
    def _fire(*_): raise AssertionError(msg)
    remaining = signal.getitimer(signal.ITIMER_REAL)[0]
    started = time.monotonic()
    old = signal.signal(signal.SIGALRM, _fire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.signal(signal.SIGALRM, old)
        signal.setitimer(signal.ITIMER_REAL, max(remaining - (time.monotonic()-started), 0.01) if remaining else 0)


def _open_fd_count():
    return len(os.listdir('/dev/fd' if os.path.isdir('/dev/fd') else '/proc/self/fd'))


# ======================================
# Route 2: break, and exceptions mid-loop
# ======================================

def test_break_cleans_up_before_the_next_statement(tmp_path):
    ''' `for _ in Cmd(...).each(): break` must leave the child dead, with no explicit close().

    The for-loop holds the generator as a temp, so breaking drops the last reference and CPython
    runs gen.close() right there.  That reaches Cmd.each()'s `except GeneratorExit` handler, which
    closes the iterator.  All of it before the assert below runs -- not at gc time, not at exit.
    '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_MARKER)
    for line in cmd.each(stdout='line', kill=signal.SIGINT):
        break
    assert(line == 'line 0\n')
    child = int(pidfile.read_text())
    assert(marker.read_text() == 'cleaned up') # The child got SIGINT and ran its own finally
    assert(not _alive(child))


def test_exception_in_loop_body_cleans_up(tmp_path):
    ''' Unwinding past the for-loop pops the generator off the value stack, so raising inside the
    body cleans up just as promptly as break -- even though a traceback for the raise survives.
    '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_MARKER)
    with pytest.raises(RuntimeError):
        for line in cmd.each(stdout='line', kill=signal.SIGINT):
            raise RuntimeError('boom')
    child = int(pidfile.read_text())
    assert(marker.read_text() == 'cleaned up')
    assert(not _alive(child))


def test_break_closes_our_fds(tmp_path):
    ''' Breaking must not leak the read end of the pipe we handed the child '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_MARKER)
    for line in cmd.each(stdout='line'): break # Warm up, so one-time allocations are not a leak
    before = _open_fd_count()
    for _ in range(3):
        for line in cmd.each(stdout='line'): break
    assert(_open_fd_count() == before)


# ==============================================
# Route 1: normal exhaustion closes out the child
# ==============================================

def test_exhaustion_closes_everything(tmp_path):
    ''' Running the iterator dry reaps the child and closes our fds '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_QUIET, 'quiet')
    assert([l.rstrip('\n') for l in cmd.each(stdout='line')] == ['line 0', 'line 1', 'line 2'])
    before = _open_fd_count()
    assert([l.rstrip('\n') for l in cmd.each(stdout='line')] == ['line 0', 'line 1', 'line 2'])
    assert(_open_fd_count() == before)


# =========================================================
# Route 3: a named local held by a traceback defers the kill
# =========================================================

def test_named_local_held_by_traceback_defers_cleanup(tmp_path):
    ''' The one real gap in the sync path.

    When the generator lives in a *named local* rather than a for-loop temp, a traceback that
    keeps that frame alive keeps the generator -- and therefore the child -- alive with it.  This
    is not hypothetical: `gen = cmd.each()` plus a failing assert means pytest holds the traceback
    for the rest of the session.

    The guarantee we actually have is the second half: cleanup is immediate once the last
    reference goes, with no gc pass needed.
    '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_MARKER)
    def consumer():
        gen = cmd.each(stdout='line', kill=signal.SIGINT) # A named local, not a loop temp
        for line in gen:
            raise RuntimeError('boom')
    saved = None
    try:
        consumer()
    except RuntimeError:
        saved = sys.exc_info()
    child = int(pidfile.read_text())
# The traceback still holds consumer's frame, which still holds `gen`
    assert(not marker.exists())
    assert(_alive(child))
# Dropping it releases the chain
    saved = None
    assert(_wait_gone(child))
    assert(marker.read_text() == 'cleaned up')


def test_reference_cycle_defers_cleanup_to_gc(tmp_path):
    ''' The same gap reached the other way: a cycle holding the generator waits for a gc pass '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_MARKER)
    gc.disable()
    try:
        gen = cmd.each(stdout='line', kill=signal.SIGINT)
        next(gen)
        cycle = [gen]
        cycle.append(cycle)
        child = int(pidfile.read_text())
        del gen, cycle
        assert(_alive(child)) # Refcounting alone cannot break the cycle
    finally:
        gc.enable()
    gc.collect()
    assert(_wait_gone(child))
    assert(marker.read_text() == 'cleaned up')


# ===============================================
# Route 4: nothing survives the parent's own exit
# ===============================================

def test_nothing_outlives_the_parent(tmp_path):
    ''' Even a generator leaked all the way to interpreter shutdown takes its child with it.

    This is why atexit is not needed on the sync path: CPython finalizes live generators during
    shutdown, and -- since 3.4 no longer blanks module globals -- iter_sync's module-level os and
    signal are still usable when it does.
    '''
    import subprocess
    marker, pidfile = tmp_path/'marker', tmp_path/'pid'
    child_py = _script(tmp_path, CHILD_MARKER, 'child')
    leaker = _script(tmp_path, f'''
import sys, gc, signal
sys.path.insert(0, {str(project_root)!r})
from libclipy.core.command.cmd import Cmd
def consumer():
    gen = Cmd(sys.executable, {str(child_py)!r}, {str(marker)!r}, {str(pidfile)!r}).each(stdout='line', kill=signal.SIGINT)
    for line in gen:
        raise RuntimeError('boom')
try:
    consumer()
except RuntimeError:
    KEEP = sys.exc_info() # A module global, so it lives until shutdown
gc.disable()              # No gc pass is going to rescue us either
''', 'leaker')
    subprocess.run([sys.executable, str(leaker)], check=True, timeout=20)
    child = int(pidfile.read_text())
    assert(_wait_gone(child)) # The leaker's shutdown finalized the generator
    assert(marker.read_text() == 'cleaned up')


# ===========================================================
# The deadlock: close() waits on a child we have not let go of
# ===========================================================

def test_close_does_not_deadlock_on_a_chatty_child(tmp_path):
    ''' Abandoning a child that is mid-write with more than a pipe-full must not wedge us.

    A child whose SIGINT handler raises nothing (which is what entry_point.handle_signal does on
    the async path, where it only schedules task.cancel()) has its interrupted write retried under
    PEP 475.  So it can only reach its own finally once somebody reads, and a close() that merely
    waits in waitpid never returns.

    Dropping the read end instead is not the answer: it frees us, but the child's cleanup print
    then takes an EPIPE and the marker below never gets written.  close() has to keep draining
    until the child is gone -- which is why the selector must outlive kill_proc().

    Closed explicitly rather than by `break` only so the failure is legible -- an exception raised
    inside a generator's finalizer is swallowed as "unraisable".  The path under test is the same
    one `break` reaches.
    '''
    cmd, marker, pidfile = _child(tmp_path, CHILD_CHATTY, 'chatty')
    gen = cmd.each(stdout='line', kill=signal.SIGINT)
    assert(next(gen) == 'ready\n')
    child = int(pidfile.read_text())
    with _deadline(2, 'close() blocked: it waits on the child while still holding the read end of its stdout'):
        gen.close()
    assert(_wait_gone(child))
    assert(marker.read_text() == 'cleaned up')


@pytest.mark.skip('policy: SIGINT only, no escalation, no timeout -- a child that ignores SIGINT hangs us forever')
def test_child_that_ignores_sigint():
    ''' kill_proc() deliberately has no SIGTERM/SIGKILL escalation and no timeout, so the child
    always gets to finish its own cleanup.  The cost is that a child which ignores SIGINT blocks
    close() forever.  Decide whether that is the policy before writing this one.
    '''
