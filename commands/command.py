import abc
from typing import Any, List, NamedTuple, Tuple
from commands.data_schema import (
    DataSchemaDict,
)
from channels.channel import Channel


class Command(metaclass=abc.ABCMeta):
    """
    A command is a reusable procedure that takes in some inputs and returns some outputs.

    @param human_check: whether the command requires human check
    @param additional_prompts: additional prompts for executing the command
    """

    human_check: bool
    additional_prompts: List[str] = []

    def __init__(
        self,
        human_check: bool = False,
    ):
        self.human_check = human_check

    @abc.abstractproperty
    def name(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def description(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def input_schema(self) -> DataSchemaDict:
        raise NotImplementedError()

    @abc.abstractproperty
    def output_schema(self) -> DataSchemaDict:
        raise NotImplementedError()

    @abc.abstractmethod
    async def _run(self, inputs: Any, channel: Channel) -> Tuple[Any, str]:
        """
        Run the command, validating the input and output based on the schema.

        @param inputs: input to the command (satisfies input_schema)
        @param channel: channel to interact with the user
        @return: (output, error), where output satisfies output_schema
        """
        raise NotImplementedError()

    async def run(self, inputs: Any, channel: Channel) -> Tuple[Any, str]:
        """
        Run the command, validating the input and output based on the schema.
        """

        error = self.input_schema.validate(inputs)
        if error:
            return None, error

        if self.human_check:
            error = await channel.wait_check(self.name, inputs)
            if error:
                return None, error

        outputs, error = await self._run(inputs, channel)
        if error:
            return None, error

        error = self.output_schema.validate(outputs)
        if error:
            return None, error

        return outputs, ""


class Variable(NamedTuple):
    name: str
    description: str
    value: Any


RETURN_COMMAND_NAME = "ReturnCommand"


class ReturnCommand(Command):
    name: str = RETURN_COMMAND_NAME
    description: str = "Finish the whole process. Use this command when you get the desired output."
    schema: DataSchemaDict

    def __init__(self, schema: DataSchemaDict, **kwargs):
        super().__init__(**kwargs)
        self.schema = schema

    @property
    def input_schema(self) -> DataSchemaDict:
        return self.schema

    @property
    def output_schema(self) -> DataSchemaDict:
        return self.schema

    async def _run(self, inputs: Any, channel: Channel) -> Tuple[Any, str]:
        return inputs, ""
