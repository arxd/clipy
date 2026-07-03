import pickle, json, re, logging, inspect
from pathlib import Path

class Hasher():
    ''' This is a wrapper for a SHA256 hash.
    It can hash multiple different kinds of objects such as files, and Make objects
    '''

    def __init__(self, make):
        from Crypto.Hash import SHA256
        self.log = make.log
        self.algo = SHA256.new()
    

    def __call__(self, *items):
        for item in items:
            self.add(item)
    

    def add(self, item):
        if item == None: return
        if isinstance(item, str): item = item.encode('utf8')
        if isinstance(item, bytes):
            #LOG self.log(f"Hash {len(item)} Bytes: {item[:50]}", v=1, tags=['make.hash'])
            self.algo.update(item)
        elif isinstance(item, Path):
            #LOG self.log(f"Hash File: {item}", v=1, tags=['make.hash'])
            self.algo.update(str(item.resolve()).encode('utf8'))
            try:
                with open(item, 'rb') as f:
                    while chunk := f.read(4096):
                        self.algo.update(chunk)
                self.algo.update(b'0')
            except:
                self.algo.update(b'1')
        elif isinstance(item, Make):
            h2 = Hasher(item)
            item.calculate_hash(h2)
            self.algo.update(h2.digest())
        elif isinstance(item, (list, tuple)):
            for i in item: self.add(i)
        elif isinstance(item, dict):
            self.add(list(item.items()))
        elif isinstance(item, set):
            self.add(sorted(list(item)))
        else:
            try:
                self.add(json.dumps(item))
            except:
                raise ValueError(f"Unhashable object {type(item)} {item!r}")


    def digest(self):
        return self.algo.digest()




class Make():
    ''' This represents an expensive action that should only be executed if necessary.
    '''

    @classmethod
    def inline(base):
        def _wrap(f):
            async def _execute(self):
                await base.execute(self)
                (await f(self)) if inspect.iscoroutinefunction(f) else f(self)
            return type(f.__name__, (base, ), {'execute': _execute})
        return _wrap


    @classmethod
    def init(base):
        def _wrap(f):
            def _init(self, **kwargs):
                base.__init__(self, **kwargs)
                f(self)
            return type(f.__name__, (base,), {'__init__':_init})
        return _wrap


    def __init__(self, *deps, **kwargs):
        ''' An instance of this make job.

        Parameters:
            name
                A pathname used as a prefix for the data this Make creates
            cache_file
                The cache file
        '''
        kwargs.setdefault('name', '/')
        kwargs.setdefault('root', None)
        kwargs.setdefault('deps', deps or {})
        for k,v in kwargs.items(): setattr(self, k, v)
        self.log = logging.getLogger(__name__+str(self.name).replace('/','.'))
        self.name = Path(self.name)
        if self.root == None:
            self.cache = None
            self.children = []
        else:
            self.root.children.append(self.name)
    

    def depend(self, name, make_class, *args, **kwargs):
        self.deps[name] = make_class(*args, root=self, name=self.name/name, **kwargs)


    def calculate_hash(self, hash):
        ''' The Make object has an associated sha256 hash that represents its 'state'.
            If that hash is the same as the cached hash then the build is skipped.
            After the build executes the hash is re-calculated and stored in the cache.

            Anything that could influence the outcome of this job needs to be included in the hash.

            Remember to sort things because the hash order is important.
        '''
        hash(self.deps)


    async def execute(self):
        ''' Find all of the Make objects in the deps and ensure them
        '''
        self.noop = True
        self.log.debug(f'Execute {self.name}')
        async def _find(item):
            if isinstance(item, Make): await item.ensure(self._deep_force)
            elif isinstance(item, (list, tuple)):
                for i in item: await _find(i)
            elif isinstance(item, dict):
                for i in item.values(): await _find(i)
        await _find(self.deps)


    def cleanup(self):
        if self.root: return
    # Remove old keys
        valid = self.children + [self.name]
        for k in list(self.cache.keys()):
            if Path(k).parent in valid: continue
            del self.cache[k]
            

    async def ensure(self, force=False):
        ''' Use a hash to determine if execute() needs to be run or not.

        Parameters:
            force
                Force execute() to run even if the hash was unchanged.

        Returns:
            True if skipped, False if executed.
        '''
        self._deep_force = force
    # If we have already executed then leave like nothing happened
        if hasattr(self, 'noop'):
            #LOG self.log(f'Skipping {self.name} : already executed (noop)', tags=['make.skip'])
            return True
    # Check to see if we need to rebuild
        try:
            assert(not force), 'forced'
        # Use a hasher to calculate the hash
            h = Hasher(self)
            self.calculate_hash(h)
            assert(h.digest() == self['digest']), 'hash mismatch'
        # The hash is unchanged.  cleanup() still gets called
            #LOG self.log(f"Skipping {self.name} : unchanged", tags=['make.skip'])
            self.cleanup()
            return True
    # We need to rebuild
        except AssertionError as e:
            #LOG self.log(f"Rebuilding {self.name} : {e}", tags=['make.build'])
            pass
    # Remove the data from the previous build
        for path in self['data_paths'] or []: del self[path]
    # Execute and save the new data
        data = await self.execute() or {}
        for k, v in data.items(): self[k] = v
        self['data_paths'] = [str(self.name/k) for k in data.keys()]
    # Calculate the new hash (it shouldn't throw any errors this time around)
        h = Hasher(self)
        self.calculate_hash(h)
        self['digest'] = h.digest()
    # Run the cleanup
        self.cleanup()
    # Save only if we are the root Make object
        if self.root == None:
            self.save()


    def __getitem__(self, path):
        return self.get_cache().get(str(self.name / path))

    def __setitem__(self, path, value):
        self.get_cache()[str(self.name / path)] = value

    def __delitem__(self, path):
        del self.get_cache()[str(self.name / path)]


    def each_cache(self, pattern):
        pattern = re.compile(pattern)
        for k, v in self.get_cache().items():
            if pattern.match(str(Path(k))): yield k, v

    
    def get_cache(self):
        if self.root: return self.root.get_cache()
        if not self.cache:
            try:
                with open(self.cache_path, 'rb') as f:
                    self.cache = pickle.load(f)
            except:
                self.cache = {}
        return self.cache

    
    def save(self):
        if not hasattr(self, 'cache_path'): return
        with open(self.cache_path, 'wb') as f:
            pickle.dump(self.cache, f)
