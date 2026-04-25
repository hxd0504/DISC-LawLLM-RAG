"""从 DISC-Law-SFT-Triplet 数据构建 Neo4j 法条知识图谱"""
import os
import json
import hashlib
import re
from collections import defaultdict
from itertools import combinations
import cn2an
from neo4j import GraphDatabase
from rag.article_extractor import extract_articles

TRIPLET_FILE = "data/DISC-Law-SFT/DISC-Law-SFT-Triplet-released.jsonl"
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")


def md5id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]


def art_num_int(num_str: str) -> int:
    try:
        return cn2an.cn2an(num_str, "smart")
    except Exception:
        return 0


def build_graph(uri, user, password):
    driver = GraphDatabase.driver(uri, auth=(user, password))

    # doc_id -> article dict（以 doc_id 为主键，消除一对多歧义）
    articles = {}
    freq = defaultdict(int)
    co_cited = defaultdict(int)
    parse_fail = 0
    total_refs = 0
    total_samples = 0

    with open(TRIPLET_FILE, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            refs = rec.get("reference", [])
            total_samples += 1
            total_refs += len(refs)

            sample_doc_ids = []
            for ref in refs:
                ref = ref.strip()
                if not ref:
                    continue
                doc_id = md5id(ref)
                arts = extract_articles(ref, doc_id)
                if not arts[0]["law_name"]:
                    parse_fail += 1
                a = arts[0]
                a["doc_id"] = doc_id
                articles[doc_id] = a
                freq[doc_id] += 1
                sample_doc_ids.append(doc_id)

            for a, b in combinations(set(sample_doc_ids), 2):
                key = (min(a, b), max(a, b))
                co_cited[key] += 1

    # SAME_LAW_ADJACENT
    by_law = defaultdict(list)
    for doc_id, art in articles.items():
        if art["law_name"] and art["article_num"]:
            m = re.match(r'第(.+)条', art["article_num"])
            if m:
                by_law[art["law_name"]].append((doc_id, art_num_int(m.group(1))))

    adjacent = []
    for law, items in by_law.items():
        items.sort(key=lambda x: x[1])
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                dist = abs(items[j][1] - items[i][1])
                if dist <= 3:
                    adjacent.append((items[i][0], items[j][0], dist))
                else:
                    break

    with driver.session() as session:
        session.run("MATCH (n:Article) DETACH DELETE n")

        for art in articles.values():
            session.run(
                "MERGE (a:Article {doc_id: $doc_id}) "
                "SET a.law_name=$law_name, a.article_num=$article_num, "
                "a.text=$text, a.freq=$freq",
                doc_id=art["doc_id"], law_name=art["law_name"],
                article_num=art["article_num"], text=art["text"],
                freq=freq[art["doc_id"]]
            )

        for (a, b), w in co_cited.items():
            session.run(
                "MATCH (x:Article {doc_id:$a}), (y:Article {doc_id:$b}) "
                "MERGE (x)-[r:CO_CITED]-(y) SET r.weight=$w, r.source='co_citation'",
                a=a, b=b, w=w
            )

        for a, b, dist in adjacent:
            session.run(
                "MATCH (x:Article {doc_id:$a}), (y:Article {doc_id:$b}) "
                "MERGE (x)-[r:SAME_LAW_ADJACENT]-(y) "
                "SET r.distance=$dist, r.weight=0.3, r.source='same_law_adjacent'",
                a=a, b=b, dist=dist
            )

    driver.close()

    print(f"Article 节点数:          {len(articles)}")
    print(f"CO_CITED 边数:           {len(co_cited)}")
    print(f"SAME_LAW_ADJACENT 边数:  {len(adjacent)}")
    print(f"解析失败 reference 数:   {parse_fail}")
    print(f"样本总数:                {total_samples}")
    print(f"平均每样本 reference 数: {total_refs/max(total_samples,1):.2f}")


if __name__ == "__main__":
    build_graph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
