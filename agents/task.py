import re
from typing import List, NamedTuple, Dict
from commands.command import (
    Variable,
)
from commands.data_schema import DataSchemaDict, DataSchemaField, DataSchemaScalar


class Task(NamedTuple):
    """
    Represent a task composed of a plain text and input variables, and output schema.

    @param text: plain text, representing the task like "Do the following with [the give url](url) and [the given text](text)."
    @param input_variables: a list of input variables, like:
        [
            Variable("url", "the url to do something", "https://www.google.com"),
            Variable("text", "the text to do something", "hello world")
        ]
    @param output_schema: a dictionary of output fields.
    """

    text: str
    input_variables: List[Variable]
    output_schema: DataSchemaDict


def build_task(text: str, inputs: Dict[str, str]) -> Task:
    """
    Build a task from a plain text and inputs.

    @param text: plain text, representing the task like "Do the following with [the give url](url) and [the given text](text)."
    @param inputs: a dictionary of input variables, like {"url": "the url to do something", "text": "the text to do something"}
    @return: a task
    """

    input_variables: List[Variable] = []
    output_fields: List[DataSchemaField] = []

    regex = r"\[(.*?)\]\((.*?)\)"
    matches = re.findall(regex, text, re.DOTALL)
    for match in matches:
        description = match[0]
        name = match[1]

        if name in inputs:
            input_variables.append(Variable(name, description, inputs[name]))
        else:
            output_fields.append(DataSchemaField(name, DataSchemaScalar(description, "str")))

    return Task(text, input_variables, DataSchemaDict(output_fields))
