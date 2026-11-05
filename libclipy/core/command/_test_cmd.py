import pytest
from .cmd import Cmd, _Conditions
from .channels import Write

def test_condtion_parse():
    ''' unit test _Conditions.parse
    '''
    c = _Conditions()
    with pytest.raises(ValueError):
        c.parse(0, 'bob,cob,x', None)



def test_stdin_bad_values():
    ''' Only allowed to send bytes,bytearray,string
    '''
    w = Write()
    with pytest.raises(ValueError):
        w.send(33)
    with pytest.raises(ValueError):
        w.send({})
    w.send('hello')
    w.send(b'world')
    w.send(bytearray([65,66]))
    assert(w.data == b'helloworldAB')



def test_stdin_no_write_after_done():
    ''' After closing stdout, you can't write again
    '''
    w = Write()
    w.send('hi')
    w.send(None)
    with pytest.raises(ValueError):
        w.send('x')



def test_stdin():
    ''' Simple write to stdin works correctly
    '''
    lines = [x for x in Cmd('cat').iter_sync(stdout='lines', stdin='the quick\nbrown\nfox jumped over\nthe lazy dog')]
    assert(lines == ['the quick\n', 'brown\n', 'fox jumped over\n', 'the lazy dog'])
    assert([x for x in Cmd('cat').iter_sync(stdout='bin', stdin=b'1234')] == [b'1234'])



def test_stdin_multiple_write():
    ''' Writing in multiple chunks works (large and small)
    '''
    cmd = iter(Cmd('cat').iter_sync(stdout='bin', stdin=True))
# Write something large enough to overwhelm buffers
    recv = bytearray()
    for _ in range(64):
        cmd.send(b'x'*1_000_000)
        recv.extend(next(cmd))
    cmd.send(None)
    print(f"{len(recv)} / {len(cmd.channels['stdin'].data)}")
    try:
        while True: recv.extend(next(cmd))
    except StopIteration: pass
    assert(len(recv) == 64_000_000)



@pytest.mark.skip('implement')
def test_stdin_writer_blocks():
    ''' Want to test no_data_to_send() functionality and raised BlockingIOError
    '''



@pytest.mark.skip('implement')
def test_stdin_async():
    ''' Async tests of all stdin functionality
    '''



@pytest.mark.skip('implement')
def test_stdin_close():
    ''' The subprocess closed while we are still trying to write to it.
    '''
    pass



@pytest.mark.skip('implement')
def test_env():
    ''' .env() and .env_set() work correctly
    '''
    pass
