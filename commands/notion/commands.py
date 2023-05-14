from typing import Any, Dict, List, Tuple
from commands.command import Command
from commands.data_schema import (
    DataSchemaArray,
    DataSchemaDict,
    DataSchemaEnum,
    DataSchemaField,
    DataSchemaScalar,
)
from notion_client import Client
from channels.channel import Channel
from utils.string import parse_comma_separated_text


def notion_commands(token: str) -> List[Command]:
    return [
        SearchNotionDatabasesCommand(token),
        InsertNotionDatabasePageCommand(token, human_check=True),
    ]


# https://developers.notion.com/reference/post-search
class SearchNotionDatabasesCommand(Command):
    name: str = "SearchNotionDatabasesCommand"
    description: str = "Search Notion databases and return the database schema"
    token: str

    input_schema: DataSchemaDict = DataSchemaDict(
        [
            DataSchemaField("database_name", DataSchemaScalar("name of the database to search", "str")),
        ]
    )
    output_schema: DataSchemaDict = DataSchemaDict(
        [
            DataSchemaField("id", DataSchemaScalar("id of the database", "str")),
            DataSchemaField("title", DataSchemaScalar("title of the database", "str")),
            DataSchemaField(
                "properties",
                DataSchemaArray(
                    DataSchemaDict(
                        [
                            DataSchemaField("name", DataSchemaScalar("name of the property", "str")),
                            DataSchemaField(
                                "type",
                                DataSchemaEnum(
                                    "type of the property",
                                    ["rich_text", "multi_select", "url", "title", "created_time", "created_by"],
                                ),
                            ),
                        ]
                    )
                ),
            ),
        ]
    )

    def __init__(self, token: str, **kwargs):
        super().__init__(**kwargs)
        self.token = token

    async def _run(self, inputs: Any, channel: Channel) -> Tuple[Any, str]:
        database_name = inputs["database_name"]

        notion = Client(auth=self.token)
        response: Any = notion.search(
            **{
                "query": database_name,
                "filter": {"value": "database", "property": "object"},
            }
        )

        # For simplicity, returns the first matched one
        if len(response["results"]) == 0:
            return None, f"Database '{database_name}' was not found. Please try again changing your query."

        result: Dict[str, Any] = response["results"][0]

        return {
            "id": result["id"],
            "title": result["title"][0]["plain_text"],
            "properties": list(
                map(
                    lambda p: {"name": p[0], "type": p[1]["type"]},
                    result["properties"].items(),
                )
            ),
        }, ""


# https://developers.notion.com/reference/post-page
class InsertNotionDatabasePageCommand(Command):
    name: str = "InsertNotionDatabasePageCommand"
    description: str = "Insert a new page to a Notion database"
    token: str
    additional_prompts: List[str] = [
        "Be sure to set the proper values to 'properties' fields, which should be inferred from the content.",
        "The value of 'multi_select' property should be a list of strings, separated by comma. For example, 'a,b,c'.",
    ]

    input_schema: DataSchemaDict = DataSchemaDict(
        [
            DataSchemaField(
                "page_data",
                DataSchemaDict(
                    [
                        DataSchemaField("content", DataSchemaScalar("content of the page", "str")),
                        DataSchemaField(
                            "properties",
                            DataSchemaArray(
                                DataSchemaDict(
                                    [
                                        DataSchemaField("name", DataSchemaScalar("name of the property", "str")),
                                        DataSchemaField(
                                            "type",
                                            DataSchemaEnum(
                                                "type of the property",
                                                [
                                                    "rich_text",
                                                    "multi_select",
                                                    "url",
                                                    "title",
                                                    "created_time",
                                                    "created_by",
                                                ],
                                            ),
                                        ),
                                        DataSchemaField("value", DataSchemaScalar("value of the property", "str")),
                                    ]
                                )
                            ),
                        ),
                    ]
                ),
            ),
            DataSchemaField(
                "database_schema",
                DataSchemaDict(
                    [
                        DataSchemaField("id", DataSchemaScalar("id of the database", "str")),
                        DataSchemaField("title", DataSchemaScalar("title of the database", "str")),
                        DataSchemaField(
                            "properties",
                            DataSchemaArray(
                                DataSchemaDict(
                                    [
                                        DataSchemaField("name", DataSchemaScalar("name of the property", "str")),
                                        DataSchemaField(
                                            "type",
                                            DataSchemaEnum(
                                                "type of the property",
                                                [
                                                    "rich_text",
                                                    "multi_select",
                                                    "url",
                                                    "title",
                                                    "created_time",
                                                    "created_by",
                                                ],
                                            ),
                                        ),
                                    ]
                                )
                            ),
                        ),
                    ]
                ),
            ),
        ],
    )

    output_schema: DataSchemaDict = DataSchemaDict(
        [
            DataSchemaField("url", DataSchemaScalar("url of the created page", "str")),
        ]
    )

    def __init__(self, token: str, **kwargs):
        super().__init__(**kwargs)
        self.token = token

    async def _run(self, inputs: Any, channel: Channel) -> Tuple[Any, str]:
        schema = inputs["database_schema"]
        page = inputs["page_data"]

        if schema["id"] == "<id of the database>" or schema["id"] == "":
            return None, "database_id is not set. Use SearchNotionDatabasesCommand to fetch the corrent database."

        properties: Dict[str, Any] = {}
        for p in page["properties"]:
            ptype = p["type"]
            pname = p["name"]
            pvalue = p["value"]

            if pvalue is None or pvalue == "":
                continue

            if ptype == "title":
                properties[pname] = {"title": [{"text": {"content": pvalue}}]}
            if ptype == "rich_text":
                properties[pname] = {"rich_text": [{"text": {"content": pvalue}}]}
            if ptype == "multi_select":
                properties[pname] = {
                    "multi_select": list(map(lambda v: {"name": v}, parse_comma_separated_text(pvalue)))
                }
            if ptype == "url":
                properties[pname] = {"url": pvalue}
            # Skip auto-generated properties
            if ptype == "created_time" or ptype == "created_by":
                pass

        notion = Client(auth=self.token)
        response: Any = notion.pages.create(
            **{
                "parent": {"database_id": schema["id"]},
                "properties": properties,
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": page["content"],
                                    },
                                }
                            ]
                        },
                    },
                ],
            }
        )
        return {"url": response["url"]}, ""
