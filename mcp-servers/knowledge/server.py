"""
Knowledge/RAG MCP Server — exposes document search over HTTP.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import json

app = FastAPI(title="CortexFlow Knowledge MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = "cortexflow_documents"

# Lazy globals — initialized on startup
_qdrant = None
_embedder = None


@app.on_event("startup")
async def startup():
    global _qdrant, _embedder
    try:
        from qdrant_client import QdrantClient
        _qdrant = QdrantClient(url=QDRANT_URL)
        print(f"✅ MCP-Knowledge: Qdrant connected at {QDRANT_URL}")
    except Exception as e:
        print(f"⚠️  MCP-Knowledge: Qdrant connection failed: {e}")

    try:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)
        print("✅ MCP-Knowledge: Embedder loaded")
    except Exception as e:
        print(f"⚠️  MCP-Knowledge: Embedder load failed: {e}")


def _collection_exists() -> bool:
    if not _qdrant:
        return False
    try:
        existing = [c.name for c in _qdrant.get_collections().collections]
        return COLLECTION in existing
    except Exception:
        return False


TOOLS = [
    {
        "name": "search_documents",
        "description": "Semantically search enterprise documents, reports, and policies.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 5},
                "doc_type": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_document",
        "description": "Retrieve the full content of a specific document by its ID.",
        "inputSchema": {
            "type": "object",
            "properties": {"doc_id": {"type": "string"}},
            "required": ["doc_id"],
        },
    },
    {
        "name": "find_policy",
        "description": "Find company policies and guidelines relevant to a topic.",
        "inputSchema": {
            "type": "object",
            "properties": {"topic": {"type": "string"}},
            "required": ["topic"],
        },
    },
]


@app.get("/tools/list")
async def list_tools():
    return {"tools": TOOLS}


@app.post("/tools/call")
async def call_tool(request: dict):
    name = request.get("name")
    arguments = request.get("arguments", {})

    if not _qdrant or not _embedder:
        return {"content": [{"type": "text", "text": "Knowledge server initializing — please retry in a moment."}]}

    if not _collection_exists():
        return {"content": [{"type": "text", "text": "No documents indexed yet. The system will index documents automatically on startup."}]}

    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        if name == "search_documents":
            query = arguments["query"]
            top_k = min(arguments.get("top_k", 5), 10)
            doc_type = arguments.get("doc_type")

            query_vector = _embedder.encode(query).tolist()

            filter_condition = None
            if doc_type:
                filter_condition = Filter(
                    must=[FieldCondition(key="doc_type", match=MatchValue(value=doc_type))]
                )

            results = _qdrant.search(
                collection_name=COLLECTION,
                query_vector=query_vector,
                limit=top_k,
                query_filter=filter_condition,
                with_payload=True,
            )

            formatted = [
                {
                    "doc_id": r.payload.get("doc_id"),
                    "title": r.payload.get("title"),
                    "doc_type": r.payload.get("doc_type"),
                    "content_snippet": r.payload.get("content", "")[:600],
                    "relevance_score": round(r.score, 3),
                    "source": r.payload.get("source"),
                }
                for r in results
            ]
            return {"content": [{"type": "text", "text": json.dumps(formatted, indent=2)}]}

        elif name == "get_document":
            doc_id = arguments["doc_id"]
            results, _ = _qdrant.scroll(
                collection_name=COLLECTION,
                scroll_filter=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                ),
                limit=1,
                with_payload=True,
            )
            if results:
                return {"content": [{"type": "text", "text": json.dumps(dict(results[0].payload), indent=2)}]}
            return {"content": [{"type": "text", "text": "Document not found"}]}

        elif name == "find_policy":
            topic = arguments["topic"]
            query_vector = _embedder.encode(f"company policy guidelines {topic}").tolist()

            results = _qdrant.search(
                collection_name=COLLECTION,
                query_vector=query_vector,
                limit=3,
                query_filter=Filter(
                    must=[FieldCondition(key="doc_type", match=MatchValue(value="policy"))]
                ),
                with_payload=True,
            )

            policies = [
                {
                    "title": r.payload.get("title"),
                    "content": r.payload.get("content", "")[:1000],
                }
                for r in results
            ]
            return {"content": [{"type": "text", "text": json.dumps(policies, indent=2)}]}

        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "mcp-knowledge",
        "qdrant_connected": _qdrant is not None,
        "embedder_loaded": _embedder is not None,
        "collection_exists": _collection_exists(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
