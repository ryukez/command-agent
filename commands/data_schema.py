import abc
from typing import Any, List, NamedTuple


class DataSchema(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def string(self) -> str:
        """
        @return: string representation of the schema
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def validate(self, data: Any) -> str:
        """
        @param data: data to validate
        @return: error message if data does not satisfy the schema, otherwise empty string
        """
        raise NotImplementedError()


class DataSchemaScalar(DataSchema):
    description: str
    python_type: str

    def __init__(self, description: str, python_type: str):
        self.description = description
        self.python_type = python_type

    def string(self) -> str:
        return f"<{self.description} ({self.python_type})>"

    def validate(self, data: Any) -> str:
        if self.python_type == "str":
            return "" if type(data) is str else "should be string"
        if self.python_type == "int":
            return "" if type(data) is int else "should be int"
        raise NotImplementedError()


class DataSchemaEnum(DataSchema):
    description: str
    values: List[Any]

    def __init__(self, description: str, values: List[Any]):
        self.description = description
        self.values = values

    def string(self) -> str:
        return f"<{self.description}, should be one of [{','.join(self.values)}]>"

    def validate(self, data: Any) -> str:
        if data not in self.values:
            return f"should be one of [{','.join(self.values)}]"
        return ""


class DataSchemaArray(DataSchema):
    schema: DataSchema

    def __init__(self, schema: DataSchema):
        self.schema = schema

    def string(self) -> str:
        return f"[ {self.schema.string()} ])"

    def validate(self, data: Any) -> str:
        if type(data) is not list:
            return "should be array"
        for item in data:
            error = self.schema.validate(item)
            if error:
                return error
        return ""


class DataSchemaField(NamedTuple):
    name: str
    schema: DataSchema


class DataSchemaDict(DataSchema):
    fields: List[DataSchemaField]

    def __init__(self, fields: List[DataSchemaField]):
        self.fields = fields

    def string(self) -> str:
        return "{ " + ", ".join(list(map(lambda f: f'"{f.name}": {f.schema.string()}', self.fields))) + " }"

    def validate(self, data: Any) -> str:
        if type(data) is not dict:
            return "should be object"
        for field in self.fields:
            error = field.schema.validate(data.get(field.name))
            if error:
                return f"field {field.name}: {error}"
        return ""
