# LegalRAG-Qwen2.5

基于 DISC-Law-SFT 公开数据集构建的中文法律问答检索增强系统。  
本项目在 DISC-LawLLM 的基础上，补充实现了法律依据向量检索、Neo4j 法条图谱扩展和 RAG / GraphRAG Prompt 增强链路。

> 本项目是基于 DISC-LawLLM 与 DISC-Law-SFT 的非官方扩展版本，不代表原项目官方实现。原项目说明见 [README-upstream.md](./README-upstream.md)。

## 当前版本

**v0.1 Retrieval Module：Vector RAG + Legal GraphRAG**

当前版本聚焦法律问答中的检索增强模块，已完成：

- 从 DISC-Law-SFT-Triplet 数据集中抽取 `reference` 法律依据
- 使用 MD5 前 16 位作为稳定 ID，对法律依据文本进行去重
- 使用 `bge-base-zh-v1.5` 生成法律依据向量
- 使用 Chroma 构建持久化向量库
- 实现 `VectorRetriever`，支持用户问题到 Top-k 法律依据检索
- 基于 Triplet 样本中的共引关系构建 Neo4j 法条图谱（181 节点，664 CO_CITED 边，365 SAME_LAW_ADJACENT 边）
- 实现 `GraphRetriever`，在向量召回基础上扩展相关法条
- 已接入 CLI / Web 的 Prompt 增强流程

## 为什么做这个扩展

DISC-LawLLM 原项目已经提供法律大模型、SFT 数据和评测框架，但其检索增强模块依赖外部知识库，且仓库中没有直接提供可复现的法条向量化和图谱检索构建流程。

本项目补充了一个可复现的检索增强模块：

```
DISC-Law-SFT-Triplet reference
        ↓
法律依据抽取与去重
        ↓
BGE 向量化 + Chroma 持久化
        ↓
Vector RAG 召回语义相关法条
        ↓
Neo4j GraphRAG 扩展共引 / 相邻法条
        ↓
增强 Prompt
        ↓
DISC-LawLLM / Qwen2.5 生成回答
```

## 模块结构

```
.
├── build_vector_db.py        # 从 Triplet reference 构建 Chroma 向量库
├── build_graph_db.py         # 从 Triplet 共引关系构建 Neo4j 法条图谱
├── cli_demo.py               # 命令行问答入口，支持 RAG 检索增强
├── web_demo.py               # Streamlit Web 问答入口
├── graph_retriever_demo.py   # GraphRetriever 独立测试脚本
├── rag/
│   ├── vector_retriever.py   # 向量检索模块
│   ├── graph_retriever.py    # 图谱检索模块
│   └── article_extractor.py  # 法条解析模块
└── README-upstream.md        # DISC-LawLLM 原项目说明
```

## Vector RAG

当前向量检索采用 `reference-level chunking`：

- 每条 `reference` 法律依据作为一个检索单元
- 使用文本内容的 MD5 前 16 位作为稳定 ID，相同 reference 自动去重
- 使用 `bge-base-zh-v1.5` 生成向量，Chroma 持久化到 `rag/law_db`
- 查询时返回 Top-k 相关法律依据，拼接到用户问题前作为上下文

## Legal GraphRAG

纯向量检索只能找到语义相似的法条，难以显式表达"共同适用""相邻条文"等法律结构关系。本项目构建了轻量级法条图谱。

### 节点

| Node | Meaning |
|------|---------|
| `Article` | 法条 / reference 级法律依据节点 |

### 关系

| Relation | Meaning | Source |
|----------|---------|--------|
| `CO_CITED` | 同一个 Triplet 样本中共同出现的法条 | DISC-Law-SFT-Triplet reference |
| `SAME_LAW_ADJACENT` | 同一部法律中的相邻条文（距离 ≤ 3） | 法律名称与条号解析 |

`CO_CITED` 是本项目的核心图关系，将 Triplet 样本中的多法条共同引用关系转化为图谱边，使系统能够在向量召回种子法条后，进一步扩展法律问答中经常联合适用的相关条文。

## 数据与模型

本项目使用以下公开资源：

- DISC-Law-SFT 数据集：[ShengbinYue/DISC-Law-SFT](https://huggingface.co/datasets/ShengbinYue/DISC-Law-SFT)
- Embedding 模型：[BAAI/bge-base-zh-v1.5](https://huggingface.co/BAAI/bge-base-zh-v1.5)
- 向量库：Chroma
- 图数据库：Neo4j

由于数据集、模型权重和向量库体积较大，本仓库不上传以下内容：

```
data/DISC-Law-SFT/
models/
rag/law_db/
```

请自行下载数据和模型，按项目说明放置到对应目录。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 构建向量库

```bash
python build_vector_db.py
```

### 3. 构建图数据库（需本地运行 Neo4j）

```bash
python build_graph_db.py
```

### 4. 启动命令行 Demo

```bash
python cli_demo.py
```

### 5. 启动 Web Demo

```bash
streamlit run web_demo.py
```

## 版本路线

| Version | Module | Status |
|---------|--------|--------|
| v0.1 | Retrieval Module: Vector RAG + Legal GraphRAG | Done |
| v0.2 | Retrieval Evaluation: Recall@k / MRR / Evidence Coverage | Planned |
| v0.3 | LoRA SFT / RAG-SFT with DISC-Law-SFT Pair & Triplet | Planned |
| v0.4 | vLLM + FastAPI Service Deployment | Planned |
| v0.5 | End-to-End Evaluation and Demo Release | Planned |

## 当前局限

- 当前版本依赖 DISC-Law-SFT-Triplet 中人工构造的 `reference` 字段，尚未覆盖真实法规库中的复杂版式
- `reference-level chunking` 在多法条 reference 场景下可能造成向量语义稀释
- `SAME_LAW_ADJACENT` 只是弱关系，相邻条文不一定共同适用
- 当前版本主要完成检索链路，尚未完成系统性检索评测、LoRA 微调和 vLLM 服务化部署

## 致谢

本项目基于以下开源项目和公开资源：

- [DISC-LawLLM](https://github.com/FudanDISC/DISC-LawLLM)
- [DISC-Law-SFT](https://huggingface.co/datasets/ShengbinYue/DISC-Law-SFT)
- [BGE Embedding](https://huggingface.co/BAAI/bge-base-zh-v1.5)
- [Chroma](https://github.com/chroma-core/chroma)
- [Neo4j](https://neo4j.com/)

原 DISC-LawLLM 项目说明见 [README-upstream.md](./README-upstream.md)。

## Disclaimer

本项目仅用于学习、研究和工程实验，不构成法律意见，也不能替代专业律师或法律机构的判断。
