# LegalRAG 部署指南

## 依赖

```
fastapi
uvicorn
openai
pyyaml
chromadb
sentence-transformers
neo4j
```

```bash
pip install fastapi uvicorn openai pyyaml chromadb sentence-transformers neo4j
```

## 1. 启动 vLLM

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --port 8000 \
  --served-model-name Qwen/Qwen2.5-7B-Instruct
```

**可选：加载 LoRA adapter**

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --enable-lora \
  --lora-modules law_rag=saves/qwen2.5-7b/lora/law_rag_sft_5k \
  --port 8000
```

若使用 LoRA，将 `serve/config.yaml` 中 `vllm.model` 改为 `law_rag`，并取消注释 `lora_adapter`。

## 2. 启动 Neo4j（GraphRAG 需要）

确保 Neo4j 已运行并导入法条图谱：

```bash
# 默认端口 bolt://localhost:7687，用户名 neo4j，密码见 config.yaml
neo4j start
```

若不需要 GraphRAG，Neo4j 可不启动，`/retrieve/graph` 和 `/chat/graphrag` 会返回 503。

## 3. 启动 FastAPI

在项目根目录执行：

```bash
cd F:\pythoncode\大模型项目\DISC-LawLLM\DISC-LawLLM-main\DISC-LawLLM-main
uvicorn serve.app:app --host 0.0.0.0 --port 8001 --reload
```

## 4. 接口说明

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 服务状态 |
| POST | `/retrieve/vector` | 向量检索 Top-k 法条 |
| POST | `/retrieve/graph` | 图谱检索（seed + expanded） |
| POST | `/chat/rag` | Vector RAG 问答 |
| POST | `/chat/graphrag` | GraphRAG 问答 |

请求体（`/retrieve/*` 和 `/chat/*`）：

```json
{
  "query": "故意伤害轻伤二级如何量刑？",
  "top_k": 5,
  "max_tokens": 512
}
```

## 5. 示例请求

```bash
# 健康检查
curl http://localhost:8001/health

# 向量检索
curl -X POST http://localhost:8001/retrieve/vector \
  -H "Content-Type: application/json" \
  -d '{"query": "故意伤害轻伤二级如何量刑？", "top_k": 3}'

# RAG 问答
curl -X POST http://localhost:8001/chat/rag \
  -H "Content-Type: application/json" \
  -d '{"query": "故意伤害轻伤二级如何量刑？", "top_k": 3, "max_tokens": 256}'

# GraphRAG 问答
curl -X POST http://localhost:8001/chat/graphrag \
  -H "Content-Type: application/json" \
  -d '{"query": "故意伤害轻伤二级如何量刑？", "top_k": 3, "max_tokens": 256}'
```

示例响应（`/chat/rag`）：

```json
{
  "query": "故意伤害轻伤二级如何量刑？",
  "answer": "根据《刑法》第234条，故意伤害他人身体的，处三年以下有期徒刑、拘役或者管制。轻伤二级属于该条第一款适用范围，通常判处三年以下有期徒刑或拘役。"
}
```

## 注意事项

- `rag/law_db/`（Chroma 向量库）和 Neo4j 数据目录不上传 Git
- 模型权重不上传 Git
- 配置敏感信息（Neo4j 密码）可通过环境变量覆盖：`NEO4J_PASSWORD`
