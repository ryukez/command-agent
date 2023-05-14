from typing import Any
from channels.channel import Channel


class ChannelConsole(Channel):
    async def send(self, message_object: Any):
        print(f"\n{message_object}\n")

    async def wait_check(self, command: str, inputs: Any) -> str:
        lines = [
            "",
            (
                'Enter "OK" if the input looks good, otherwise put the reason'
                " for rejection or details on how to fix the input:"
            ),
            f"Command: {command}",
            "Inputs:",
            f"{inputs}",
            "",
        ]

        result = input("\n".join(lines))
        return result if result != "OK" else ""
