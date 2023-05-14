import abc
from typing import Optional
from commands.command import Command


class CommandResolver(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def resolve(self, command: str) -> Optional[Command]:
        """
        Resolve a command by name.

        @param command: command name
        @return: command object if found, otherwise None
        """
        raise NotImplementedError()
