from libclipy.tools.diff import Change, FileDiff, Diff


OLD = 'a\n\nb\nc\nd\n'
NEW = 'a\nZ\nc\nd\ne\n'
OUT = '''2,3c2
<
< b
---
> Z
5a5
> e
\\ No newline at end of file
'''


def parsed():
    return FileDiff.parse('old.py', 'new.py', OUT)


def test_change_ranges():
    ''' The ranges are 0-based slices of the old/new file '''
    c, a = parsed().changes
    assert (c.op, c.name) == ('c', 'change')
    assert (c.old, c.new) == (range(1,3), range(1,2))
    assert (a.op, a.old, a.new) == ('a', range(5,5), range(4,5))


def test_change_lines_slice_the_files():
    old, new = OLD.splitlines(), NEW.splitlines()
    for c in parsed():
        assert old[c.old.start:c.old.stop] == c.old_lines
        assert new[c.new.start:c.new.stop] == c.new_lines


def test_status():
    d = parsed()
    assert bool(d) and d.status == 'differ' and len(d) == 2
    assert d.counts == (1, 0, 2)
    assert not FileDiff.parse('a', 'b', None)
    assert FileDiff.parse('a', 'b', '').status == 'same'
    assert FileDiff.parse('a', 'b', 'Binary files a and b differ\n').status == 'binary'
    assert FileDiff('a', 'b', missing=['b']).status == 'missing'


def test_hunk_header_only():
    assert Change.parse('5d7')._replace(old_lines=[], new_lines=[]) == ('d', range(4,5), range(7,7), [], [])
    assert Change.parse('---') is None
    assert Change.parse('> not a header') is None


def test_compare(tmp_path):
    old, new = tmp_path/'old.py', tmp_path/'new.py'
    old.write_text(OLD)
    new.write_text(NEW)
    diff = Diff()
    d = diff.compare(old, new, path='here.py')
    assert str(d.path) == 'here.py'
    assert [c.op for c in d] == ['c', 'a']
    assert not diff.compare(old, old)
    assert diff.compare(old, tmp_path/'nope.py').missing == (tmp_path/'nope.py',)
