"""
GraphRetriever: 向量召回 seed 法条 → Neo4j 1-hop 扩展
接口与 VectorRetriever 保持一致。
"""
import os
import hashlib
from neo4j import GraphDatabase
from rag.vector_retriever import VectorRetriever

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")


class GraphRetriever:
    def __init__(self, persist_dir="rag/law_db",
                 neo4j_uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD,
                 top_k=5):
        self._fallback = VectorRetriever(persist_dir)
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))
        self.driver.verify_connectivity()  # 构造阶段失败则让 fallback 生效
        self.top_k = top_k

    def _expand(self, seed_texts: list[str], top_k: int) -> list[str]:
        expanded = []
        with self.driver.session() as session:
            for text in seed_texts:
                doc_id = hashlib.md5(text.encode()).hexdigest()[:16]
                res = session.run(
                    "MATCH (a:Article {doc_id: $doc_id}) RETURN a.doc_id AS did LIMIT 1",
                    doc_id=doc_id
                )
                record = res.single()
                if not record:
                    continue
                did = record["did"]

                neighbors = session.run(
                    "MATCH (a:Article {doc_id:$did})-[r:CO_CITED]-(b:Article) "
                    "RETURN b.text AS text, r.weight AS w ORDER BY w DESC LIMIT $k",
                    did=did, k=top_k
                )
                for row in neighbors:
                    expanded.append(row["text"])

                if len(expanded) < 3:
                    adj = session.run(
                        "MATCH (a:Article {doc_id:$did})-[:SAME_LAW_ADJACENT]-(b:Article) "
                        "RETURN b.text AS text LIMIT 3",
                        did=did
                    )
                    for row in adj:
                        expanded.append(row["text"])

        return expanded

    def retrieve(self, query: str, top_k: int = None) -> dict:
        k = top_k or self.top_k
        seeds = self._fallback.retrieve(query, top_k=k)
        expanded = self._expand(seeds, k)
        seen = set(seeds)
        unique_expanded = [t for t in expanded if t not in seen]
        return {"seeds": seeds, "expanded": unique_expanded[:k]}

    def format_context(self, query: str, top_k: int = None) -> str:
        try:
            result = self.retrieve(query, top_k)
            parts = []
            if result["seeds"]:
                parts.append("【向量召回法条】\n" + "\n---\n".join(result["seeds"]))
            if result["expanded"]:
                parts.append("【图谱扩展法条】\n" + "\n---\n".join(result["expanded"]))
            if not parts:
                return ""
            return "\n\n".join(parts) + "\n\n【问题】\n"
        except Exception:
            return self._fallback.format_context(query, top_k or self.top_k)

    def close(self):
        self.driver.close()
