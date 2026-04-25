"""从 DISC-Law-SFT-Triplet 数据中提取法条，构建向量库"""
import json
import hashlib
from rag.vector_retriever import VectorRetriever

TRIPLET_FILE = "data/DISC-Law-SFT/DISC-Law-SFT-Triplet-released.jsonl"


if __name__ == "__main__":
    laws = {}
    with open(TRIPLET_FILE, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            for ref in rec.get("reference", []):
                ref = ref.strip()
                if ref:
                    doc_id = hashlib.md5(ref.encode()).hexdigest()[:16]
                    laws[doc_id] = ref

    print(f"共提取 {len(laws)} 条唯一法条")

    retriever = VectorRetriever("rag/law_db", reset=True)
    retriever.build_from_laws(laws)
    print("向量库构建完成。")
