''' <written by Claude Opus 5>

Channel.parse() contracts.

A channel accumulates raw bytes in `data` and `parse()` hands back one value at a time.  Both
iterators lean on the same contract:

    SyncIterator.next_step   for chan in self._read_gen:
                                 if (v:=chan.parse()) is _NULL: continue
                                 return v
    AsyncIterator.ready_read while (v:=chan.parse()) is not _NULL: self._q.put_nowait((chan, v))

so the hard requirement is that parse() *eventually returns _NULL*.  A parse that keeps handing
back values spins that while-loop forever, and makes next_step's StopIteration unreachable.

`done` is the EOF flag: Channel.close() sets it when the read end hits EOF, and it is what tells
a parser that no more bytes are coming, so an unterminated trailing record can be released.
'''
import time, pytest
from .channels import Read, ReadLine, _NULL


def _drain(chan, limit=20):
    ''' Everything parse() will give up right now, the way ready_read() drains it.

    Bounded, so a parse() that never returns _NULL fails the test instead of hanging the suite.
    '''
    out = []
    for _ in range(limit):
        if (v:=chan.parse()) is _NULL: return out
        out.append(v)
    pytest.fail(f"parse() never returned _NULL; produced {out!r} and kept going")


def _line(data=b'', **kwargs):
    buffer = bytearray(data)
    return ReadLine(src='stdout', buffer=buffer, _view=memoryview(buffer), b0=0, b1=len(data), **kwargs)


# =========================
# While the channel is open
# =========================

def test_a_complete_line_comes_back_with_its_newline():
    ''' The docstring's promise: lines are returned *with* the trailing \\n '''
    chan = _line(b'hello\n')
    assert(chan.parse() == 'hello\n')
    assert(chan.data == b'')


def test_a_partial_line_is_held_until_its_newline_arrives():
    ''' No newline yet and the channel is still open, so there is nothing to hand back '''
    chan = _line(b'hel')
    assert(chan.parse() is _NULL)
    assert(chan.data == b'hel') # ...and the bytes are kept for the next read
    chan.extend_data(b'lo\n')
    assert(chan.parse() == 'hello\n')


def test_lines_come_back_one_at_a_time_in_order():
    chan = _line(b'one\ntwo\nthree\n')
    assert(_drain(chan) == ['one\n', 'two\n', 'three\n'])


def test_a_trailing_partial_survives_a_drain():
    ''' Draining yields the complete lines and leaves the unfinished one buffered '''
    chan = _line(b'one\ntwo\nthr')
    assert(_drain(chan) == ['one\n', 'two\n'])
    assert(chan.data == b'thr')


def test_blank_lines_are_preserved():
    ''' An empty line is a value, not an absence of one '''
    chan = _line(b'\n\na\n')
    assert(_drain(chan) == ['\n', '\n', 'a\n'])


def test_carriage_returns_are_left_alone():
    ''' Splitting is on \\n only; \\r is part of the line's content '''
    chan = _line(b'a\r\n')
    assert(chan.parse() == 'a\r\n')


def test_lines_are_decoded_as_utf8():
    chan = _line('héllo ☃\n'.encode('utf8'))
    assert(chan.parse() == 'héllo ☃\n')


# ==========
# After EOF
# ==========

def test_close_marks_eof():
    ''' close() is what tells parse() no more bytes are coming (fd is None here, so nothing to shut) '''
    chan = _line(b'')
    assert(chan.done is False)
    chan.close()
    assert(chan.done is True)


def test_an_unterminated_final_line_is_released_at_eof():
    ''' The child exited without a trailing newline.  Those bytes are still a line. '''
    chan = _line(b'no newline')
    assert(chan.parse() is _NULL) # Still open: it might yet arrive
    chan.close()
    assert(chan.parse() == 'no newline') # No trailing \n, because there wasn't one


def test_eof_drains_complete_and_partial_lines_together():
    chan = _line(b'one\ntwo\nthr')
    chan.close()
    assert(_drain(chan) == ['one\n', 'two\n', 'thr'])


def test_parse_returns_null_once_drained_at_eof():
    ''' The termination half of the contract.  Once the buffer is empty and EOF is reached there
    is nothing left, and parse() has to say so -- otherwise ready_read()'s `while ... is not _NULL`
    never exits and next_step() never reaches its StopIteration.
    '''
    chan = _line(b'one\n')
    chan.close()
    assert(chan.parse() == 'one\n')
    assert(chan.data == b'')
    assert(chan.parse() is _NULL)


def test_parse_returns_null_at_eof_with_no_data_at_all():
    ''' A child that exits having written nothing '''
    chan = _line(b'')
    chan.close()
    assert(chan.parse() is _NULL)


def test_parse_stays_null_at_eof():
    ''' Asked again and again after exhaustion, it keeps saying _NULL '''
    chan = _line(b'one\n')
    chan.close()
    _drain(chan)
    for _ in range(3):
        assert(chan.parse() is _NULL)


def test_draining_a_closed_channel_terminates():
    ''' Exactly the loop AsyncIterator.ready_read runs after it sees a zero-length read '''
    chan = _line(b'one\ntwo\n')
    chan.close()
    assert(_drain(chan) == ['one\n', 'two\n'])
    assert(_drain(chan) == [])


def test_truncated_utf8_at_eof():
    ''' A child killed mid-character leaves an incomplete utf8 sequence, which raises UnicodeDecodeError
    '''
    chan = _line('☃'.encode('utf8')[:2])
    chan.close()
    with pytest.raises(UnicodeDecodeError):
        chan.parse()



# =========================
# The buffer underneath
# =========================

def test_ensure_space_keeps_unconsumed_bytes():
    ''' Unread bytes live in [b0:b1] (see the `data` property).  Making room must move *those* to
    the front, whether it grows the buffer or just recycles the space already consumed.
    '''
    chan = Read(src='stdout')
    chan.extend_data(b'consumed-PENDING')
    chan.b0 = len(b'consumed-')      # the front has been handed out; PENDING has not
    assert(chan.data == b'PENDING')
    chan._ensure_space(len(chan.buffer)*2) # Force the relocate branch
    assert(chan.data == b'PENDING')


def test_a_partial_record_survives_buffer_recycling():
    ''' The same thing through the front door.

    Feeding in pieces that do not line up with the records means a partial line is pending almost
    every time more data arrives, so the buffer has to recycle its consumed space again and again
    while holding that fragment.  Losing it, or shifting it, corrupts the stream.
    '''
    lines = [f"line {i}\n" for i in range(2000)]
    blob = ''.join(lines).encode()
    chan, out = ReadLine(src='stdout'), []
    for i in range(0, len(blob), 7): # 7 bytes at a time: never aligned with the lines
        chan.extend_data(blob[i:i+7])
        while (v:=chan.parse()) is not _NULL: out.append(v)
    assert(out == lines)
