from typing import Any, Dict, List, NamedTuple, Tuple, Union
from commands.command import RETURN_COMMAND_NAME, Command, ReturnCommand, Variable
from commands.composite import CompositeCommand

from commands.data_schema import (
    DataSchemaDict,
    DataSchemaField,
    DataSchemaScalar,
)
from commands.executor import CommandExecuter
from commands.resolver import CommandResolver
from langchain.llms.base import BaseLLM
from channels.channel import Channel


class CommandStep(NamedTuple):
    id: str
    command: str
    input_variables: List[str]


class SequentialCommandStepCommand(CompositeCommand):
    """
    A composite command consisting of a sequence of command executions.
    """

    name: str = ""
    description: str = ""
    input_variables: Dict[str, str]  # [name, description]
    output_variables: Dict[str, str]  # [name, description]
    steps: List[CommandStep]
    command_executor: CommandExecuter
    command_resolver: CommandResolver

    def __init__(
        self,
        name: str,
        description: str,
        input_variables: Dict[str, str],
        output_variables: Dict[str, str],
        steps: List[CommandStep],
        command_llm: BaseLLM,
        command_resolver: CommandResolver,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.name = name
        self.description = description
        self.input_variables = input_variables
        self.output_variables = output_variables
        self.steps = steps
        self.command_executor = CommandExecuter(command_llm)
        self.command_resolver = command_resolver

    @property
    def input_schema(self) -> DataSchemaDict:
        return DataSchemaDict(
            fields=[
                DataSchemaField(name=name, schema=DataSchemaScalar(description=description, python_type="str"))
                for (name, description) in self.input_variables.items()
            ]
        )

    @property
    def output_schema(self) -> DataSchemaDict:
        return DataSchemaDict(
            fields=[
                DataSchemaField(name=name, schema=DataSchemaScalar(description=description, python_type="str"))
                for (name, description) in self.output_variables.items()
            ]
        )

    def _resolve_command(self, command: str) -> Union[Command, None]:
        if command == RETURN_COMMAND_NAME:
            return ReturnCommand(self.output_schema)
        else:
            return self.command_resolver.resolve(command)

    def _step_summary(self, step: CommandStep, inputs: List[Variable], outputs: Any, error: str) -> Any:
        summary = {
            "step_id": step.id,
            "command": step.command,
            "inputs": {i.name: i.value for i in inputs},
        }

        if error == "":
            summary["outputs"] = outputs
        else:
            summary["error"] = error

        return summary

    async def _run(self, inputs: Any, channel: Channel) -> Tuple[Any, str]:
        variables: Dict[str, Variable] = {}
        for name, description in self.input_variables.items():
            variables[name] = Variable(name, description, inputs[name])

        for step in self.steps:
            command = self._resolve_command(step.command)
            if command is None:
                raise Exception(f"Command {step.command} not found")

            step_inputs = list(map(lambda v: variables[v], step.input_variables))

            outputs, error = await self.command_executor.execute(command, step_inputs, channel)
            if error != "":
                return None, error

            await channel.send(self._step_summary(step, step_inputs, outputs, error))

            variables[f"steps.{step.id}.output"] = Variable(
                f"steps.{step.id}.output",
                f"<result of {step.command}({ ', '.join(step.input_variables) })>",
                outputs,
            )

            if step.command == "ReturnCommand":
                return outputs, ""

        raise Exception("No ReturnCommand found in the steps")

    @classmethod
    def from_json(cls, data: Any, command_llm: BaseLLM, command_resolver: CommandResolver):
        return SequentialCommandStepCommand(
            name=data["name"],
            description=data["description"],
            input_variables=data["input_variables"],
            output_variables=data["output_variables"],
            steps=list(map(lambda s: CommandStep(**s), data["steps"])),
            command_llm=command_llm,
            command_resolver=command_resolver,
        )

    def to_json(self) -> Any:
        return {
            "type": "SequentialCommandStepCommand",
            "name": self.name,
            "description": self.description,
            "input_variables": self.input_variables,
            "output_variables": self.output_variables,
            "steps": list(map(lambda s: s._asdict(), self.steps)),
        }
