import asyncio

class Singleton(type):
    def __call__(self, *args, **kwargs):
        key, cls = self.dedup_key(*args, **kwargs)
        if cls is None: return super().__call__(*args, **kwargs)
        try:
            return cls.instances[key]
        except KeyError:
            obj = super().__call__(*args, **kwargs)
            cls.instances[key] = obj
            return obj



class Port():
    ''' This sets the type, direction, multiplicty of a port in a Node
    '''

class Input(Port):
    ''' An input-only port
    '''

class Output(Port):
    ''' An output-only port
    '''

class Node():
    ''' Basic graph-based methods
    '''
    def __init__(self):
        self.ports = {}

    def graphviz_node(self):
        return []#f'n_{id(self)} [shape=record, label="{ {<in1> A|<in2> B|<in3> C|<in4> D} | AND | <out> Out }"']

    def graphviz_edges(self):
        #for name, port in self.
        return []#f'n_{id(self)} -> f'


class Resource(metaclass=Singleton):
    ''' A resource is something fairly unique or scarce.

    Examples:
        * Database
        * Folder containing files
        * Program executable
        * Server
        * User account on a linux machine
        * The amount of free RAM

    Resources can be in a certain state:
        * Server running
        * Folder empty
        * Program executable built and up-to-date
        * User account created and in the 'video' group

    Resources issue condition objects.
    A condition is a read-only object that defines a desired state of a resource.
    A condition can then be 'ensured' so that the resource is in the desired state.

    Some conditions might directly conflict with other conditions.
    That is fine, as long as the two don't need to be ensured simultaneously.

    A resource can also manage sub-resources.  For example, you might get file resources from a folder resource.
    The folder resource could then have higher-level conditions such as ensuring that old, irrelevant files are deleted.
    '''


class Condition():
    ''' This is an abstract desired state or condition to be met.

    Examples:
        * A library/executable is built and up-to-date
        * A server is running correctly.
        * Necessary system packages are available
    
    The condition normally referrs to the states of one or more Resources.
    However, it also may be derived entirely from other Conditions.
    '''





class Resolver():
    ''' This is an action that can be taken.

    In order for a resource to be brought into the correct state, as required by conditions, a resolver is used.
    The resolver is code that does whatever is needed to bring the current state to the required state.

    A resolver action may operate on more than one resource and therefore affect more than one condition at a time.

    A condition may be able to supply the correct resolver to satisfy itself, or maybe more complicated logic is needed to discover the needed resolver.

    A resolver may depend on certain conditions/resources before it can be executed.
    For example, before a source file can be turned into an object file by a compiiler, we need to ensure that the correct compiler and supporting libraries exist.
    '''
    
    def __getattr__(self, attr):
        if attr not in self.deps: raise AttributeError(f"{attr!r} is not in deps")
        return self.deps[attr]
        



class DepGraph():
    ''' Collect Resources, Conditions and Resolvers into a dependancy graph.

    The ultimate goal is to build a DAG of resolvers that, when executed, fully resolve all conditions.
    '''


class SysToolRsc(Resource):
    ''' This is a system tool from libclipy.tools
    '''
    def __init__(self, tool, *args):
        self.tool = tool
        self.args = args
