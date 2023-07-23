import asyncio
import base64
import async_timeout

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
    
    def connection_lost(self, exc):
        if self._transport.get_protocol() is not self:
            return True
        else:
            self._transport.abort()
            self._connected.set()
    
    def eof_received(self):
        if self._transport.get_protocol() is not self:
            return True
        else:
            self._transport.abort()
            self._connected.set()
    
    def connection_made(self, transport: asyncio.transports.Transport):
        self._transport = transport
    
    @aclassmethod
    async def create_proxy_connection(cls, host, port, username=None, password=None, timeout=10):
        ioloop = asyncio.get_running_loop()
        if username and password:
            protocol_factory = lambda: cls(username, password)
        else:
            protocol_factory = cls
        async with async_timeout.timeout(timeout):
            _, protocol = await ioloop.create_connection(protocol_factory, host, port)
            return protocol
    
    async def connect(self, host, port):
        pass


class HttpProxyConnectionProtocol(BaseProxyProtocol):
    def data_received(self, data):
        if b"200" in data.split(b"\r\n")[0]:
            self._connected.set()
        else:
            self._transport.abort()
            self._connected.set()
    
    async def connect(self, host, port, timeout=10):
        try:
            async with async_timeout.timeout(timeout):
                host, port = host.encode(), str(port).encode()
                conn_str = b"CONNECT " + host + b":" + port + b" HTTP/1.1\r\nHost: " + host + b"\r\n\r\n"
                self._transport.write(conn_str)
                await self._connected.wait()
                if self._transport.is_closing():
                    raise Exception()
        except Exception as ex:
            self._transport.abort()
            raise ex


class Socks4ProxyConnectionProtocol(BaseProxyProtocol):
    def data_received(self, data):
        if data[0] == 0x00:
            self._connected.set()
        else:
            self._transport.abort()
            self._connected.set()
    
    async def connect(self, host, port, timeout=10):
        try:
            async with async_timeout.timeout(timeout):
                ip = await get_ip_by_hostname(host)
                ip_bytes = ip_to_bytes(ip)
                port = port.to_bytes(2, 'big')
                conn_str = b'\x04\x01' + port + ip_bytes + b'\x00'
                self._transport.write(conn_str)
                await self._connected.wait()
                if self._transport.is_closing():
                    raise Exception()
        except Exception as ex:
            self._transport.abort()
            raise ex


class Socks5ProxyConnectionProtocol(BaseProxyProtocol):
    __slots__ = ("_ip", "_port")
    
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
            self._transport.abort()
            self._connected.set()
    
    async def connect(self, host, port, timeout=10):
        try:
            async with async_timeout.timeout(timeout):
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
                if self._transport.is_closing():
                    raise Exception()
        except Exception as ex:
            self._transport.abort()
            raise ex
