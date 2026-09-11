import logging, re, json, sys, os
from .pretty import Text, CLR, print, Table, Pretty

class ClipyLogger(logging.Logger):
    ''' This is set as the default Logger class in cli.py
    '''
    def __init__(self, name):
        super().__init__(name)
        self.default_tags = set()


    def __call__(self, *msg, v=0, exc_info=None, stacklevel=0, stack_info=False, name=None, **extra):
        tags = set(extra.get('tags',[])) | self.default_tags
        levelno = (30 if 'warn' in tags else 40 if 'error' in tags else 20 if v <= 0 else 11) - v
        if tags: extra['tags'] = list(tags)
        self.log(levelno, str(Text(*msg)), exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel+2, extra=extra)




class ClipyFormatter(logging.Formatter):
    
    def format(self, r):
        rpath = r.pathname and os.path.relpath(r.pathname)
        r.rloc = '' if not rpath or rpath.startswith('.') else f"{CLR.a}{rpath}:{r.lineno}{CLR.x}"
        clr = CLR.m if r.levelno < 20 else CLR.c if r.levelno < 25 else CLR.y if r.levelno < 35 else CLR.lr
        #r.name = f"{clr}{r.name}{CLR.x}"
        r.lvl = f"{clr}{r.levelno//10}{r.levelno%10 or ' '}{CLR.x}"
        if obj := r.__dict__.get('obj'):
            r.obj = self.format_obj(obj)
        else:
            r.obj = ''
        
        if r.levelno >= 40: r.msg = f"{CLR.r}{r.msg}{CLR.x}"
        elif r.levelno >= 30: r.msg = f"{CLR.y}{r.msg}{CLR.x}"
        elif r.levelno > 20: r.msg = f"{CLR.w}{r.msg}{CLR.x}"
        r.names = ''
        for i, name in enumerate(r.__dict__.get('tags',[]) + [r.name]):
            r.names += ' ' + [CLR.m, CLR.c][i%2] + name
        r.names += CLR.x
        if hasattr(r, 'format'):
            return logging.Formatter(r.format, validate=False, style='{').format(r)
        return super().format(r)


    def format_obj(self, obj):
        tbl = Table(8, 0, sides=0x10, border='')
        tbl('', Pretty(obj))
        return '\n' + '\n'.join(tbl.reflow(width=print.w-9))




class ClipyJsonFormatter(ClipyFormatter):

    def format_obj(self, obj):
        try:
            return '\n    '+json.dumps(obj)
        except:
            return super().format_obj(obj)




class ClipyLogFilter(logging.Handler):
    ''' FIXME: parallel handlers run at the same time.  i.e. You can't filter messages at the root level.
    '''
    _formatter = ClipyFormatter

    @classmethod
    def filter_logs(self, *tags, name='root', **kwargs):
        logger = logging.getLogger(name)
        logger.propagate = False
        filter = self(*tags, logger=logger, **kwargs)
        logger.addHandler(filter)
        return filter
    

    def __init__(self, *tags, logger, level=0):
        super().__init__()
        self.tags_orig = tags
        self.tags = [self._compile(tag) for tag in tags]
        self.levelno = level
        self.actions = []
        self.logger = logger
        self.disabled = False
    
    def filter(self, r):
        raise NotImplementedError()

    def emit(self, r):
        raise NotImplementedError()
        

    def handle(self, r):
        if self._match(r):
            for action in self.actions:
                if (r := action(r)) == None: return
        if self.logger.parent: self.logger.parent.handle(r)
    

    def _compile(self, tag):
        _sub = lambda m: {'.*':r'(\.[^.]+)?', '*':r'[^.]*', '.**': r'(\.[^.]+)*'}.get(m[0])
        return re.compile('^'+re.sub(r'(\.\*\*)|(\.\*)|(\*)', _sub, tag) + '$')


    def _match(self, r):
        if self.disabled: return False
        if r.levelno < self.levelno: return False
        tags = [r.name] + list(r.__dict__.get('tags',[]))
        def _match_any(tag_re):
            for tag in tags:
                if tag_re.match(tag): return True
        for tag_re in self.tags:
            if not _match_any(tag_re): return False
        return True


    def drop(self):
        self.actions.append(lambda _: None)
        return self


    def set_format(self, fmt):
        self.actions.append(lambda r: (r.__dict__.update(dict(format=fmt)), r)[1])
        return self


    def transform(self, handler):
        self.actions.append(handler)
        return self


    def stdout(self, fmt):
        return self.stream(fmt, sys.stdout)


    def stderr(self, fmt):
        return self.stream(fmt, sys.stderr)


    def stream(self, fmt, stream):
        _stdout = logging.StreamHandler(stream)
        _stdout.setFormatter(type(self)._formatter(fmt, validate=False, style='{'))
        self.actions.append(lambda r: (_stdout.handle(r), None)[1])
        return self



class ClipyLogJsonFilter(ClipyLogFilter):
    _formatter = ClipyJsonFormatter

