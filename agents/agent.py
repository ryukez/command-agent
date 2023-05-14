import re
from typing import Any, List, NamedTuple, Optional, Dict

from test.test_enum import classproperty

from agents.task import Task
from channels.channel import Channel
from commands.command import (
    RETURN_COMMAND_NAME,
    Command,
    ReturnCommand,
    Variable,
)
from commands.executor import CommandExecuter
from commands.registry import CommandRegistry
from langchain import LLMChain, PromptTemplate
from langchain.llms.base import BaseLLM


class AgentAction(NamedTuple):
    """
    Represents an action that the agent can take.
    """

    thought: str
    command: str
    input_variables: List[str]


class AgentActionResult(NamedTuple):
    """
    Represents the result of an action that the agent took.
    """

    command: Command
    inputs: List[Variable]
    outputs: Any
    error: str


class AgentEnvironment(NamedTuple):
    """
    Represents the environment that the agent is executed in.
    """

    commands: Dict[str, Command]
    variables: Dict[str, Variable]
    last_action_result: Optional[AgentActionResult]


class AgentStep(NamedTuple):
    """
    Represents a step that the agent takes.
    """

    id: str
    action: AgentAction
    result: AgentActionResult
    observation: str


class AgentRun(NamedTuple):
    """
    Represents a summary of the agent execution.
    """

    task: Task
    result: Any
    steps: List[AgentStep]


