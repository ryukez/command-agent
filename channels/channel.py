import abc
from typing import Any


class Channel(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def send(self, message_object: Any):
        """
        Send a message to the user.

        @param message_object: message to send (json object)
        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def wait_check(self, command: str, inputs: Any) -> str:
        """
        Ask the user to check the input.

        @param command: command name
        @param inputs: input to the command
        @return: error message if the input is rejected, otherwise empty string
        """
        raise NotImplementedError()
