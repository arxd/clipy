import re
from collections import namedtuple
from pathlib import Path
from libclipy.core.pretty import CLR
from cli import ConfigVar
from .sys_tool import SysTool


HUNK_RE = re.compile(r'^(\d+)(?:,(\d+))?([acd])(\d+)(?:,(\d+))?$')
BINARY_RE = re.compile(r'^Binary files .* and .* differ$')


class Change(namedtuple('Change', ('op', 'old', 'new', 'old_lines', 'new_lines'))):
    ''' A single hunk of a diff.

        op
            'a' (added), 'd' (deleted) or 'c' (changed)
        old, new
            The 0-based `range` of lines in the old/new file.
            It is a slice, so ``old_text.splitlines()[c.old.start:c.old.stop] == c.old_lines``.
            An 'a' has an empty `old` range marking where the lines were inserted, and a 'd' has an empty `new` range.
        old_lines, new_lines
            The lines themselves, without their line ending.
    '''
    __slots__ = ()
    OPS = {'a':'add', 'c':'change', 'd':'delete'}

    @classmethod
    def parse(cls, line):
        ''' Build an empty Change from a normal-format header line such as ``1,3c1,4``, or None if it isn't one.
        '''
        if not (m:=HUNK_RE.match(line)): return None
        op, (o0, o1, n0, n1) = m[3], [int(g) for g in (m[1], m[2] or m[1], m[4], m[5] or m[4])]
        return cls(op, range(o0, o0) if op == 'a' else range(o0-1, o1), range(n0, n0) if op == 'd' else range(n0-1, n1), [], [])


    @property
    def name(self):
        return self.OPS[self.op]


    def __str__(self):
        return f"@@ {_at(self.old)} -> {_at(self.new)} @@ {self.name}"


    def pretty(self, indent='  '):
        yield f"{indent}{CLR.c}{self}{CLR.x}"
        for line in self.old_lines: yield f"{indent}{CLR.r}- {line}{CLR.x}"
        for line in self.new_lines: yield f"{indent}{CLR.g}+ {line}{CLR.x}"


def _at(r):
    ''' Render a line range the way a unified diff does: 1-based start,count (start is the insertion point when count is 0)
    '''
    return f"{r.start+1 if len(r) else r.start},{len(r)}"



class FileDiff():
    ''' The comparison of file `a` (old) with file `b` (new).

        path
            The name this comparison is reported under
        changes
            The list of Change hunks
        binary
            The files differ but diff couldn't say how
        missing
            The paths (of a and/or b) that don't exist, in which case there are no changes
    '''
    def __init__(self, a, b, *, path=None, changes=(), binary=False, missing=()):
        self.a, self.b = Path(a), Path(b)
        self.path = Path(path) if path else self.b
        self.changes = list(changes)
        self.binary = binary
        self.missing = tuple(missing)


    @classmethod
    def parse(cls, a, b, out, *, path=None):
        ''' Parse the normal-format output of ``diff a b``.  `out` is None or '' when the files are the same.
        '''
        self = cls(a, b, path=path)
        for line in (out or '').splitlines():
            if change:=Change.parse(line):
                self.changes.append(change)
            elif BINARY_RE.match(line):
                self.binary = True
            elif line[:1] in ('<', '>') and self.changes:
                (self.changes[-1].old_lines if line[0] == '<' else self.changes[-1].new_lines).append(line[2:])
        return self


    @property
    def status(self):
        ''' One of 'missing', 'binary', 'differ' or 'same' '''
        if self.missing: return 'missing'
        if self.binary: return 'binary'
        return 'differ' if self.changes else 'same'


    @property
    def counts(self):
        ''' The number of (added, deleted, changed) lines '''
        n = dict(a=0, d=0, c=0)
        for c in self.changes: n[c.op] += max(len(c.old), len(c.new))
        return (n['a'], n['d'], n['c'])


    def pretty(self):
        clr = {'same':CLR.a, 'differ':CLR.y, 'binary':CLR.m, 'missing':CLR.r}[self.status]
        note = ' '.join(str(m) for m in self.missing) or (f"+{self.counts[0]} -{self.counts[1]} ~{self.counts[2]}" if self.changes else '')
        yield f"{CLR.bld}{self.path}{CLR.x} {clr}{self.status}{CLR.x} {note}"
        for c in self.changes: yield from c.pretty()



class Diff(SysTool):
    ''' The system diff tool, returning structured results.

        Diff().compare('old.py', 'new.py')
    '''
    version = None
    version_probe = None
    cmd = ConfigVar('diff_path The path to the diff executable', default='diff')


    def compare(self, a, b, path=None):
        ''' Compare file `a` (old) with file `b` (new) and return a FileDiff.
        '''
        a, b = Path(a), Path(b)
        if missing:=tuple(f for f in (a,b) if not f.is_file()):
            return FileDiff(a, b, path=path, missing=missing)
        out = self(a, b, msg=None, if_0='null,null,', if_1='utf8,null,', or_else='null,,raise diff failed')
        return FileDiff.parse(a, b, out, path=path)
