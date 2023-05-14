import abc
from typing import List, NamedTuple, Union


class Entry(NamedTuple):
    key: str
    value: str


class Storage(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get(self, key: str) -> Union[Entry, None]:
        raise NotImplementedError()

    @abc.abstractmethod
    def set(self, entry: Entry, description: str):
        raise NotImplementedError()

    @abc.abstractmethod
    def query(self, q: str, n: int) -> List[Entry]:
        """
        Fetch top n entries whose description match the query.

        @param q: query
        @param n: number of entries to fetch
        """

        raise NotImplementedError()
