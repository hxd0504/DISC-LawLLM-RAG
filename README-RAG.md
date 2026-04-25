# DISC-LawLLM-RAG

基于 DISC-Law-SFT 公开数据集构建的中文法律问答检索增强系统，当前版本实现了 Vector RAG 与 Legal GraphRAG 两种法律依据检索链路，并支持在 CLI / Web 问答入口中进行 Prompt 增强。

Built on top of [DISC-LawLLM](https://github.com/FudanDISC/DISC-LawLLM) from Fudan University DISC Lab.

---

## Current Version

**v0.1 Retrieval Module**

- 从 DISC-Law-SFT-Triplet 数据集中抽取 `reference` 法律依据
- 使用 MD5 前 16 位作为稳定 ID，对法律依据文本进行去重
- 使用 `bge-base-zh-v1.5` 对法条文本进行向量化
- 使用 Chroma 构建持久化法律依据向量库
- 实现 `VectorRetriever`，支持用户问题到 Top-k 法律依据检索
- 基于 Triplet 数据中的法条共引关系构建 Neo4j 法条图谱
- 实现 `GraphRetriever`，在向量召回基础上进行图谱邻域扩展
- 已接入 CLI / Web 端的 Prompt 增强流程

---

## Pipeline

```text
DISC-Law-SFT-Triplet 数据
        ↓
抽取 reference 法律依据
        ↓
MD5 去重生成稳定 doc_id
        ↓
bge-base-zh-v1.5 向量化
        ↓
Chroma 向量库
        ↓
VectorRetriever 召回 Top-k reference
        ↓
Neo4j GraphRetriever 沿 CO_CITED / SAME_LAW_ADJACENT 扩展相关法条
        ↓
构造增强 Prompt → DISC-LawLLM / Qwen2.5 生成回答
```

---

## Vector RAG

当前向量检索模块采用 `reference-level chunking`：

- 每条 `reference` 字段中的法律依据文本作为一个检索单元
- 使用文本内容的 MD5 前 16 位作为稳定 ID，相同法律依据自动去重
- 使用 `bge-base-zh-v1.5` 生成 768 维向量
- 使用 Chroma 持久化到 `rag/law_db`
- 查询时返回 Top-k 相关法律依据，拼接到用户问题前作为上下文

---

## Legal GraphRAG

纯向量检索只能找到语义相似的法条，但法律问答中还需要找到经常共同适用、相邻的法条。

### Node

- `Article`：法条 / reference 级法律依据节点（181 个）

### Relations

| Relation | Meaning | Count |
|---|---|---|
| `CO_CITED` | 同一个 Triplet 样本中共同出现的法条 | 664 |
| `SAME_LAW_ADJACENT` | 同一部法律中条号距离 ≤ 3 的相邻条文 | 365 |

`CO_CITED` 是核心关系：将 Triplet 数据中的多法条共同引用关系转化为图谱边，使系统能够在向量召回种子法条后，进一步扩展司法实践中经常联合适用的相关条文。

---

## Project Structure

```
├── rag/
│   ├── vector_retriever.py     # VectorRetriever: Chroma + bge-base-zh-v1.5
│   ├── graph_retriever.py      # GraphRetriever: vector seeds + Neo4j expansion
│   ├── article_extractor.py    # Parse law_name and article_num from reference text
│   └── __init__.py
├── build_vector_db.py          # Build Chroma vector store from Triplet dataset
├── build_graph_db.py           # Build Neo4j graph from Triplet dataset
├── graph_retriever_demo.py     # Standalone test for GraphRetriever
├── cli_demo.py                 # CLI chat with RAG
└── web_demo.py                 # Streamlit web UI with RAG
```

---

## Data

本项目使用公开数据集：

- `DISC-Law-SFT-Triplet-released.jsonl`
- 来源：[ShengbinYue/DISC-Law-SFT](https://huggingface.co/datasets/ShengbinYue/DISC-Law-SFT)

由于数据集和模型文件体积较大，本仓库不直接上传完整数据和模型权重。请自行下载后放置到以下目录：

```
data/DISC-Law-SFT/DISC-Law-SFT-Triplet-released.jsonl
models/BAAI/bge-base-zh-v1___5/
```

---

## Installation

```bash
pip install -r requirements.txt
```

### Download embedding model

```bash
pip install modelscope
```

```python
from modelscope import snapshot_download
snapshot_download('BAAI/bge-base-zh-v1.5', cache_dir='models')
```

> ModelScope saves the model to `models/BAAI/bge-base-zh-v1___5`. The code expects this exact path.

### Build vector database

```bash
python build_vector_db.py
```

### Build graph database

Start Neo4j locally, then:

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password

python build_graph_db.py
```

### Run

```bash
# Web UI (uses GraphRetriever, falls back to VectorRetriever if Neo4j unavailable)
streamlit run web_demo.py

# CLI
python cli_demo.py

# Test GraphRetriever only
python graph_retriever_demo.py
```

---

## Version Roadmap

| Version | Module | Status |
|---|---|---|
| v0.1 | Retrieval Module: Vector RAG + Legal GraphRAG | Done |
| v0.2 | Retrieval Evaluation: Recall@k / MRR / Evidence Coverage | Planned |
| v0.3 | LoRA SFT / RAG-SFT with DISC-Law-SFT Pair & Triplet | Planned |
| v0.4 | vLLM + FastAPI Service Deployment | Planned |
| v0.5 | End-to-End Evaluation and Demo Release | Planned |

---

## Limitations

1. `reference-level chunking` 依赖 Triplet 数据中人工构造的 reference 字段，尚未覆盖真实法规库中的复杂版式
2. 一条 reference 可能包含多个法条，直接整体向量化会造成一定语义稀释
3. 过短 reference 可能无法支撑复杂法律问题的完整推理
4. `SAME_LAW_ADJACENT` 只是弱结构关系，相邻条文不一定共同适用
5. 当前版本尚未完成系统性 Recall@k / MRR 评测、LoRA 微调和 vLLM 服务化部署

---

## Based On

[FudanDISC/DISC-LawLLM](https://github.com/FudanDISC/DISC-LawLLM) — Fudan University DISC Lab
