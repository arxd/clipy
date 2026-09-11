from cli import Command, Venv

@Command()
def nginx():
    ''' Run nginx
    '''
    import socket
    from libclipy.tools.nginx import Nginx
    name = socket.gethostname()
    nginx = Nginx()
    nginx.proxy_cache_path()
    nginx.http_to_https()
    server = nginx.server(name=name, root='web')
    server.proxy_cache('/font/', 'fonts.gstatic.com')
    server.proxy_cache('/esm/', 'esm.sh')
    server.loc('/ws', 'proxy_pass http://127.0.0.1:8001', ws=True)
    server.loc('/', 'try_files $uri /index.html')
    nginx.config()
    print(f"https://{name}"+f":{nginx.port}"*(nginx.port!=80))
    return nginx.run()


import logging
log = logging.getLogger('bob')


@Venv(requirements='wcwidth aiohttp')
@Command()
def server():
    ''' Run the websocket server
    '''
    from .web.ws import Server
    Server().run(port=8001)


@Command()
def run_():
    ''' Run both nginx and the webserver
    '''
    

