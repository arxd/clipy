import os
from pathlib import Path
from .sys_tool import SysTool
from cli import ConfigVar


class Server():
    def __init__(self, *, nginx, **kwargs):
        kw = dict(no_cache=True, port=nginx.port, cert='cert', locs=[], proxy_intercept_errors=True, error_codes=[404, 500, 502, 503, 504], root=None)
        kw['server'] = [
            'rewrite ^(.*)/$ $1/index.html last', # rewrite trailing slashes to index.html
        ]
        kw.update(kwargs)
        if kw['port'] == 80 and kw['cert']: kw['port'] = 443
        for k,v in kw.items(): setattr(self, k, v)
        if self.cert:
            from .openssl import OpenSSL
            OpenSSL().ensure_server_cert(nginx.prefix/self.cert)


    def loc(self, *loc, ws=False):
        if ws: loc = [*loc, 'proxy_http_version 1.1', 'proxy_set_header Upgrade $http_upgrade', 'proxy_set_header Connection "upgrade"']
        self.locs.append(list(loc))


    def proxy(self, loc, upstream='default_upstream'):
        self.locs.append([loc, 
            f'proxy_pass http://{upstream}/',
            'proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for',
            'proxy_set_header X-Forwarded-Proto $scheme',
            'proxy_set_header Host $http_host',
            'proxy_redirect off',
        ])


    def proxy_cache(self, loc, host, zone='default_zone', lines=[]):
        self.locs.append([loc,
            f'proxy_pass https://{host}/',
            'proxy_ssl_server_name on', # So that nginx passes SNI host upstream
            f'proxy_set_header Host {host}', # So upstream sees the correct host
            'proxy_hide_header Access-Control-Allow-Origin', # so we can override it
            f'add_header Access-Control-Allow-Origin "https://{self.name}" always', # fonts are always loaded cross-origin by the browser
            f'proxy_cache {zone}', # The zone to cache files in
            'proxy_cache_valid 200 302 30d', # status-codes 200 and 302 should be cached for 30 days
            'proxy_cache_use_stale updating error timeout invalid_header', # If the upstream is having a problem then it is ok to serve a stale file
            'proxy_cache_revalidate on', # Simple revalidation from the upstream when the cached file expires (avoid redownloading)
            'proxy_cache_lock on', # Prevent race condition if two clients try to download an upstream file at the same time
            #expires 30d;
            #add_header Cache-Control "public, no-transform";
        ]+lines)


    def config(self):
        yield f'listen {self.port}' + ' ssl'*bool(self.cert)
        yield f'server_name {self.name}'
        if self.cert: yield from [f'ssl_certificate {self.cert}.pem', f'ssl_certificate_key {self.cert}-key.pem']
        if self.root: yield f'root {self.root}'
        if self.proxy_intercept_errors: yield 'proxy_intercept_errors on'
        if self.no_cache: yield from [
            'open_file_cache off',
            'add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" always',
            'add_header Pragma "no-cache" always',
            'add_header Expires "0" always',
        ]
        yield from self.server
    # Error codes
        for code in self.error_codes:
            yield f'error_page {code} = @error_{code}'
            yield (f'location @error_{code}', ['default_type text/plain', f'return {code} "{code}"'])
    # Locations
        for loc in self.locs:
            yield (f'location {loc[0]}', list(loc[1:]))
        


class Nginx(SysTool):

    version_probe = (lambda s: (s.cmd.v, '-v')), r'^.*nginx/(?P<v0>\d+)\.(?P<v1>\d+)\.(?P<v2>\d+).*$'
    cmd = ConfigVar('nginx_path The path to the nginx executable', default='nginx')
    version = ConfigVar('nginx_version The required version of nginx', default='1.29')
    prefix = ConfigVar('nginx_prefix The base directory for nginx files (config, logs, etc.)', default='local/nginx')
                       
    @classmethod
    def install_help_generic(self):
        return ['$ brew install nginx']


    def __init__(self, **kwargs):
        self.cfg = dict(workers=1, port=8080, servers={}, no_cache=True, http=[], upstreams={}, max_body_size='128k')
        self.cfg.update(kwargs)
        self.prefix = Path(Nginx.prefix.v)
        self.prefix.mkdir(parents=True, exist_ok=True)
        if not (self.prefix/'mime.types').exists():
            import urllib.request
            urllib.request.urlretrieve('https://raw.githubusercontent.com/nginx/nginx/master/conf/mime.types', self.prefix/'mime.types')
        self.http += [
            "log_format dev '[$status] $upstream_response_time $http_host $request'",
            f'access_log {self.prefix}/nginx.log dev',
            'sendfile on',
            'keepalive_timeout 5',
            'proxy_read_timeout 3600',
            f'client_max_body_size {self.max_body_size}',
            'include mime.types',
            'server_names_hash_bucket_size 64',
        ] + [f'{x}_temp_path {self.prefix}' for x in ['client_body', 'proxy', 'fastcgi','uwsgi','scgi']]


    def proxy_cache_path(self, path=None, zone='default_zone'):
        path = path or self.prefix/'proxy_cache'
        path.mkdir(parents=True, exist_ok=True)
        self.http += [f'proxy_cache_path {path} levels=1:2 keys_zone={zone}:10m max_size=1g inactive=30d use_temp_path=off']


    def __getattr__(self, k):
        return self.cfg[k]


    def http_to_https(self):
        if self.port != 80: return None
        return self.server(name='_', port=80, cert=None, no_cache=False, server=['return 301 https://$host$request_uri'])


    def server(self, **kwargs):
        d = Server(nginx=self, **kwargs)
        self.servers[d.name] = d
        return d


    def upstream(self, *hosts, name='default_upstream', hash=None):
        if hash == 'user': hash = 'hash $http_authorization consistent'
        self.upstreams[name] = [hash]*bool(hash) + [f'server {host}' for host in hosts]


    def config(self):
        for name,hosts in self.upstreams.items(): self.http.append((f'upstream {name}', list(hosts)))
        for d in self.servers.values(): self.http.append(('server', list(d.config())))
        cfg = [
            f'daemon off',
            f'worker_processes {self.workers}',
            f'pid {self.prefix}/nginx.pid',
            ('events', [
                'worker_connections 1024',
                'accept_mutex ' + ('on' if self.workers > 1 else 'off'),
            ]),
            ('http', self.http),
        ]

        def config_lines(x, depth=0):
            for l in x:
                if isinstance(l, tuple):
                    yield ' '*4*depth + l[0] + ' {\n'
                    yield from config_lines(l[1], depth+1)
                    yield ' '*4*depth + '}\n'
                else:
                    yield ' '*4*depth + l + ';\n'
        with open(self.prefix/'nginx.conf', 'w') as f:
            f.write(''.join(config_lines(cfg)))
    

    def run(self):
        return self.exec('-c', self.prefix/'nginx.conf', '-p', Path.cwd(), '-e', 'stderr')
