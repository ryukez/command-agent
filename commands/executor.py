import json
from typing import Any, Tuple, List
from commands.command import Command, Variable
from langchain import LLMChain, PromptTemplate
from langchain.llms.base import BaseLLM
from channels.channel import Channel


class CommandExecuter:
    llm_chain: LLMChain

    PROMPT = """
Your task is to transform the given context into the desired data format.

Context:
{context}

Format:
{format}

Output should only contain the output, with the format of JSON which satisfies the format above.

Output:
"""

    def __init__(self, llm: BaseLLM):
        prompt = PromptTemplate(template=self.PROMPT, input_variables=["context", "format"])
        self.llm_chain = LLMChain(llm=llm, prompt=prompt)

    async def execute(self, command: Command, variables: List[Variable], channel: Channel) -> Tuple[Any, str]:
        context = "\n\n".join(map(lambda v: f"{v.description}: {json.dumps(v.value, ensure_ascii=False)}", variables))
        format = command.input_schema.string()
        if len(command.additional_prompts) > 0:
            format += "\n\nAdditional prompts:" + "\n".join(command.additional_prompts)

        llm_result = self.llm_chain.run(context=context, format=format)

        inputs = json.loads(llm_result)

        try:
            outputs, error = await command.run(inputs, channel)
            if error != "":
                return None, error
        except Exception as e:
            return None, str(e)

        return outputs, ""
