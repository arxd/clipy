'''
A graph of dependencies


Separate the 'what' from the 'how'.
What: I want a user named 'app' on the linux server.
How:  Use useradd to add a user.

So we start with a declarative list of all our 'what's and then make sure each 'what' has a supporting 'how'.
It would also be preferable if we could measure success.  Did we achieve our 'what'?  If it has already been achieved then we don't need the 'how'.


co-operation between dependency nodes.
If two deps need a shared resource (IAP tunnel) then it would be efficient to create that resource once and share it between everyone who needs it (if it is shareable) before releasing, rather than creating it and releasing it individually for everyone who needs it.

We also want to group nodes.  For example, a clean-up process might want to know all the files that will be created in a location by a depgraph so that it can remove everything else.

A pool of objects, such as a GCP collection of subnets could be a single node.  Each resource (subnet) of that pool would also be a node.
The pool node would then depend on each of the individual resource nodes of its type.
That would let it remove any stale resources in its jurisdiction after all of its inputs had stabilized.

We should be able to build a literal graph (graphviz)




'''

import asyncio


class VariableListener():
    DONE = object()

    def __init__(self, v):
        self.vs = []
        self.changed = asyncio.Event()
        if hasattr(v,'v'): self.set(v.v, True)

    def set(self, v, done):
        self.vs.append(v)
        if done: self.vs.append(VariableListener.DONE)
        self.changed.set()
        self.changed.clear()

    async def __anext__(self):
        if not self.vs: await self.changed.wait()
        v = self.vs.pop(0)
        if v is VariableListener.DONE: raise StopAsyncIteration
        return v


class Variable():
    ''' A Variable has a (possibly) changing value until it settles on a final value.

    You can follow the value with an async generator, or just wait for the final value.
    '''
    def __init__(self):
        self._listeners = set()

    def set(self, v, *, done=False):
        for l in self._listeners: l.set(v, done)
        if done:
            if self.hasattr('v'): raise ValueError(f"This Variable has already settled to {self.v!r}")
            self.v = v

    async def wait(self):
        async for x in self: pass
        return x
    
    def __aiter__(self):
        client = VariableListener(self)
        self._listeners.add(client)
        return client

    



async def test():

    async for x in value():
        x.use()



class DepNode():
    ''' A node in the dependency graph.

    A `Dep` has zero or more child `Dep` dependencies.
    It has a current state, and a target state.
    The node actively tries to move to its target state.

    The dependencies may change dynamically as the node moves through different states.
    For example, when it enters a 'building' state it might depend on new nodes (such as a compiler), which might not be needed otherwise.

    The node may take more or less paranoid actions to get to the final state with an equivalent speed trade-off.
    For example, it might use a cached value if it can for speed, or it could recreate everything and double-check outputs when being extra paranoid.

    See `PureFn` for the simplest concrete example.
    '''
    def __init__(self):
        self.state = None


class PureFn():
    ''' This is a dependency node that wraps an *pure* function (async or otherwise).

    This means that as long as the input values don't change, the output won't change, even on repeated calls (with the same inputs).
    Note that side-effects (like file creation) are considered outputs.

    The node has inputs which may be constants (set during __init__) or variables (outputs from other DepNodes).
    The node has has output python values and side-effects.

    It has the option to cache its output if that would give a beneficial speed up.

    .. mermaid::

        stateDiagram-v2
        
        None --> DISCOVER
        DISCOVER --> IDENTITY

    There are a few stable states (aside from the initial ``None`` state).
    The ``STABLE`` state means that all of the functions inputs are stable, meaning they are constants or they are in a ``STABLE`` state.
    Being in a ``STABLE`` state means that your node can have an identity (hash) that will not change.
    From the ``INIT`` state it may transition to ``HASH`` which is when it calculates its input and output hashes to determine if it is in a consistent state or not.
    When the hash checks complete it will move to ``VALID`` or ``INVALID`` depending on if the hashes match.
    Finally, it can move from ``INVALID``, through ``EVAL`` to ``VALID`` by evaluating its underlying function.
        
    '''
    def __init__(self, fn, cache, **kwargs):
        pass
        

class IAP(DepNode):
    ''' This is an open IAP tunnel to a VM instance
    '''
    def __init__(self):
        pass
