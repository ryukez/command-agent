import abc
from typing import Any


class Channel(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def send(self, message: str, data: Any = {}):
        """
        Send a message to the user.

        @param message: message to send
        @param data: data to send (json object)
        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def wait_reply(self, message: str, data: Any = {}) -> str:
        """
        Ask the user for reply.

        @param name: message to send
        @param data: data to send (json object)
        @return: user's response
        """
        raise NotImplementedError()
