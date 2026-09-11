import sys, os, pickle, base64, traceback, json, logging

# python is executed with -I, so we need to manually add the project root to the path
sys.path.insert(0, os.environ['_CLIPY_ROOT'])
# Change to the root so every command knows where it is at
os.chdir(os.environ['_CLIPY_ROOT'])

# Get logging class early so top-level getLogger() during imports uses our logger
from libclipy.core.logger import ClipyLogger, ClipyLogFilter
logging.getLogger().setLevel(logging.NOTSET)
logging.setLoggerClass(ClipyLogger)

from cli import Exec, main
from config import env
from libclipy.core.command.command import FRAME

if sys.argv[1]: # Get our data from the parent cmd
    with open(int(sys.argv[1]), 'rb', closefd=True) as f:
        data = pickle.load(f)
else: # We are main() cmd
    env.work.mkdir(parents=True, exist_ok=True)
    data = {}

# Initialize the configuration environment
from libclipy.core.config import initialize_config
initialize_config(data.get('env'))

# Logging filter
logging.getLogger().setLevel((11 if env.verbosity > 0 else 20)-env.verbosity)
ClipyLogFilter.filter_logs().stderr('{lvl} {message}{names} {rloc} {obj}')


# ==========
# Output
# ==========

from libclipy.core.pretty import print

def output_pretty(v, stream):
    if v is None: return
    print.set_stream(stream)
    print.pretty(v)


def output_json(v, stream):
    stream.write(json.dumps(v))


def output_pickle(v, stream, binary=False):
    if hasattr(v, '__traceback__'):
        v.traceback_text = "".join(traceback.format_exception(type(v), v, v.__traceback__))
        v.__traceback__ = None
        v.__context__ = None
        v.__cause__ = None
    if binary:
        b = pickle.dumps(v, protocol=5)
        stream.write(FRAME.pack(len(b)))
        stream.write(b)
        # `out` is a 128KB BufferedWriter, so without this nothing reaches our parent until we exit,
        # which would defeat the point of Command.each_async() yielding values as they arrive.
        stream.flush()
    else:
        stream.write(base64.b64encode(pickle.dumps(v, protocol=5)).decode('ascii'))        


# ==========
# Runners
# ==========

def implicit_normal(cmd, args, kwargs):
    ''' The command function will not call the child command so we need to call it.
    Our return value depends on if there is a child or not.
    If there is no child then return our return value.
    If there is a child then our return value becomes its parameters and we return its return value.
    '''
    result = type(cmd).__func__(*args, **kwargs)
    if cmd.is_async: result = run_coro(result)
    if cmd.sub is not None: 
        result = {} if result is None else result
        if not isinstance(result, dict): raise ValueError(f"Implicit command '{cmd}' must return None or a dict, not {result!r}")
        # Our command has finished so instead of spawning a new process for the sub-command, just exec() into it with a tail-call.
        result = cmd.sub.exec(**result) # The exec() doesn't happen at this point, result will be an Exec object
    return output(result)


def explicit_normal(cmd, args, kwargs):
    ''' The Command function is in charge of calling the sub-command
    '''
    result = type(cmd).__func__(*args, **kwargs)
    if cmd.is_async: result = run_coro(result)
    return output(result)


def implicit_generator(cmd, args, kwargs):
    ''' This generator will yield multiple results.
    If we don't have a child then each of those results is returned.
    If we do have a child then each of those results is used as the arguments to a call of the child.
    '''
    def _send_child_results(result):
        result = {} if result is None else result
        if not isinstance(result, dict): raise ValueError(f"Implicit generator '{cmd}' must yield None or a dict, not {result!r}")
        if cmd.sub is None:
            output(result)
        else: # We have a child so yield each one of its result as our own
            for x in cmd.sub.each(**result):
                output(x)

    gen = type(cmd).__func__(*args, **kwargs)
    if cmd.is_async:
        async def _agen():
            async for result in gen: _send_child_results(result)
        run_coro(_agen())
    else:
        for result in gen: _send_child_results(result)


def explicit_generator(cmd, args, kwargs):
    gen = type(cmd).__func__(*args, **kwargs)
    if cmd.is_async:
        async def _agen():
            async for result in gen: output(result)
        run_coro(_agen())
    else:
        for result in gen: output(result)


def run_coro(coro):
    ''' This is an improved asyncio.run(coro) that handles Ctl-C correctly so that async with() constructs get cleaned up. 
    '''
    import asyncio, signal
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
# A wrapper to catch cancel and allow a double ctl-C for hard kill
    task = loop.create_task(coro)
# Handle ctl-c SIGINT
    def handle_signal(signal, _):
        nonlocal task
        if task is None: os._exit(128+signal) # FIXME We need to SIGKILL open child processes
        loop.call_soon_threadsafe(task.cancel)
        task = None
    signal.signal(signal.SIGINT, handle_signal)
# Run the loop
    try:
        return loop.run_until_complete(task)
    except asyncio.CancelledError:
        raise KeyboardInterrupt() from None
    finally:
        # Abandoning an async generator (`async for ... break`) doesn't run its finally inline.
        # CPython schedules athrow(GeneratorExit) as a *task*, so closing the loop first just
        # discards that task ("Task was destroyed but it is pending") and the finally never runs --
        # which would leak the child process that Command.each_async() cleans up there.
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


# ==========
# Main
# ==========

fd = os.environ.get('_CLIPY_FD')
out = fd and open(int(fd), 'wb', closefd=False)

def output(v):
    if isinstance(v, Exec): return v
    fmt = env.format if fd is None else 'pickle'
    if fmt == 'pickle': return output_pickle(v, out or sys.stdout, out)
    if isinstance(v, Exception): return output_pretty(v, sys.stderr)
    return (output_json if fmt=='json' else output_pretty)(v, sys.stdout)

try:
    cmd = data.get('cmd', main.instance().bind(*sys.argv[2:]))
    kwargs = data.get('kwargs',{})
    if not cmd.is_implicit: kwargs['_sub_cmd'] = cmd.sub
    handler = ['explicit','implicit'][cmd.is_implicit] + '_' + ['normal','generator'][cmd.is_generator]
    result = globals()[handler](cmd, *cmd.args_kwargs(*data.get('args',tuple()), **kwargs))

except Exception as e:
    output(e)
    sys.exit(e.returncode if hasattr(e, 'returncode') else 1)

finally:
    if out: out.close()

if result:
    # Result is an Exec object.  Doing an exec replaces the process without running any __exit__, finally, or atexit handlers.
    # So we explicitly let all those run before doing the exec()
    import atexit
    atexit._run_exitfuncs()
    result()
    # never gets here

if fd: os.close(int(fd))
