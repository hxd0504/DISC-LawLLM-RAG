# LegalRAG-Qwen2.5

基于 DISC-Law-SFT 公开数据集构建的中文法律问答检索增强系统。  
本项目围绕法律问答中的外部知识利用问题，完成了法条向量库、法条知识图谱与 GraphRAG 检索增强链路的实现。

当前版本包含三部分：

1. **Vector RAG**：基于 BGE + Chroma 的法律依据语义检索；
2. **Legal Knowledge Graph**：基于 Triplet reference 共现关系构建 Neo4j 法条图谱；
3. **GraphRAG**：在向量召回基础上沿法条图谱扩展相关证据。

> 本项目是基于 DISC-LawLLM 与 DISC-Law-SFT 的非官方扩展版本，不代表原项目官方实现。原项目说明见 [README-upstream.md](./README-upstream.md)。

## 当前版本

**v0.1 Retrieval + KG Module：Vector RAG + Legal KG + GraphRAG**

当前版本已完成：

- 基于 DISC-Law-SFT-Triplet 的 `reference` 字段构建法律依据文本集合；
- 使用 `bge-base-zh-v1.5` 与 Chroma 构建法条向量库；
- 实现 `VectorRetriever`，支持 Top-k 法律依据语义召回；
- 从 reference 中解析法律名称、条号与原文，构建 Neo4j 法条知识图谱；
- 基于同一样本内法条共现关系构建 `CO_CITED` 边；
- 基于法律名称与条号顺序构建 `SAME_LAW_ADJACENT` 边；
- 基于 embedding 相似度构建 `SIMILAR` 边（预留接口）；
- 实现 `GraphRetriever`，支持"向量召回种子法条 + 图谱邻域扩展"的 GraphRAG 检索流程；
- 将 Vector RAG / GraphRAG 接入 CLI 与 Web 端的 Prompt 增强流程。

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

## Project Structure

```
.
├── build_vector_db.py          # 构建 Chroma 法条向量库
├── build_graph_db.py           # 构建 Neo4j 法条知识图谱
├── cli_demo.py                 # 命令行问答入口
├── web_demo.py                 # Web 问答入口
├── graph_retriever_demo.py     # GraphRetriever 独立测试脚本
├── rag/
│   ├── vector_retriever.py     # Vector RAG 检索器
│   ├── graph_retriever.py      # GraphRAG 检索器（基于图谱扩展相关法条）
│   └── article_extractor.py    # 法条解析模块（法律名称、条号、原文）
└── README-upstream.md          # DISC-LawLLM 原项目说明
```

## Vector RAG

当前向量检索采用 `reference-level chunking`：

- 每条 `reference` 法律依据作为一个检索单元
- 使用文本内容的 MD5 前 16 位作为稳定 ID，相同 reference 自动去重
- 使用 `bge-base-zh-v1.5` 生成向量，Chroma 持久化到 `rag/law_db`
- 查询时返回 Top-k 相关法律依据，拼接到用户问题前作为上下文

## Legal Knowledge Graph

在向量检索模块之外，本项目进一步构建了一个轻量级法律知识图谱，用于显式表达法条之间的结构关系。

知识图谱的数据来源是 `DISC-Law-SFT-Triplet` 中的 `reference` 字段。系统会从每条 reference 中解析法律名称、条号和原始文本，并将其组织为法条级节点。

### Node Schema

| Node | Description |
|------|-------------|
| `Article` | 法条 / reference 级法律依据节点 |

### Article Properties

| Property | Description |
|----------|-------------|
| `doc_id` | 法条节点稳定 ID，由 reference 原文 MD5 前 16 位生成 |
| `law_name` | 法律名称，例如《中华人民共和国刑法》 |
| `article_num` | 条号，例如第二百六十四条 |
| `text` | 法条或 reference 原文 |
| `freq` | 该法条在 Triplet 数据中出现的次数 |

### Edge Schema

| Relation | Description | Source |
|----------|-------------|--------|
| `CO_CITED` | 同一个 Triplet 样本中共同出现的法条 | reference 共现关系 |
| `SAME_LAW_ADJACENT` | 同一部法律中条号相邻或接近的法条（距离 ≤ 3） | 法律名称与条号解析 |
| `SIMILAR` | embedding 余弦相似度超过阈值的法条 | BGE 向量相似度（预留） |

`CO_CITED` 是当前知识图谱中最核心的关系。它将 Triplet 样本中的多法条共同引用现象转化为图谱边，用来表达法律问答场景中经常联合适用的条文组合。

当前图谱规模：181 个 Article 节点，664 条 CO_CITED 边，365 条 SAME_LAW_ADJACENT 边。

## Legal GraphRAG

Legal GraphRAG 是基于上述法律知识图谱实现的检索增强模块。

其检索流程如下：

```
用户问题
    ↓
BGE 编码 query
    ↓
VectorRetriever 从 Chroma 中召回 Top-k seed reference
    ↓
根据 seed reference 定位 Neo4j 中的 Article 节点
    ↓
沿 CO_CITED / SAME_LAW_ADJACENT 边扩展 1-hop 相关法条
    ↓
合并向量召回结果与图谱扩展结果
    ↓
构造结构化法律依据上下文
    ↓
DISC-LawLLM / Qwen2.5 生成回答
```

与纯向量 RAG 相比，GraphRAG 不只依赖语义相似度，还能利用法条之间的共引关系和结构关系补充相关证据。

若 Neo4j 不可用，`GraphRetriever` 会自动降级为 `VectorRetriever`。

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
| v0.1 | Retrieval + KG Module: Vector RAG, Legal KG, GraphRAG | Done |
| v0.2 | LoRA RAG-SFT Pilot: Qwen2.5-7B + LLaMA-Factory + 5K Triplet | Done |
| v0.3 | Evidence Quality Control + GraphRAG Reranking | Planned |
| v0.4 | Retrieval Evaluation: Recall@k / MRR / Evidence Coverage | Planned |
| v0.5 | vLLM + FastAPI Service Deployment | Planned |
| — | Full SFT | Optional, not on main roadmap |

## 当前局限

- 当前版本依赖 DISC-Law-SFT-Triplet 中人工构造的 `reference` 字段，尚未覆盖真实法规库中的复杂版式
- `reference-level chunking` 在多法条 reference 场景下可能造成向量语义稀释
- `SAME_LAW_ADJACENT` 只是弱关系，相邻条文不一定共同适用
- `SIMILAR` 边尚未实现，当前图谱仅包含 CO_CITED 和 SAME_LAW_ADJACENT
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
