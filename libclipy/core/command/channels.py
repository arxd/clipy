import os, io, struct, pickle

_NULL = object() # A sentenal for next_step to return if it doesn't have a value.  Parse returns this if it can't parse a value.

class Channel():
    def __init__(self, **kwargs):
        defaults = dict(fd=None, child_fd=None, done=False, buffer=bytearray(), b0=0, b1=0)
        defaults.update(kwargs)
        for k,v in defaults.items(): setattr(self, k, v)
        self._view = memoryview(self.buffer)


    def __repr__(self):
        args = [f'{k}={v!r}' for k, v in self.__dict__.items() if k not in ('buffer','_view')]
        args.append(f'data={self.data!r}')
        return f"{self.__class__.__name__}({','.join(args)})"


    def _ensure_space(self, amt):
    # Do we need more buffer bytes?
        size = self.b1 - self.b0
        if len(self.buffer) - size < amt:
            self._view.release()
            self.buffer.extend(b'\x00' * amt)
            self._view = memoryview(self.buffer)
    # Do we need to relocate to the front?
        if len(self.buffer) - self.b1 < amt:
            self._view[:size] = self._view[self.b0:self.b1]
            self.b0, self.b1 = 0, size


    def extend_data(self, data):
        size = len(data)
        self._ensure_space(size)
        self._view[self.b1:self.b1+size] = data
        self.b1 += size


    @property
    def data(self):
        return self._view[self.b0:self.b1].tobytes()

    
    def close(self):
        if self.done: return True
        self.done = True
        if self.fd is not None: os.close(self.fd)


    def close_child(self):
        if self.child_fd is not None and self.child_fd > 0: os.close(self.child_fd)



class Mem(Channel):
    ''' For passing data through memory to the child
    '''

    def __init__(self, *, data, **kwargs):
        super().__init__(**kwargs)
        data = pickle.dumps(data, protocol=5)
        self.size = len(data)  
    # Create functions shm_open() and shm_unlink()
        import ctypes, mmap
        libc = ctypes.CDLL(None, use_errno=True)
        shm_open = libc.shm_open
        shm_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_uint]
        shm_open.restype = ctypes.c_int
        shm_unlink = libc.shm_unlink
        shm_unlink.argtypes = [ctypes.c_char_p]
        shm_unlink.restype = ctypes.c_int
        def _assert(condition):
            if not condition:
                e = ctypes.get_errno()
                raise OSError(e, os.strerror(e))
    # Open a mem file
        self.child_fd = shm_open(b'/cli.py', os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600) # FIXME O_RD only?
        _assert(self.child_fd > 0)
        try:
            os.set_inheritable(self.child_fd, True)
        # Write the data
            os.ftruncate(self.child_fd, self.size)
            mm = mmap.mmap(self.child_fd, self.size)
            mm[:self.size] = data
            mm.close()
        finally:
            _assert(shm_unlink(b'/cli.py') == 0)



class Read(Channel):
    ''' These classes read data into an internal data buffer
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.fd: self.fileobj = io.FileIO(self.fd, mode='r', closefd=False)


    def read_some_data(self):
        self._ensure_space(4096)
        got = self.fileobj.readinto(self._view[self.b1:])
        self.b1 += got
        return got


    def close(self):
        if super().close(): return True
        if self.fd: self.fileobj.close()
        



class ReadGen(Read):
    ''' These classes try to parse the data and return objects
    '''
    def parse(self):
        return _NULL # Just accumulate the data



class ReadView(ReadGen):
    ''' Like ReadBin but returns a memory view of the buffer so you have to be more careful
    '''



class ReadBin(ReadGen):
    ''' Returns binary data as soon as it is available
    '''
    def parse(self):
        if not (data := self.data): return _NULL
        self.b0 = self.b1
        return data



class ReadLine(ReadGen):
    ''' Returns utf8 encoded lines (with the trailing \n)
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.i0 = 0

    def parse(self):
        try:
            i = self.buffer.index(10, self.b0+self.i0, self.b1)
        except ValueError:
        # No newline in the data
            self.i0 = self.b1 - self.b0
            if not self.done: return _NULL # Don't send an incomplete line until the end
            if self.done and self.i0 == 0: return _NULL # Nothing more to send
        # Send the remaining data that we have
            line = self.data.decode('utf8')
            self.b0 = self.b1
            return line
        # There is a newline at `i`
        line = self._view[self.b0:i+1].tobytes().decode('utf8')
        self.b0 = i+1
        self.i0 = 0
        return line



PICKLE_HDR = struct.Struct('!I')

class ReadPickle(ReadGen):
    ''' Returns pickled objects
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = None

    def parse(self):
        size = self.b1-self.b0
        if self.done and 0 < size < (self.size or PICKLE_HDR.size):
            raise ValueError(f"Truncated output: {self.data!r}")
    # Read the header size
        if self.size is None and size >= PICKLE_HDR.size:
            self.size = PICKLE_HDR.unpack(self._view[self.b0:self.b0+PICKLE_HDR.size])[0]
            self.b0 += PICKLE_HDR.size
            return self.parse()
    # Read the body
        if self.size is not None and size >= self.size:
            item = pickle.loads(self._view[self.b0:self.b0+self.size])
            self.b0 += self.size
            self.size = None
            return item
        return _NULL



class Write(Channel):
  
    def send(self, data):
        if data is None:
            self.done = True
        elif self.done: raise ValueError(f"Writing data to closed pipe: {data!r}")
        if isinstance(data, str): data = data.encode('utf8')
        self.data += data


    def write(self):
        if not self.data: return
        try:
            self.data = self.data[os.write(self.fd, self.data):]  # FIXME: The subprocess might have closed while we still are trying t osend stuff
        except BlockingIOError: 
            pass

    # def close()  FIXME Think about how close interacts with send(None)