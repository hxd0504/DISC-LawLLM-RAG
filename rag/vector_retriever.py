"""
向量检索模块：法条库 → Chroma 向量库 → 语义检索
使用本地 bge-base-zh-v1.5 embedding
"""

import os
import re
from typing import List, Dict
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

BGE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "BAAI", "bge-base-zh-v1___5")
COLLECTION_NAME = "law_articles"


class VectorRetriever:
    def __init__(self, persist_dir: str = "rag/law_db", reset: bool = False):
        self.ef = SentenceTransformerEmbeddingFunction(model_name=os.path.abspath(BGE_MODEL_PATH))
        self.client = chromadb.PersistentClient(path=persist_dir)
        if reset:
            try:
                self.client.delete_collection(COLLECTION_NAME)
            except Exception:
                pass
            self.collection = self.client.create_collection(COLLECTION_NAME, embedding_function=self.ef)
        else:
            self.collection = self.client.get_or_create_collection(COLLECTION_NAME, embedding_function=self.ef)

    def build_from_laws(self, laws: Dict[str, str]):
        """laws: {id: 法条文本}"""
        ids = list(laws.keys())
        docs = list(laws.values())
        print(f"[VectorRetriever] 写入 {len(docs)} 条法条...")
        batch = 100
        for i in range(0, len(docs), batch):
            self.collection.upsert(documents=docs[i:i+batch], ids=ids[i:i+batch])
            print(f"  {min(i+batch, len(docs))}/{len(docs)}", end="\r")
        print(f"\n[VectorRetriever] 完成")

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        if self.collection.count() == 0:
            return []
        results = self.collection.query(query_texts=[query], n_results=top_k)
        return results["documents"][0]

    def format_context(self, query: str, top_k: int = 3) -> str:
        docs = self.retrieve(query, top_k)
        if not docs:
            return ""
        return "【相关法条】\n" + "\n---\n".join(docs) + "\n\n【问题】\n"
