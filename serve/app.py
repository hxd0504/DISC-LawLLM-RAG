"""
FastAPI service for Legal RAG / GraphRAG Q&A.
vLLM is called via OpenAI-compatible API — no model loading here.
"""
import os
import yaml
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI

from rag.vector_retriever import VectorRetriever
from rag.graph_retriever import GraphRetriever

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_cfg_path = Path(__file__).parent / "config.yaml"
with open(_cfg_path, encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

_vcfg = CFG["vllm"]
_rcfg = CFG["retriever"]

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["vector"] = VectorRetriever(persist_dir=_rcfg["chroma_dir"])
    try:
        state["graph"] = GraphRetriever(
            persist_dir=_rcfg["chroma_dir"],
            neo4j_uri=_rcfg["neo4j_uri"],
            user=_rcfg["neo4j_user"],
            password=_rcfg["neo4j_password"],
            top_k=_rcfg["top_k"],
        )
    except Exception:
        state["graph"] = None  # Neo4j unavailable — graph endpoints will 503

    state["llm"] = OpenAI(base_url=_vcfg["base_url"], api_key="EMPTY")
    yield
    if state.get("graph"):
        state["graph"].close()


app = FastAPI(title="LegalRAG API", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    max_tokens: int = 512

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = "你是一名专业法律助手，请根据给定法律依据准确回答问题。"

def _chat(context: str, query: str, max_tokens: int) -> str:
    user_msg = f"{context}【问题】\n{query}" if context else query
    resp = state["llm"].chat.completions.create(
        model=_vcfg["model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "model": _vcfg["model"]}


@app.post("/retrieve/vector")
def retrieve_vector(req: QueryRequest):
    docs = state["vector"].retrieve(req.query, top_k=req.top_k)
    return {"query": req.query, "results": docs}


@app.post("/retrieve/graph")
def retrieve_graph(req: QueryRequest):
    if not state.get("graph"):
        raise HTTPException(503, "Neo4j unavailable")
    result = state["graph"].retrieve(req.query, top_k=req.top_k)
    return {"query": req.query, **result}


@app.post("/chat/rag")
def chat_rag(req: ChatRequest):
    context = state["vector"].format_context(req.query, top_k=req.top_k)
    answer = _chat(context, req.query, req.max_tokens)
    return {"query": req.query, "answer": answer}


@app.post("/chat/graphrag")
def chat_graphrag(req: ChatRequest):
    if not state.get("graph"):
        raise HTTPException(503, "Neo4j unavailable")
    context = state["graph"].format_context(req.query, top_k=req.top_k)
    answer = _chat(context, req.query, req.max_tokens)
    return {"query": req.query, "answer": answer}
