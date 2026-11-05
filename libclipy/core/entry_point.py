# python is executed with -I, so we need to manually add the project root to the path
import sys, os, signal, time, logging
sys.path.insert(0, sys.argv[3])

# Set logging class early so top-level getLogger() calls during imports use our logger
from libclipy.core.logger import ClipyLogger, ClipyLogFilter
logging.setLoggerClass(ClipyLogger)


# Handle ctl-c SIGINT
task = None
loop = None
def handle_signal(signal, _):
    global task
    if isinstance(task, float):
        dt = time.time() - task
        if dt > 2: os._exit(128+signal)
    else:
        cancel, task = task and task.cancel, time.time()
        if cancel:
            loop.call_soon_threadsafe(cancel)
        else:
            raise KeyboardInterrupt()
signal.signal(signal.SIGINT, handle_signal)


def _send_child_results(v):
    if v is None: v = {}
    if not isinstance(v, dict): raise ValueError(f"Implicit generator '{cmd}' must yield None or a dict, not {v!r}")
    for x in cmd.sub.each(**v): output(x)

# Handlers for every permutation of sync/async,  normal/generator, explicit/implicit
def f_generator_async_implicit(v): return f_generator_async(v, cmd.sub and _send_child_results)
def f_generator_async(v, out=None):
    async def _agen():
        async for x in v: (out or output)(x)
    run_coro(_agen())
    return Command.no_return

def f_generator_implicit(v): return f_generator(v, cmd.sub and _send_child_results)
def f_generator(v, out=None):
    for x in v: (out or output)(x)
    return Command.no_return

# As a tail-call optimization we can do an exec() and reuse-this process for our child call
def f_async_implicit(v): return f_implicit(run_coro(v))
def f_implicit(v):
    if cmd.sub is None: return v
    if v is None: v = {}
    if not isinstance(v, dict): raise ValueError(f"Implicit command '{cmd}' must return None or a dict, not {v!r}")
    return cmd.sub.exec(**v)

def f_async(v): return run_coro(v)
def f(v): return v


def run_coro(coro):
    ''' This is an improved asyncio.run(coro) that handles Ctl-C correctly so that async with() constructs get cleaned up. 
    '''
    global task, loop
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = loop.create_task(coro)
    try:
        return loop.run_until_complete(task)
    except asyncio.CancelledError: # task gets cancelled by the ctl-c signal handler above
        raise KeyboardInterrupt() from None
    finally:
        # Cancel all tasks
        if pending := [t for t in asyncio.all_tasks(loop) if not t.done()]:
            for t in pending: t.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        # Abandoning an async generator (`async for ... break`) doesn't run its finally inline.
        # CPython schedules athrow(GeneratorExit) as a *task*, so closing the loop first just
        # discards that task ("Task was destroyed but it is pending") and the finally never runs --
        # which would leak the child process that Command.each_async() cleans up there.
        loop.run_until_complete(loop.shutdown_asyncgens())
        # Command.each_async() hands venv_path() to the default executor, whose threads outlive the loop
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()


# Read our input from shared memory
import mmap, pickle, traceback
mm_size, mm_fd = map(int, sys.argv[1:3])
mm = mmap.mmap(mm_fd, mm_size)
_config_data, _cmd_info = pickle.loads(mm[:mm_size])
mm.close()
os.close(mm_fd)

# Configuration in three steps: 1) parent/env changes things 2) targets change defaults 3) final changes things
from libclipy.core.config import ConfigVar, target, verbosity, output, Target
import config # Make sure the targets are registered
# 1)
for k,v in _config_data.items(): ConfigVar.set_by_name(k,v)
# 2)
ConfigVar.lock = True
ConfigVar.preserve = False
for t in target.v: Target.call(t)
# 3)
ConfigVar.lock = False
Target.call('final')
ConfigVar.preserve = True

# With the configured verbosity we can now finish setting up logging
logging.getLogger().setLevel((11 if verbosity.v > 0 else 20)-verbosity.v)
ClipyLogFilter.filter_logs().stderr('{lvl} {message}{names} {rloc} {obj}')


# Logs from these will be subject to the configured logging preferences
from libclipy.core.command.command import Command
from libclipy.core.command.cmd import Exec

try:
    if 'cmd' in _cmd_info:
        cmd, args, kwargs = _cmd_info['cmd']
    else:
        from cli import main
        cmd, args, kwargs = main().bind_cli(*_cmd_info['argv']), tuple(), {}
# Set the _sub_cmd for implicit commands.  FIXME: should this be done in cmd.args_kwargs?
    if not cmd.is_implicit: kwargs['_sub_cmd'] = cmd.sub
# cmd_v may be a coro, generator, or the single value to output depending on the function's type.
    cmd_v = type(cmd).call_func(*cmd.args_kwargs(*args, **kwargs))
# The handler decides how to get the value/s from cmd_v to output()
    handler = 'f'+'_generator'*cmd.is_generator + '_async'*cmd.is_async + '_implicit'*cmd.is_implicit
    result = globals()[handler](cmd_v)
    returncode = 0
# If an exception is thrown then the result becomes the exception
except BaseException as e:
    result = e
    returncode = e.returncode if hasattr(e, 'returncode') else 1

# Now either exec or return the returncode
if isinstance(result, Exec):
    # Doing an exec replaces the process without running any __exit__, finally, or atexit handlers.
    # So we explicitly let all those run before doing the exec()
    import atexit
    atexit._run_exitfuncs()
    result()
else:
    if result is not Command.no_return: output(result)
    output.close()
    sys.exit(returncode)
