import asyncio
from dotenv import load_dotenv
from samples.execute_command import execute_command
from samples.run_agent import run_agent


if __name__ == "__main__":
    load_dotenv(verbose=True)
    # asyncio.run(run_agent())
    asyncio.run(execute_command())
