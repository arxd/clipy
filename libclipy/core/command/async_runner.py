import signal, asyncio, os
from .errors import CtlCException


def run_coro(coro):
    ''' This is an improved asyncio.run(coro) that handles Ctl-C correctly so that async with() constructs get cleaned up. 
    '''
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
        raise CtlCException() from None
    finally:
        loop.close()



def has_running_loop():
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False
