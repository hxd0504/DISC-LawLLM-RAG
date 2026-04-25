"""独立测试 GraphRetriever，不依赖主模型。"""
from rag.graph_retriever import GraphRetriever

QUERY = "盗窃罪的量刑标准是什么？"

gr = GraphRetriever()
result = gr.retrieve(QUERY)

print("=== 向量召回 seed 法条 ===")
for i, t in enumerate(result["seeds"], 1):
    print(f"{i}. {t[:80]}...")

print("\n=== 图谱扩展法条 ===")
for i, t in enumerate(result["expanded"], 1):
    print(f"{i}. {t[:80]}...")

print("\n=== format_context 输出 ===")
print(gr.format_context(QUERY))

gr.close()
