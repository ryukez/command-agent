import os
from agents.agent import CommandBasedAgent
from agents.commands import create_sequential_command_from_agent_run
from agents.task import build_task
from channels.console import ChannelConsole
from commands.notion.commands import notion_commands
from commands.registry import CommandRegistry
from dotenv import load_dotenv
from langchain import OpenAI
from langchain.embeddings import OpenAIEmbeddings
import pinecone
from storage.pinecone import PineconeDB

# Generated by ChatGPT
TEXT = """
An introduction to Large Language Model

Large Language Models (LLMs) are a type of machine learning model designed to understand and generate human-like text. They are part of a broader category of models called transformers, which utilize a type of neural network architecture known as the Transformer. These models are trained on a wide variety of internet text to capture the patterns, grammar, and style of human language.

The most well-known LLM is GPT (Generative Pretrained Transformer), developed by OpenAI. As of my knowledge cutoff in September 2021, the latest version is GPT-4. This model has a vast number of parameters, which allow it to generate high-quality, human-like text based on the input it is given.

LLMs work by predicting the next word in a sentence. For example, given the input "The sky is...", the model might predict "blue" as the next word. However, it's not just guessing the next word randomly; it's making an educated guess based on the patterns it learned during training.

The training process involves showing the model many examples of sentences and letting it gradually adjust its parameters to better predict the next word in the sentence. The aim is to minimize the difference between the model's predictions and the actual next words in the sentences it is trained on.

These models can be used in a variety of applications, including drafting emails, writing code, creating written content, answering questions, translating languages, and even tutoring in a wide range of academic subjects. However, their use also raises important ethical and safety concerns, such as the potential for misuse, the generation of misinformation, and the need for appropriate content filtering.
"""


async def run_agent():
    load_dotenv(verbose=True)

    plan_llm = OpenAI(temperature=0, max_tokens=200, model_kwargs={"stop": CommandBasedAgent.STOP_WORD})
    command_llm = OpenAI(temperature=0, max_tokens=1500)

    task = build_task(
        "Save [the given text](text) into [the given Notion database](database_name). Output [the URL of the created page](page_url).",
        {"database_name": os.environ["NOTION_DATABASE_NAME"], "text": TEXT},
    )

    pinecone.init(api_key=os.environ["PINECONE_API_KEY"], environment=os.environ["PINECONE_ENVIRONMENT"])
    index = pinecone.Index(os.environ["PINECONE_COMMANDS_INDEX_NAME"])

    emb = OpenAIEmbeddings()
    storage = PineconeDB(index, emb)

    command_registry = CommandRegistry(notion_commands(token=os.environ["NOTION_TOKEN"]), storage, command_llm)
    channel = ChannelConsole()

    agent = CommandBasedAgent(plan_llm, command_llm, channel, verbose=True)

    run = await agent.run(task, command_registry)
    print(run.result)

    # Save the execution sequence as a single composite command
    if input("Save the command? YES/[NO]: ") == "YES":
        name = input("Enter the command name: ")
        command = create_sequential_command_from_agent_run(name, run, command_llm, command_registry)
        print(command.to_json())

        command_registry.save(command)
        print("Command saved.")
