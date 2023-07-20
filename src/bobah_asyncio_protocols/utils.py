import asyncio
import socket

import aiodns


class aclassmethod(object):
    __slots__ = ("__method")
    def __init__(self, method):
        self.__method = method

    def __get__(self, instance, cls):
        async def wrapper(*args, **kwargs):
            return await self.__method(cls, *args, **kwargs)
        return wrapper


async def get_ip_by_hostname(hostname):
    if hostname.replace(".", "").isdigit():
        return hostname
    loop = asyncio.get_running_loop()
    resolver = aiodns.DNSResolver(loop=loop)
    host = await resolver.gethostbyname(hostname, socket.AF_INET)
    host = host.addresses[0]
    return host


def ip_to_bytes(ip):
    bytes_ip = b""
    for n in ip.split("."):
        bytes_ip += int(n).to_bytes(1, "big")
    return bytes_ip
