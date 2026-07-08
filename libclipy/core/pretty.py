import os,traceback

try:
    from wcwidth import wcswidth
except:
    wcswidth = lambda x: len(x)


class Color():
    def __init__(self):
        self.color_on = True

    def __getattr__(self, a):
        if not self.color_on: return ''
        a = {'a':'1;30', 'la':'0;37', 'r':'0;31', 'lr':'1;31', 'g':'0;32', 'lg':'1;32', 'o':'0;33','y':'1;33','b':'0;34','lb':'1;34','m':'0;35', 'lm':'1;35', 'c':'0;36', 'lc':'1;36', 'bld':'1','w':'1','x':'0'}[a]
        return '\x1b['+a+'m'

CLR = Color()


class Txt():
    ''' Single-line mixture of Txt and str of a single style.
    Sub-Txt objects may supplement, or override the style.
    Control characters (such as newline) are rendered instead of functional.
    '''
    @classmethod
    def single(self, txt, *, style=None):
        return self((txt, 0, len(txt), 1), style=style)
    

    def __init__(self, *parts, style=None):
        self.cw = 0
        self.color = style
        self.parts = parts
    

    def __len__(self):
        try:
            return self._len
        except:
            self._len = sum(map(self._len, self.parts))
        return self._len
    

    def _len(self, p):
        return p[2]-p[1] if isinstance(p, tuple) else len(p)
    

    def _pw(self, p, pi):
        if isinstance(p, tuple): return (p[2]-p[1])*p[3]
        if isinstance(p, Txt): return p.width

        return len(p)*self.cw if isinstance(p,str) else p.width


    @property
    def width(self):
        try:
            return self._width
        except:
            self._width = sum(map(self._pw, self.parts))
        return self._width
    
    
    def split(self, width):
        w = 0
        lhs = []
        rhs = ''
        for pi, p in enumerate(self.parts):
            if w + (pw:=self._pw(p)) > width:
                lhs.append(p[:(width-w)//self.cw] if isinstance(p, str) else p.split(width-w))
                rhs = 1/0
                break
            lhs.append(p)
            w += pw
        return Txt(*lhs, style=self.style), Txt(rhs, *self.parts[pi+1:], style=self.style)




def pretty_tty(v):
    width = os.get_terminal_size().columns
    if hasattr(v, 'pretty'):
        yield from v.pretty()
    elif hasattr(v, 'traceback_lines'):
        yield from v.traceback_lines
    elif hasattr(v, '__traceback__'):
        for line in traceback.format_exception(type(v), v, v.__traceback__):
            yield line.rstrip()
    else:
        yield repr(v)
    return
    if width is None: width = os.get_terminal_size().width

    if isinstance(v, dict):
        keys = list(map(str, v.keys()))
        kw = max(map(len, keys))
        if width - kw < width: yield from wrap(repr(v, width))

