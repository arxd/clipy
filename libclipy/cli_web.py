from cli import Command, Venv, ConfigVar

hostname = ConfigVar('Nginx.hostname The default hostname to use when one is not given in a server() declaration', default='')

@Command()
def nginx(hostname='', *, tls=False):
    ''' Run nginx

    Parameters:
        <str> --hostname <str> | <socket.gethostname>:8080
            Which hostname:port to listen to.  Examples:  localhost:8080  _:80
        --tls
            Run with
        --hostname
            Which hostname should the server{} block be tied to?
    '''
    import socket
    from libclipy.tools.nginx import Nginx
    name, port = (*hostname.split(':'), '8080')[:2]
    if not name: name = '_'
    nginx = Nginx()
    #if tls: nginx.http_to_https()
    server = nginx.server(name=name, port=port, cert=tls, root='web')
    server.proxy_cache('/font/', 'fonts.gstatic.com')
    server.proxy_cache('/esm/', 'esm.sh')
    server.loc('/ws', 'proxy_pass http://127.0.0.1:8001', ws=True)
    server.loc('/', 'try_files $uri /index.html')
    nginx.config()
    print(f"http{'s'*tls}://{name}"+f":{nginx.port}"*(nginx.port!=80))
    return nginx.run().exec()



@Venv('cli::main', req='aiohttp')
@Command()
def server():
    ''' Run the websocket server
    '''
    from .web.ws import Server
    Server().run(port=8001)