class CommandBasedAgent:
    """
    An agent to handle a given task by executing commands.

    @param plan_llm: The LLM to use for planning.
    @param command_llm: The LLM to use for executing commands.
    @param channel: The channel to use for communication with the user.
    @param verbose: Whether to print verbose output.
    @param num_commands: The number of commands to be embedded in the prompt for planning.
    @param plan_max_retry: The maximum number of times to retry planning.
    @param max_step_count: The maximum number of steps to take.
    """

    plan_llm_chain: LLMChain
    command_llm: BaseLLM
    channel: Channel
    verbose: bool
    num_commands: int = 10
    plan_max_retry: int = 3
    max_step_count: int = 10

    PROMPT = """
Perform the following task as best as you can. You have access to the following commands and variables:

[Commands]
{commands}

[Variables]
{variables}

Use the following format:

Task: the given task you must perform
Thought: you should always think about what to do
Command: the command to execute, should be one of [{command_names}]
Input variables: the variables you can use in the command, should be a subset of [{variable_names}]. For example, [{variable_names}].
Observation: the result of the command
... (this Thought/Command/Input variables/Observation can repeat N times)
Thought: I now know the final answer
Command: ReturnCommand
Input variables: [<variables to use>]

Task: {task}{agent_scratchpad}
"""

    @classproperty
    # Need to set to the LLM as a stop word
    def STOP_WORD(cls) -> str:
        return "Observation:"

    def __init__(self, plan_llm: BaseLLM, command_llm: BaseLLM, channel: Channel, verbose: bool = False) -> None:
        prompt = PromptTemplate(
            template=self.PROMPT,
            input_variables=["commands", "command_names", "variables", "variable_names", "task", "agent_scratchpad"],
        )
        self.plan_llm_chain = LLMChain(llm=plan_llm, prompt=prompt, verbose=verbose)
        self.command_executor = CommandExecuter(command_llm)
        self.channel = channel
        self.verbose = verbose

    def _execute_prompt(
        self,
        task: str,
        commands: Dict[str, Command],
        variables: Dict[str, Variable],
        agent_scratchpad: str,
    ) -> str:
        # Build input
        command_descriptions = "\n\n".join(
            map(
                lambda c: f"{c.name}\n- Description: {c.description}\n- Input: {c.input_schema.string()}\n- Output: {c.output_schema.string()}",
                commands.values(),
            )
        )
        command_names = ",".join(commands.keys())

        variable_descriptions = "\n".join(map(lambda v: f"{v.name}: {v.description}", variables.values()))
        variable_names = ",".join(map(lambda v: f'"{v}"', variables.keys()))

        # Run LLM
        return self.plan_llm_chain.run(
            commands=command_descriptions,
            command_names=command_names,
            variables=variable_descriptions,
            variable_names=variable_names,
            task=task,
            agent_scratchpad=agent_scratchpad,
        )

    def _parse_agent_action(self, output: str) -> Optional[AgentAction]:
        """
        Parse the output of the LLM into an AgentAction.

        (Thought:) <thought>
        Command: <command>
        Input variables: [<var1>, <var2>]
        """

        regex = r"[\s]*(.*)[\n]*Command:[\s]*(.*)[\n]*Input variables:[\s]*(.*)"
        match = re.search(regex, output, re.DOTALL)
        if not match:
            return None
        thought = match.group(1).strip()
        command = match.group(2).strip()
        command_input = match.group(3).strip()

        # Decode ['var1', "var2"] into List[str]
        input_variables = list(map(lambda s: s.strip().strip("'\""), command_input.strip("[]").split(",")))

        return AgentAction(thought, command, input_variables)

    def _build_scratchpad(self, step_history: List[AgentStep]) -> str:
        lines: List[str] = []
        for step in step_history:
            lines += [
                f"Thought: {step.action.thought}",
                f"Command: {step.action.command}",
                f"Input variables: {step.action.input_variables}",
                f"Observation: {step.observation}",
            ]

        return "\n".join(lines) + "\nThought: "

    def _plan(self, task: str, step_history: List[AgentStep], environment: AgentEnvironment) -> AgentAction:
        """
        Plan the next action to take.
        """

        current_output = ""

        for i in range(self.plan_max_retry):
            output = self._execute_prompt(
                task, environment.commands, environment.variables, self._build_scratchpad(step_history) + current_output
            )
            action = self._parse_agent_action(output)
            if action:
                # Modify input variables
                variables: List[str] = []
                for v in action.input_variables:
                    for var in environment.variables.keys():
                        if v.startswith(var):
                            variables.append(var)
                            break

                return AgentAction(action.thought, action.command, variables)

            current_output = current_output + output + "\nThought:"

        raise Exception(f"Failed to plan after {self.plan_max_retry} retries")

    async def run(
        self,
        task: Task,
        command_registry: CommandRegistry,
    ) -> AgentRun:
        """
        Run the agent on the given task.
        """

        variables = {v.name: v for v in task.input_variables}
        commands = {
            c.name: c
            for c in command_registry.query(task.text, n=self.num_commands) + [ReturnCommand(schema=task.output_schema)]
        }
        environment: AgentEnvironment = AgentEnvironment(
            commands=commands, variables=variables, last_action_result=None
        )

        step_history: List[AgentStep] = []
        for step_number in range(self.max_step_count):
            action = self._plan(task.text, step_history, environment)
            if self.verbose:
                print(action)

            command = environment.commands[action.command]
            inputs = list(map(lambda v: environment.variables[v], action.input_variables))

            [outputs, error] = await self.command_executor.execute(command, inputs, self.channel)
            if error == "":
                observation = f"Command was successful, saving the result to steps.{step_number}.output variable"
                variables[f"steps.{step_number}.output"] = Variable(
                    f"steps.{step_number}.output",
                    f"result of {action.command}({ ', '.join(action.input_variables) }).",
                    outputs,
                )
            else:
                observation = f"[Error] {error}"

            if self.verbose:
                print(observation)

            result = AgentActionResult(command=command, inputs=inputs, outputs=outputs, error=error)
            step = AgentStep(id=f"{step_number}", action=action, result=result, observation=observation)
            step_history.append(step)

            if command.name == RETURN_COMMAND_NAME and error == "":
                return AgentRun(task, outputs, step_history)

        raise Exception(f"Failed to complete task after {self.max_step_count} steps")
