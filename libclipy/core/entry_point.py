# python is executed with -I, so we need to manually add the project root to the path
import sys, os, signal, time, logging
sys.path.insert(0, sys.argv[3])
os.chdir(sys.path[0])

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


# Output the value in pickle format (this way can encode the most variety of outputs)
# For sub-commands sending through a pipe to the parent, this is the only output available and binary is set to True.
# However, you can even choose to send the pickled object to stdout, but in that case it will be b64 encoded.
def output_pickle(v, stream):
    if hasattr(v, '__traceback__'):
        if not hasattr(v, 'traceback_text'):
            v.traceback_text = traceback.format_exception(type(v), v, v.__traceback__)
        v.__traceback__ = None
        v.__context__ = None
        v.__cause__ = None
    b = pickle.dumps(v, protocol=5)
    try:
        stream.write(PICKLE_HDR.pack(len(b)))
        stream.write(b)
        # `out` is a 128KB BufferedWriter, so without this nothing reaches our parent until we exit,
        # which would defeat the point of Command.each_async() yielding values as they arrive.
        stream.flush()
    except BrokenPipeError:
        pass


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
# Run the loop
    try:
        return loop.run_until_complete(task)
    except asyncio.CancelledError:
        raise KeyboardInterrupt() from None
    finally:
        # Tasks other than ours can still be pending (an asyncio.gather() whose parent was
        # cancelled abandons its children).  A task suspended inside an async generator holds
        # that generator mid-asend, and shutdown_asyncgens() can't aclose() a running generator
        # ("aclose(): asynchronous generator is already running").  So settle the tasks first,
        # exactly as asyncio.run() does.
        if pending := [t for t in asyncio.all_tasks(loop) if not t.done()]:
            for t in pending: t.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        # Abandoning an async generator (`async for ... break`) doesn't run its finally inline.
        # CPython schedules athrow(GeneratorExit) as a *task*, so closing the loop first just
        # discards that task ("Task was destroyed but it is pending") and the finally never runs --
        # which would leak the child process that Command.each_async() cleans up there.
        loop.run_until_complete(loop.shutdown_asyncgens())
        # each_async() hands venv_path() to the default executor, whose threads outlive the loop
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()


import mmap, pickle, traceback
from libclipy.core.config import initialize_config, out_fd, verbosity, format_out

# Read our input from shared memory
mm_size, mm_fd = map(int, sys.argv[1:3])
mm = mmap.mmap(mm_fd, mm_size)
_config_data, _cmd_info = pickle.loads(mm[:mm_size])
mm.close()
os.close(mm_fd)

# Use the _config_data to initilize our ConfigVar values
initialize_config(_config_data)
# With the configured verbosity we can now finish setting up logging
logging.getLogger().setLevel((11 if verbosity.v > 0 else 20)-verbosity.v)
ClipyLogFilter.filter_logs().stderr('{lvl} {message}{names} {rloc} {obj}')

# Logs from these will be subject to the configured logging preferences
from libclipy.core.command.command import Command
from libclipy.core.command.cmd import Exec
from libclipy.core.command.channels import PICKLE_HDR

# Where is our output going?
if out_stream:=out_fd.v and open(out_fd.v, 'wb', closefd=False): # Don't closefd because we might pass it along if we Exec
    # A child command always returns pickled results through the pipe (out_fd)
    output = lambda v: output_pickle(v, out_stream)
else: # The root command's results go to stdout/stderr, but how should we format the result?
    from libclipy.core.pretty import print
    if format_out.v == 'pickle': # Pickle base64 results
        import base64
        output = lambda v: sys.stdout.write(base64.b64encode(pickle.dumps(v, protocol=5)).decode('ascii'))
    elif format_out.v == 'json': # Json
        import json
        output = lambda v: sys.stdout.write(json.dumps(v))
    else: # pretty
        output = lambda v: v is not None and print.pretty(v)

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
# The handler decides how to get the value('s) from cmd_v to output()
    handler = 'f'+'_generator'*cmd.is_generator + '_async'*cmd.is_async + '_implicit'*cmd.is_implicit
    result = globals()[handler](cmd_v)
# The result may be a value to return, or an Exec to replace the current process
    if not isinstance(result, Exec):
        if result is not Command.no_return: output(result)
        if out_stream: os.close(out_fd.v) # We handled the output() (didn't exec) so close the fd

except BaseException as e:
    output(e)
    sys.exit(e.returncode if hasattr(e, 'returncode') else 1)

finally:
    try:
        if out_stream: out_stream.close()
    except (OSError, BrokenPipeError): # FIXME: Is this needed?
        pass

if isinstance(result, Exec):
    # result was an Exec object
    # Doing an exec replaces the process without running any __exit__, finally, or atexit handlers.
    # So we explicitly let all those run before doing the exec()
    import atexit
    atexit._run_exitfuncs()
    result()
