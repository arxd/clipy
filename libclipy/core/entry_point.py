import sys, os, pickle, base64, traceback, json

# python is executed with -I, so we need to manually add the project root to the path
sys.path.insert(0, os.environ['_CLIPY_ROOT'])
# Change to the root so every command knows where it is at
os.chdir(os.environ['_CLIPY_ROOT'])

from cli import Exec, main
from config import env

# Get our data from the parent
if sys.argv[1]:
    with open(int(sys.argv[1]), 'rb', closefd=True) as f:
        data = pickle.load(f)
else:
    env.work.mkdir(parents=True, exist_ok=True)
    data = {}


# Initialize the configuration environment
from libclipy.core.config import initialize_config
initialize_config(data.get('env'))


# ==========
# Output
# ==========

from libclipy.core.pretty import pretty_tty

def output_pretty(v, stream):
    if v is None: return
    for line in pretty_tty(v):
        stream.write(line)
        stream.write('\n')


def output_json(v, stream):
    stream.write(json.dumps(v))


def output_pickle(v, stream, binary=False):
    if hasattr(v, '__traceback__'):
        v.traceback_text = "".join(traceback.format_exception(type(v), v, v.__traceback__))
        v.__traceback__ = None
        v.__context__ = None
        v.__cause__ = None
    if binary:
        pickle.dump(v, stream, protocol=5)
    else:
        stream.write(base64.b64encode(pickle.dumps(v, protocol=5)).decode('ascii'))        


# ==========
# Runners
# ==========

def implicit_normal(cmd, args, kwargs):
    result = type(cmd).__func__(*args, **kwargs)
    if cmd.is_async: result = run_coro(result)
    # Call the sub-command using result as keyword arguments?
    if cmd.sub is not None: 
        result = {} if result is None else result
        if not isinstance(result, dict): raise ValueError(f"Implicit command '{cmd}' must return None or a dict, not {result!r}")
        result = cmd.sub.exec(**result)
    return output(result)


def explicit_normal(cmd, args, kwargs):
    result = type(cmd).__func__(*args, **kwargs)
    if cmd.is_async: result = run_coro(result)
    return output(result)


def implicit_generator(cmd, args, kwargs):
    if cmd.is_async: raise NotImplementedError()
    for result in type(cmd).__func__(*args, **kwargs):
        # Call the sub-command using result as keyword arguments?
        if cmd.sub is not None: 
            result = {} if result is None else result
            if not isinstance(result, dict): raise ValueError(f"Implicit command '{cmd}' must return None or a dict, not {result!r}")
            result = cmd.sub(**result)
        output(result)


def explicit_generator(cmd, args, kwargs):
    if cmd.is_async: raise NotImplementedError()
    for result in type(cmd).__func__(*args, **kwargs):
        output(result)


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
        if task is None: os._exit(128+signal)
        loop.call_soon_threadsafe(task.cancel)
        task = None
    signal.signal(signal.SIGINT, handle_signal)
# Run the loop
    try:
        return loop.run_until_complete(task)
    except asyncio.CancelledError:
        raise KeyboardInterrupt() from None
    finally:
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
    import atexit
    atexit._run_exitfuncs()
    result()
elif fd:
    os.close(int(fd))
