from commands.resolver import CommandResolver
from commands.sequential import CommandStep, SequentialCommandStepCommand
from langchain.llms.base import BaseLLM
from agents.agent import AgentRun


def create_sequential_command_from_agent_run(
    name: str, agent_run: AgentRun, command_llm: BaseLLM, command_resolver: CommandResolver
) -> SequentialCommandStepCommand:
    steps = list(filter(lambda step: step.result.error == "", agent_run.steps))

    return SequentialCommandStepCommand(
        name,
        agent_run.task.text,
        {v.name: v.description for v in agent_run.task.input_variables},
        {f.name: f.schema.string() for f in agent_run.task.output_schema.fields},
        list(map(lambda step: CommandStep(step.id, step.action.command, step.action.input_variables), steps)),
        command_llm,
        command_resolver,
    )
