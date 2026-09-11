import copy, json
from pathlib import Path
from .sys_tool import SysTool
from cli import ConfigVar

class EObj():
    sub_list = None
    defaults = {}
    args = []

    def __init__(self, *args, use_this_data=None, **kwargs):
        if use_this_data != None:
            self._d = use_this_data
        else:
            self._d = copy.deepcopy(self.defaults)
            a = dict(zip(self.args, args))
            if len(a) != len(args): raise ValueError(f"{self.__class__.__name__} only takes {len(self.args)} positional arguments")
            self._d.update(a)
            self._d.update(kwargs)
            self.clean()

    def __deepcopy__(self, memo):
        return self.__class__(use_this_data = {k:copy.deepcopy(v,memo) for k,v in self._d.items()})

    def update(self, obj):
        self._d = obj._d if isinstance(obj, EObj) else obj

    def clean(self):
        pass

    def __getitem__(self, item):
        return self.get(item)

    #def __reduce_ex__(self, protocol):
    #    return self.to_json()

    def _get(self, key, or_else=None):
        return self._d[key] if key in self._d else self.get(self.sub_list)._get(key, or_else) if self.sub_list else or_else

    def get(self, item, or_else=None):
        parts = str(item).split('.',1)
        obj = self._get(parts[0], or_else)
        return obj if obj == None or len(parts) == 1 else obj.get(parts[1])

    def append(self, item):
        (self.get(self.sub_list) if self.sub_list else self)._d.append(item)

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, attr, val):
        if attr in {'_d'}: return super().__setattr__(attr, val)
        self._d[attr] = val

    def to_json(self):
        return self._d
        
    def __repr__(self):
        def serialize(obj):
            return obj.to_json()
            #if hasattr(obj, 'to_json'):
            #    return obj.to_json()
            #raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')
        return json.dumps(self, default=serialize)



class EList(EObj):
    def __init__(self, *items, use_this_data=None):
        self._d = list(items) if use_this_data==None else use_this_data

    def __deepcopy__(self, memo):
        return self.__class__(use_this_data = [copy.deepcopy(v,memo) for v in self._d])

    def _get(self, index, or_else=None):
        try:
            i = int(index)
        except ValueError:
            i = [i for i,v in enumerate(self._d) if index == v.name]
            assert(len(i) < 2), f"Duplicate names: {index}"
            if not i: return or_else
            i = i[0]
        try:
            return self._d[i]
        except:
            return or_else



class Address(EObj):
    defaults = dict(addr_port=':0')
    args = ['addr_port']

    def clean(self):
        addr,port = self.addr_port.split(':')
        self._d.setdefault('address', addr or '0.0.0.0')
        self._d.setdefault('port', port or 0)
        self._d['port'] = int(self.port)

    def to_json(self):
        return dict(socket_address = dict(address=self.address, port_value=self.port))



class EType(EObj):
    args = ['name', 'kind']

    def to_json(self):
        cfg = {'@type':self.kind}
        cfg.update({k:v for k,v in self._d.items() if k not in {'kind','name'}})
        return dict(name=self.name, typed_config=cfg)



class Certificate(EObj):
    args = ['prefix']
    def to_json(self):
        return dict(certificate_chain=dict(filename=f'{self.prefix}.pem'), private_key=dict(filename=f'{self.prefix}-key.pem'))



class FilterChain(EObj):
    defaults = dict(
        filters=EList(), 
        filter_chain_match=EObj(), 
        transport_socket=EType('envoy.transport_sockets.tls','type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext',
            #session_timeout = 35,
            common_tls_context=EObj(
                tls_params = EObj(),
                tls_certificates = EList(),
                alpn_protocols=['h2','http/1.1'],
            )
        )
    )
    sub_list = 'filters'



class FilterChains(EList):
    list_type = FilterChain



class Listener(EObj):
    sub_list = 'filter_chains'
    defaults = dict(
        address=Address(),
        filter_chains=FilterChains(),
        listener_filters=EList(
            # Uncomment if Envoy is behind a load balancer that exposes client IP address using the PROXY protocol.
            # EType(type.googleapis.com/envoy.extensions.filters.listener.proxy_protocol.v3.ProxyProtocol'),
            EType('tls', 'type.googleapis.com/envoy.extensions.filters.listener.tls_inspector.v3.TlsInspector'),
        ),
        # Best practices https://www.envoyproxy.io/docs/envoy/latest/configuration/best_practices/edge
        per_connection_buffer_limit_bytes=32768,
    )



class Cluster(EObj):
    defaults = dict(
        typed_extension_protocol_options = {
            'envoy.extensions.upstreams.http.v3.HttpProtocolOptions': {
                '@type': 'type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions',
                'upstream_http_protocol_options': {},
                'common_http_protocol_options': {},
                'explicit_http_config': {
                    'http2_protocol_options': {
                        'max_concurrent_streams': 3000,
                    }
                }
            }
        },
        load_assignment = EObj(endpoints=EList(EObj(lb_endpoints=EList()))),
        connect_timeout = '3.00s',
        type = 'STATIC',
        lb_policy = 'LEAST_REQUEST',
        #transport_socket = EObj(),
        # Best practices https://www.envoyproxy.io/docs/envoy/latest/configuration/best_practices/edge
        per_connection_buffer_limit_bytes=32700,
    )
    args = ['name']

    def clean(self):
        self.load_assignment.cluster_name = self.name



