from typing import List, Union
from langchain.embeddings.base import Embeddings
import pinecone
from storage.storage import Entry, Storage


class PineconeDB(Storage):
    index: pinecone.Index
    embeddings: Embeddings

    def __init__(self, index: pinecone.Index, embeddings: Embeddings):
        self.index = index
        self.embeddings = embeddings

    def get(self, key: str) -> Union[Entry, None]:
        response = self.index.fetch([key])
        if key in response.get("vectors", {}):
            props = response.get("vectors")[key]
            return Entry(props["id"], props["metadata"]["value"])
        return None

    def set(self, entry: Entry, description: str):
        [vector] = self.embeddings.embed_documents([description])
        self.index.upsert([(entry.key, vector, {"value": entry.value})])

    def query(self, q: str, n: int) -> List[Entry]:
        vector = self.embeddings.embed_query(q)
        response = self.index.query(vector, include_metadata=True, top_k=n)

        entries: List[Entry] = []
        for m in response.get("matches", []):
            entries.append(Entry(m.id, m.metadata["value"]))
        return entries
