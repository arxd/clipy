import logging, json
from cli import ConfigVar
from aiohttp import web


class Server():
    protocol = ConfigVar('server_protocol The first of the websocket protocols', default='v0')

    def __init__(self, *, auth=None):
        self.app = web.Application()
        self.app.router.add_get('/ws', self.handler)
        self.log = logging.getLogger('ws')
        self.auth = auth


    async def handler(self, req):
        if "Upgrade" not in req.headers: raise web.HTTPNotFound()
        sec = [x.strip() for x in req.headers.get('Sec-WebSocket-Protocol','').split(',', 1)]
        if len(sec) != 2 or sec[0] != Server.protocol.v:
            self.log(f"Bad Sec-WebSocket-Protocol: {len(sec)}!=2 or {sec[0]}!={Server.protocol.v}", tags=['ws','error'])
            raise web.HTTPBadRequest()
        user = self.auth.token_to_user(sec[1]) if self.auth else None
        if self.auth and not user:
            self.log(f"Unauthorized: {sec[1]}", tags=['ws','error'])
            raise web.HTTPBadRequest()
    # We have a user so prepare and listen for messages
        ws = web.WebSocketResponse(max_msg_size=4*1024, protocols=(sec[0],))
        await ws.prepare(req)
        await ws.send_str(json.dumps(dict(cmd='user', user=user and user.client_info())))
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                self.log(f"{user}: msg: {msg.data}", tags=['ws'])
                #await ws.send_str(f"Echo: {msg.data}")
            elif msg.type == web.WSMsgType.BINARY:
                self.log(f"{user}: binary: {len(msg.data)}", tags=['ws'])
            elif msg.type == web.WSMsgType.ERROR:
                self.log(f"{user}: error: {ws.exception()}", tags=['ws','error'])

        self.log(f"{user}: closed", tags=['ws'])
        return ws


    def run(self, host='localhost', port=9001):
        web.run_app(self.app, host=host, port=port)
        