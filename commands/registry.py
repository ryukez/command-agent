import json
from typing import Dict, Optional, List
from commands.command import Command
from commands.composite import CompositeCommand
from commands.resolver import CommandResolver
from commands.sequential import SequentialCommandStepCommand
from langchain.llms.base import BaseLLM
from storage.storage import Entry, Storage


class CommandRegistry(CommandResolver):
    """
    Manages the commands that the agent can execute.

    @param builtin_commands: list of builtin commands
    @param storage: storage to use for command persistence
    @param command_llm: LLM to be used for command execution
    """

    builtin_commands: Dict[str, Command]
    storage: Storage
    command_llm: BaseLLM

    def __init__(self, builtin_commands: List[Command], storage: Storage, command_llm: BaseLLM):
        self.builtin_commands = {c.name: c for c in builtin_commands}
        self.storage = storage
        self.command_llm = command_llm

        # Create or update entries for builtin commands
        for cmd in builtin_commands:
            self.save(cmd)

    def parse_command(self, body: str) -> Optional[Command]:
        try:
            data = json.loads(body)
            if data["type"] == "__builtin__":
                return self.builtin_commands[data["name"]]
            if data["type"] == "SequentialCommandStepCommand":
                return SequentialCommandStepCommand.from_json(data, command_llm=self.command_llm, command_resolver=self)
        except Exception as e:
            print(e)
            pass

        return None

    def resolve(self, command: str) -> Optional[Command]:
        entry = self.storage.get(command)
        if entry is not None:
            return self.parse_command(entry.value)
        return None

    def query(self, q: str, n: int) -> List[Command]:
        commands: List[Command] = []
        for e in self.storage.query(q, n):
            command = self.parse_command(e.value)
            if command is not None:
                commands.append(command)
        return commands

    def save(self, command: Command):
        if isinstance(command, CompositeCommand):
            self.storage.set(Entry(command.name, json.dumps(command.to_json())), command.description)
        else:
            self.builtin_commands[command.name] = command
            self.storage.set(
                Entry(command.name, json.dumps({"type": "__builtin__", "name": command.name})),
                command.description,
            )
