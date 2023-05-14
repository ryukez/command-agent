import abc
from typing import Any
from commands.command import Command
from commands.resolver import CommandResolver
from langchain.llms.base import BaseLLM


class CompositeCommand(Command):
    @abc.abstractclassmethod
    def from_json(cls, data: Any, command_llm: BaseLLM, command_resolver: CommandResolver) -> "CompositeCommand":
        """
        @param data: data to deserialize (json object)
        @param command_llm: LLM to be used for command execution
        @param command_resolver: command resolver to find commands
        @return: deserialized command
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def to_json(self) -> Any:
        """
        @return: serialized command (json object)
        """
        raise NotImplementedError()
