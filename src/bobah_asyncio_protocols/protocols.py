import asyncio
import base64

from . import aclassmethod, ip_to_bytes, get_ip_by_hostname


class BaseProxyProtocol(asyncio.protocols.Protocol):
    __slots__ = ("_username", "_password", "_transport", "_connected")

    _username: str
    _password: str
    _transport: asyncio.transports.Transport
    _connected: asyncio.Event

    def __init__(self, username=None, password=None):
        super().__init__()

        self._username = username
        self._password = password
        self._connected = asyncio.Event()
    
    def get_transport(self):
        return self._transport
    
    def connection_made(self, transport: asyncio.transports.Transport):
        self._transport = transport
    
    @aclassmethod
    async def create_proxy_connection(cls, host, port, username=None, password=None):
        ioloop = asyncio.get_running_loop()
        if username and password:
            protocol_factory = lambda: cls(username, password)
        else:
            protocol_factory = cls
        _, protocol = await ioloop.create_connection(protocol_factory, host, port)
        return protocol
    
    async def connect(host, port):
        pass


class Socks4ProxyConnectionProtocol(BaseProxyProtocol):
    def connection_made(self, transport):
        super().connection_made(transport)
    
    def data_received(self, data):
        if data[0] == 0x00:
            self._connected.set()
        else:
            raise Exception()
    
    async def connect(host, port):
        ip = get_ip_by_hostname(host)
        ip_bytes = ip_to_bytes(ip)
        port = port.to_bytes(2, 'big')
        conn_str = b'\x04\x01' + port + ip_bytes + b'\x00'
        self._transport.write(conn_str)
        await self._connected.wait()


class Socks5ProxyConnectionProtocol(BaseProxyProtocol):
    __slots__ = ("_ip", "_port")
    def connection_made(self, transport):
        super().connection_made(transport)
    
    def data_received(self, data):
        if len(data) == 2 and data[0] == 0x05 and data[1] == 0x02 and self._username and self._password:
            auth_string = b"\x01"
            auth_string += len(self._username).to_bytes(1, "big") + self._username.encode()
            auth_string += len(self._password).to_bytes(1, "big") + self._password.encode()
            self._transport.write(auth_string)
        elif len(data) == 2 and data[0] == 0x05 and data[1] == 0x00:
            conn_str = b'\x05\x01\x00\x01' + self._ip + self._port
            self._transport.write(conn_str)
        elif len(data) == 10 and data[0] == 0x05 and data[1] == 0x00 and data[3] == 0x01:
            self._connected.set()
        else:
            raise Exception()
    
    async def connect(host, port):
        ip = await get_ip_by_hostname(host)
        self._ip = ip_to_bytes(ip)
        self._port = port.to_bytes(2, 'big')

        conn_str = b"\x05"
        if self._username and self._password:
            conn_str += b'\x02\x00\x02'
        else:
            conn_str += b'\x01\x00'
        self._transport.write(conn_str)
        await self._connected.wait()
