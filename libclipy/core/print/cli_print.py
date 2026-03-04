import re

class ProgressBar():
    def __init__(self, **kwargs):
        self.stream = kwargs.get('stream', sys.stdout)
        self.width = kwargs.get('width',40)
        self.step_i = 0
        self.steps = kwargs.get('steps',0)
        self.prev_len = 0


    def bar(self, done, *msg):
        if done:
            bar = CLR.g + '━'*self.width
        elif not self.steps:
            w = self.width // 4
            i = self.step_i%w
            bar = CLR.a + '━━━━'*i +' '+ CLR.y + '━━ ' + CLR.a  + '━━━━'*(w-i-1)
        else:
            prog = int(min(1.0, self.step_i/self.steps)*self.width)
            bar = CLR.y + '━'*prog + ' '+ CLR.a + '━'*(self.width-prog-1)
        txt = bar + CLR.x + '  ' + str(Text(*msg)) + ' '
        txt += ' '*(self.prev_len - len(txt))
        self.prev_len = len(txt)
        return txt


    def step(self, *parts):
        self.stream.write('\r ' + self.bar(False, *parts))
        self.stream.flush()
        self.step_i += 1


    def done(self, *parts):
        self.stream.write('\r ' + self.bar(True, *parts) + '\n')




class Text(list):
    @staticmethod
    def unindent(p):
        # Unindent multi-line strings
        newlines = p.strip().splitlines()
        indent = ''
        for line in newlines[1:]: # The first line is skipped because it starts right after the opening '''
            stripped = line.lstrip()
            if stripped: # First non-blank line sets the indentation level
                indent = line[:len(line)-len(stripped)]
                break
        n_indent = len(indent)
        if indent: newlines = [l[n_indent:] if l.startswith(indent) else l for l in newlines]
        return newlines


    @staticmethod
    def l10n(p):
        lang = os.environ.get('CLIPY_LANG', 'en')
        if lang in p: p = p[p.index(lang)+len(lang):]
        return p.split('~lang',1)[0]


    def __init__(self, *msg, **kwargs):
        self.wrap = kwargs.get('wrap', True)
        self.indent = kwargs.get('indent', '')
        self.color = kwargs.get('color', '')
        if msg: self(*msg)
    

    def width(self):
        return max(map(lambda l: ConsoleBuffer.guessw(l.rstrip()), self)) if self else 0
        

    def __str__(self):
        return '\n'.join(self)


    def __call__(self, *msg):
        self.append('')
        for m in msg:		
            if isinstance(m, str):
                m = Text.l10n(m)
                newlines = Text.unindent(m) if '\n' in m else [m]
            else:
                newlines = []
                try:
                    m = map(str, m)
                except:
                    m = [str(m)]
                for n in m:
                    newlines += n.split('\n')
            newlines = [l.replace('\t','    ') for l in newlines]
            if not newlines: continue
            self[-1] += newlines[0]
            self += newlines[1:]
        return self


    def reflow(self, width=0, height=0, **kwargs):
        body = []
        min_brk = max(width - 15, 15)
        width = width and max(4, width - ConsoleBuffer.guessw(self.indent))
        def _grp(c):
            if c in '0123456789.０１２３４５６７８９': return 1
            c = ord(c)
            if c >= 0x3040 and c <= 0x309F: return 2
            if c >= 0x30A0 and c <= 0x30FF: return 3
            return 4

        def _brk(line, i):
            if line[i] in '\'",': return 2
            if line[i] in ' 　「' or line[i-1] in '。、！？': return 3
            if _grp(line[i-1]) != _grp(line[i]): return 2
            return 1

        def _wrap(line):
            i = w = bi = bw = bs = 0
            while i < len(line):
                if w > min_brk:
                    b = _brk(line, i)
                    if b >= bs: bs,bw,bi = b,w,i
                cw = _wcswidth(line[i])
                w += cw
                if w < width or i == len(line)-1 and w == width:
                    i += 1
                    continue
                # Can't fit i on this line
                w -= cw
                if width <= 4 or not self.wrap: # No wrap
                    #body.append((w+1, line[:i]+'…'))
                    return '', line[:i]+'…'
                if bs: # Rewind to the last break point
                    i, w = bi,bw
                #body.append((w, line[:i]))
                return '⤷ ' + line[i:].lstrip(), line[:i]
            return '', line
            #body.append((w,line))
        rout = 0
        for line in self:
            line = line.rstrip().replace('\t','    ')
            if not width or _wcswidth(line) <= width:
                rout += 1
                yield self.indent+self.color+line+(CLR.x if self.color else '')
            else:
                #return body.append((linew if linew >=0 else ConsoleBuffer.guessw(line), line))
                while line:
                    line, short = _wrap(line)
                    if short:
                        rout += 1
                        yield self.indent+self.color+short+(CLR.x if self.color else '')

        while rout < height:
            rout += 1
            yield self.indent