class Route(EObj):
    def to_json(self):
        match = self.match or EObj(**{k:v for k,v in self._d.items() if k in {'prefix','path','safe_regex','path_separated_prefix'}})
        route = self.route or EObj(**{k:v for k,v in self._d.items() if k in {'cluster','prefix_rewrite','timeout','idle_timeout'}})
        return EObj(match=match, route=route)


class Envoy(SysTool):

    sub_commands = []
    version_probe = r'^envoy\s+version.*?/(?P<v0>\d+)\.(?P<v1>\d+)\.(?P<v2>\d+)/.*$'
    cmd = ConfigVar('envoy_path The path to the envoy executable', default='envoy')
    version = ConfigVar('envoy_version The desired version for envoy', default='1.30')
    config = ConfigVar('envoy_config The location of the envoy config file', default='local/envoy/config.json')        
                       
    @classmethod
    def install_help_generic(self):
        return ['https://www.envoyproxy.io/docs/envoy/latest/start/install', '$ brew install envoy']


    def __init__(self, **kwargs):
        listeners = type('Listeners', (EList,), {'list_type':Listener})()
        self.cfg = EObj(static_resources=EObj(listeners = listeners, clusters = EList()))
        self.cfg.overload_manager = EObj(
            refresh_interval = '0.25s',
            resource_monitors = EList(
                EType('heap', 'type.googleapis.com/envoy.extensions.resource_monitors.fixed_heap.v3.FixedHeapConfig',
                    max_heap_size_bytes=2**27,
                ),
            ),
            actions = EList(
                EObj(name='envoy.overload_actions.shrink_heap', triggers=EList(EObj(name='heap', threshold=EObj(value=0.80)))),
                EObj(name='envoy.overload_actions.stop_accepting_requests', triggers=EList(EObj(name='heap', threshold=EObj(value=0.98)))),
            )
        )


    def enable_admin(self, port=8001):
        self.cfg.admin = EObj(
            address = Address(f'127.0.0.1:{port}'),
        )
        

    def ensure(self, path):
        parts = path.split('.')
        obj = self.cfg
        for i, fld in enumerate(parts):
            if obj[fld] != None:
                obj = obj[fld]
            else:
                list_type = obj.get(obj.sub_list).list_type if obj.sub_list else obj.list_type
                try:
                    int(fld)
                    obj.append(list_type())
                except ValueError:
                    obj.append(list_type(name=fld))
                obj = obj[fld]
        return obj


    def listen(self, address, id=0):
        if not isinstance(address, Address): address = Address(address)
        lsr = self.ensure(f'static_resources.listeners.{id}')
        lsr.address = address


    def route(self, *args, listener_chain_filter='0.0.0', vhost='default_vhost', **kwargs):
        vhost = self.cfg.static_resources.listeners[listener_chain_filter].route_config.virtual_hosts[vhost]
        vhost.routes.append(Route(*args, **kwargs))


    def http(self, name='ingress_http', listener_chain='0.0', hostname='*'):
        chain = self.ensure(f'static_resources.listeners.{listener_chain}')
        obj = EType(name, 'type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager',
            stat_prefix = name,
            codec_type = 'auto',
            http_filters = EList(
                EType('envoy.filters.http.router','type.googleapis.com/envoy.extensions.filters.http.router.v3.Router'),
            ),
            access_log = EList(EType('asdf', 'type.googleapis.com/envoy.extensions.access_loggers.stream.v3.StdoutAccessLog')),
            route_config = EObj(
                name='default_routes',
                ignore_path_parameters_in_path_matching=True,
                virtual_hosts=EList(
                    EObj(name='default_vhost', require_tls='EXTERNAL_ONLY', domains=[hostname], routes=EList()),
                ),
            ),
            #request_id_extension = ,
            # Best practices https://www.envoyproxy.io/docs/envoy/latest/configuration/best_practices/edge
            stream_idle_timeout = '300s', # 5 mins, must be disabled for long-lived and streaming requests
            request_timeout = '300s', # 5 mins, must be disabled for long-lived and streaming requests
            use_remote_address = True,
            merge_slashes = True,
            normalize_path = True,
            path_with_escaped_slashes_action = 'UNESCAPE_AND_REDIRECT',
            common_http_protocol_options = EObj(
                idle_timeout = '3600s',
                headers_with_underscores_action = 'REJECT_REQUEST',
            ),
            http2_protocol_options=EObj(
                max_concurrent_streams=100,
                initial_stream_window_size=65535,
                initial_connection_window_size=1048576,
            ), 
        )
        chain.append(obj)
        return obj


    def add_certificate(self, prefix, listener_chain='0.0'):
        chain = self.ensure(f'static_resources.listeners.{listener_chain}')
        chain.transport_socket.common_tls_context.tls_certificates.append(Certificate(prefix))


    def add_cluster(self, *args, **kwargs):
        self.cfg.static_resources.clusters.append(Cluster(*args, **kwargs))


    def add_endpoint(self, endpoint, cluster_name='0'):
        if isinstance(endpoint, Address):
            endpoint = EObj(endpoint=EObj(address=endpoint))
        self.cfg.static_resources.clusters[cluster_name].load_assignment.endpoints[0].lb_endpoints.append(endpoint)


    def save(self):
        path = Path(Envoy.config.v)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            cfg_obj = json.loads(repr(self.cfg))
            if path.suffix == '.json':
                json.dump(cfg_obj, f, indent=4)
            else:
                raise ValueError(f"Can't save config: {path}")


    def check_config(self):
        self.save()
        self('-c', Envoy.config.v, '--mode', 'validate')


    def run(self):
        self.save()
        self('-c', Envoy.config.v)
