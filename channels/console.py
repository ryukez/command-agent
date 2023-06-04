import json
from typing import Any
from channels.channel import Channel


class ChannelConsole(Channel):
    async def send(self, message: str, data: Any = {}):
        lines = [
            "",
            message,
        ]

        if data != {}:
            lines.append("")
            lines.append(json.dumps(data, indent=2, ensure_ascii=False))

        print("\n".join(lines))

    async def wait_reply(self, message: str, data: Any = {}) -> str:
        lines = [
            "",
            message,
        ]

        if data != {}:
            lines.append("")
            lines.append(json.dumps(data, indent=2, ensure_ascii=False))

        return input("\n".join(lines))