class Box():
    default_border = '┌┐└┘─│'

    def __init__(self, *msg, **kwargs):
        self.just = kwargs.get('just', '^<')
        self.sides = kwargs.get('sides', 15) # top right bottom left
        self.border = kwargs.get('border', Box.default_border)
        self.height = kwargs.get('height', 0)
        self.body = Text(*msg, **kwargs)


    def __call__(self, *msg):
        self.body(*msg)


    def __len__(self):
        return self.height or (len(self.body) + (self.sides>>3&1) + (self.sides>>1&1))

    
    def __bool__(self):
        return bool(self.body)


    def width(self):
        return self.body.width() + (self.sides>>2&1) + (self.sides&1)


    def reflow(self, width=0, height=0, **kwargs):
        sides = self.sides
        #sides = self.sides & 10 if width and width < 3 else self.sides
        #sides = sides & 5 if height and height < 3 else sides
        T,R,B,L = [sides>>i&1 for i in range(3,-1,-1)]
        body_w = width and width-R-L
        body = [(ConsoleBuffer.guessw(l), l) for l in self.body.reflow(body_w)]
        height = (height or self.height or (len(body)+T+B)) -T-B

        # horizontal justification
        maxw = body_w or reduce(lambda a, l: max(a,l[0]), body, 0)
        def _just(line, just):
            pre = ' '*{'<':0, '.':(maxw-line[0])//2, '>':(maxw-line[0])}[just]
            return pre + line[1] + ' '*(maxw-line[0]-len(pre))
        body = [_just(l, self.just[1]) for l in body]
        if height and len(body) > height:
            overflow = '⋮%s'%(len(body)-height+1)
            body = body[:height-1] + [_just((len(overflow), overflow), '.')]
        # vertical justification
        pad_height = height - len(body)
        pad_start = [] if pad_height <= 0 else [' '*maxw]*{'^':0, '.':pad_height//2, '_':pad_height}[self.just[0]]
        pad_end = [] if pad_height <= 0 else [' '*maxw]*(height - len(pad_start) - len(body))

        if T: yield (self.border[0] if L else '') + self.border[4]*maxw + (self.border[1] if R else '')
        for line in pad_start + body + pad_end:
            yield (self.border[5] if L else '') + line + (self.border[5] if R else '')
        if B: yield (self.border[2] if L else '') + self.border[4]*maxw + (self.border[3] if R else '')




class DefaultCell(Box): pass

    

class Table():
    default_border = '┌┬┐├┼┤└┴┘─│'

    def __init__(self, *cols, **kwargs):
        self.stream = kwargs.get('stream', sys.stdout)
        self.ncols = len(cols)
        self.col_widths = cols
        self.col_color = [kwargs.get('color%s'%i, kwargs.get('color', '')) for i in range(self.ncols)]
        self.col_border = [kwargs.get('border%s'%i, kwargs.get('border', Table.default_border))+' '*11 for i in range(self.ncols)]
        self.col_just = [kwargs.get('just%s'%i, kwargs.get('just', '^<')) for i in range(self.ncols)]
        self.col_sides = [kwargs.get('sides%s'%i, kwargs.get('sides', 0x3f)) for i in range(self.ncols)]
        assert(self.ncols)
        self.rows = []


    def __bool__(self):
        return bool(self.rows)


    def __len__(self):
        return len(list(self.reflow()))


    def width(self):
        try:
            return ConsoleBuffer.guessw(next(iter(self.reflow())))
        except:
            return 0


    def reflow(self, width=0, height=0, **kwargs):
        if not self.rows: return
        # Add bottom borders
        for i, c in enumerate(self.rows[-1]):
            if not isinstance(c, DefaultCell): continue
            c.sides |= 2 if self.col_sides[i] & 2 else 0
        # Resolve widths
        def _w0(col_i):
            return max(map(lambda r: r[col_i].width(), self.rows))
        if width:
            widths = [_w0(i) if c <= 0 else int(width*c) if c < 1 else c for i,c in enumerate(self.col_widths)]
            free = width - sum(widths)
            # Shrink columns
            while free < 0:
                widths[widths.index(max(widths))] -= 1
                free += 1
            # split extra space between negative columns
            frac = sum([-x for x in self.col_widths if x < 0] or [0])
            for i, c in enumerate(self.col_widths):
                if c >= 0: continue
                widths[i] = int(-c*free/frac)
            # Allocate superfluous space to the last column
            widths[i] += width - sum(widths)
            assert(sum(widths) == width)
        else:
            widths = [_w0(i) for i in range(self.ncols)]
        #
        hout = 0
        for row in self.rows:
            lines = [list(o.reflow(width=w)) for w,o in zip(widths, row)]
            h = max(map(len, lines))
            lines = [list(o.reflow(width=w, height=h)) for w,o in zip(widths, row)]
            for r in range(h):
                hout += 1
                yield ''.join([lines[c][r] for c in range(self.ncols)])
        end = ' '*ConsoleBuffer.guessw(''.join([lines[c][0] for c in range(self.ncols)]))
        while hout < height:
            hout += 1
            yield end
        

    def reset(self):
        self.rows = []			


    def __call__(self, *objs, **kwargs):
        def _add(obj):
            if not self.rows or len(self.rows[-1]) % self.ncols == 0:
                self.rows.append([])
            self.rows[-1].append(obj)
        for o in objs:
            if isinstance(o, DefaultCell) or not hasattr(o, 'reflow'):#isinstance(o, Box):
                col = (len(self.rows[-1]) if self.rows else 0)%self.ncols
                csides = kwargs.get('sides', self.col_sides[col])
                cborder = kwargs.get('border', self.col_border[col])
                just = kwargs.get('just', self.col_just[col])
                color = kwargs.get('color', self.col_color[col])
                sides = 0
                Rf, Cf, Cl = (not self.rows or len(self.rows)==1 and len(self.rows[0]) < self.ncols, col==0, col==self.ncols-1)
                border = cborder[0 if Rf and Cf else 1 if Rf else 3 if Cf else 4]
                border += cborder[2 if Rf else 5]
                border += cborder[6 if Cf else 7] + cborder[8]
                border += cborder[9:]
                sides += 1 if csides&(1 if Cf else 16) else 0 # Left edge
                sides += 8 if csides&(8 if Rf else 32) else 0 # Top edge
                sides += 4 if csides&4 and Cl else 0 # right edge
                if isinstance(o, DefaultCell):
                    o.sides, o.border, o.just = sides, border, just
                else:
                    o = DefaultCell(*(o if isinstance(o, tuple) else (o,)), sides=sides, border=border, just=just, color=color)
            _add(o)


class Color():
    def __init__(self):
        self.color_on = True

    def __getattr__(self, a):
        if not self.color_on: return ''
        a = {'a':'1;30', 'la':'0;37', 'r':'0;31', 'lr':'1;31', 'g':'0;32', 'lg':'1;32', 'o':'0;33','y':'1;33','b':'0;34','lb':'1;34','m':'0;35', 'lm':'1;35', 'c':'0;36', 'lc':'1;36', 'bld':'1','w':'1','x':'0'}[a]
        return '\x1b['+a+'m'



class ConsoleBuffer():
    color_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    @classmethod
    def guessw(self, s):
        s = self.color_escape.sub('', s)
        w = _wcswidth(s)
        return len(s) if w < 0 else w


    def __init__(self, stream, color=None):
        self.set_stream(stream, color=color)
        self.set_doc_lang(False,False)
        self.blank = {}


    def set_doc_lang(self, en, ja):
        os.environ['CLIPY_LANG'] = '~lang en~'
        #if en or ja:
        #    os.environ['CLIPY_LANG'] = '~lang ' + ('en' if en else 'ja') + '~'
        #else:	
        #    os.environ.setdefault('CLIPY_LANG', '~lang ' + ('ja' if 'ja' in os.environ.get('LANG', '') else 'en') + '~')


    def set_stream(self, stream, color=None):
        self.stream = stream
        try:
            ConsoleBuffer.w = os.get_terminal_size().columns - 1
        except:
            ConsoleBuffer.w = 79

        try:
            from wcwidth import wcswidth
            global _wcswidth
            _wcswidth = wcswidth
        except:
            pass
        
        CLR.color_on = (os.environ.get("CLIPY_COLOR", 'y' if self.stream.isatty() else 'n').lower() == 'y') if color==None else color
        #self.stream.write(CLR.x)
        self.ERR = CLR.lr + 'Error: ' + CLR.x
        self.WARN = CLR.y + 'Warning: ' + CLR.x


    def __call__(self, *objs, **kwargs):
        stream = kwargs.get('stream', self.stream)
        self.blank.setdefault(stream, 0)
        for obj in objs:
            if hasattr(obj, 'reflow'):
                lines = obj.reflow(kwargs.get('width',0))
            else:
                lines = str(obj).split('\n')
            new_blank = 0
            for line in lines:
                line = line.rstrip()
                if not line and self.blank[stream]:
                    self.blank[stream] -= 1
                    continue
                self.blank[stream] = 0
                new_blank = 0 if line else new_blank + 1
                stream.write(line+'\n')
            self.blank[stream] += new_blank


    def print(self, *msg, end='\n'):
        self.stream.write(' '.join(map(str,msg)) + end)


    def pretty(self, v, expand=0, **kwargs):
        kwargs.setdefault('width', print.w)
        self('', Pretty(v, expand), '', **kwargs)


    def ln(self, *msg, **kwargs):
        self('', Text(*msg, **kwargs), '', **kwargs)


    def hr(self):
        self('━'*ConsoleBuffer.w)


    def progress(self, *msg, **kwargs):
        self('', Text(*msg))
        kwargs.setdefault('stream', self.stream)
        return ProgressBar(**kwargs)


    def box(self, *msg, **kwargs):
        self(*Box(*msg, **kwargs).reflow(kwargs.get('width',0), kwargs.get('height',0)))


    def ftr(self, *msg, **kwargs):
        txt = Text(*msg, **kwargs)
        if not txt: return self.hr()
        tbl = Table(0,-1,sides=0)
        b = Box(txt[:1], sides=7, **kwargs)
        bw = b.width()
        tbl('┯'+'━'*(bw-2)+'┯', '━'*(ConsoleBuffer.w-bw))
        tbl(b.reflow(), txt[1:])
        self(tbl, width=ConsoleBuffer.w)



class DocText():
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)
        self.subs = []


    def parse(self, indent, i, lines):
        self.indent = indent
        sec = []
        while True:
            indent = (len(lines[i]) - len(lines[i].lstrip()) if lines[i].strip() else self.indent) if i < len(lines) else -1
            if indent != self.indent or not lines[i].strip():
                if sec:
                    self.subs.append(self.sub_doc(sec))
                    sec = []
                if indent < self.indent:
                    return i, indent
                if indent > self.indent:
                    i, indent = self.subs[-1].parse(indent, i, lines)
                    i -= 1
            else:
                sec.append(lines[i].strip())
            i += 1
        

    def sub_doc(self, lines):
        kw = lines[0].lower() if len(lines) == 1 else ''
        if kw == 'parameters:': return DocParameters(dfn=self.dfn, text=Text(lines[0]))
        elif len(lines)==1 and lines[0].endswith(':') and not lines[0].endswith('::'): return DocSection(text=Text(lines[0]))
        return DocText(text=Text('\n'.join(lines)))
        
    
    def print(self, depth, stream=None):
        if hasattr(self, 'text'): 
            self.text.indent = '   '*depth
            print(self.text,'', stream=stream or sys.stdout)
        for s in self.subs:
            s.print(depth + 1, stream)

    def __str__(self):
        return (str(self.text) if hasattr(self, 'text') else '') + '\n'.join(map(str, self.subs))




class DocSection(DocText):
    def print(self, depth=0, stream=None):
        if stream: print.ln('**', self.text, '**', stream=stream)
        else: print.box(self.text)
        for s in self.subs:
            s.print(depth + 1, stream)




class DocParameterGroup(DocText):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.args = []
        
        try:
            p = self.text.split('|')
            assert(len(p) <= 2)
            p, self.explain = p if len(p)>1 else (p[0], '')
            self.explain = self.explain.strip()
            self.required = 'required' in self.explain
            for p in p.split(','):
                p = p.strip().split(' ')
                assert(len(p) <= 2), 'too many spaces %s'%p
                kv, typ = p if len(p)>1 else (p[0], '') if p[0].startswith('-') else ('-', p[0])
                kv2 = kv[2:] if kv.startswith('--') else kv[1:] if kv.startswith('-') else kv
                assert(not kv2 or kv2 not in self.dfn.doc_args), '%s in %s'%(kv2, self.dfn.doc_args)
                if kv2:
                    self.dfn.doc_args[kv2] = typ
                else:
                    self.dfn.doc_args[kv2] += 1
                self.args.append((kv, typ) if kv2 else (typ, ''))
        except Exception as e:
            print(e)
            self.dfn.error("Poorly formated parameter: ", self.text)
        
        
    def print(self, depth, stream=None):
        clrx, clrb, clra = ('','','') if stream else (CLR.x, CLR.b, CLR.lr if self.required else CLR.o)
        args = [clra + v[0] + clrx + (v[1] and ' '+v[1]) for v in self.args]
        expl = self.explain and clrb+' | '+self.explain+clrx
        print(('.. option:: ' if stream else '   '*depth) + ', '.join(args) + expl, stream=stream or sys.stdout)
        if stream: print('', stream=stream)
        for s in self.subs:
            s.print(depth + 1, stream)




class DocParameters(DocSection):
    def sub_doc(self, lines):
        return DocParameterGroup(dfn=self.dfn, text=lines[0])

    def print(self, depth=0, stream=None):
        if not stream: return super().print(depth)
        for s in self.subs:
            s.print(depth, stream)



def _pretty_obj(v, expand, width, depth):
    if not hasattr(v, '__pretty__'): return None
    stream = io.StringIO()
    p = ConsoleBuffer(stream, color=True)
    v.__pretty__(p)
    return stream.getvalue().split('\n')

def _pretty_dict(v, expand, width, depth):
    try:
        keymax = max(map(ConsoleBuffer.guessw, map(str, v.keys())))
        assert(not width or width-keymax > 30)
    except:
        return None
    clr = [CLR.o, CLR.c, CLR.m, CLR.g][depth%4]
    lines = []
    for k, v in v.items():
        k = str(k)
        for i, line in enumerate(Pretty(v).reflow(expand=expand, width=width and width-keymax-1, depth=depth+1)):
            prefix = ' '*(keymax+1) if i else ' '*(keymax-ConsoleBuffer.guessw(k))+clr+k+CLR.x+' '
            lines.append(f'{prefix}{line}')
    return lines

def _pretty_list(v, expand, width, depth):
    if isinstance(v, list) or isinstance(v, tuple):
        return _pretty_dict({f'[{i}]':val for i,val in enumerate(v)}, expand, width, depth)

def _pretty_flat(v, expand, width, depth):
    return list(Text((repr(v),)).reflow(width=width))


class Pretty():
    def __init__(self, value, expand=0):
        self.expand = expand
        self.value = value

    def __len__(self):
        return len(self.reflow())

    def width(self):
        return max(map(ConsoleBuffer.guessw, self.reflow()))

    def reflow(self, width=0, height=0, expand=0, depth=0, **kwargs):
        for fn in (_pretty_obj, _pretty_list, _pretty_dict, _pretty_flat):
            lines = fn(self.value, expand or self.expand, width, depth)
            if lines != None: break
        yield from lines[:height or len(lines)]
        if len(lines) < height: yield from ['']*(height-len(lines))
            
            
CLR = Color()
_wcswidth = lambda x: len(x)
import os, sys, io
from functools import reduce
print = ConsoleBuffer(sys.stdout)
