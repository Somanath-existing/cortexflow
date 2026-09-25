from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.core.config import settings
import asyncio

router = APIRouter()

# Lazy QdrantClient — NOT initialized at module level to avoid import-time crash
_qdrant = None
_qdrant_lock = asyncio.Lock()


async def get_qdrant():
    """Return a shared QdrantClient, initializing it lazily."""
    global _qdrant
    if _qdrant is None:
        async with _qdrant_lock:
            if _qdrant is None:
                from qdrant_client import QdrantClient
                _qdrant = QdrantClient(url=settings.qdrant_url)
    return _qdrant


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = "report",
):
    """Upload and index a document into both Qdrant and pgvector."""
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=400, detail="File must be readable text (UTF-8 or Latin-1)")

    # Lazy imports to avoid loading heavy models at startup
    from backend.rag.indexer import index_document, init_collection

    qdrant = await get_qdrant()
    await init_collection(qdrant)

    doc_id = file.filename or "uploaded_doc.txt"
    title = doc_id.replace("_", " ").rsplit(".", 1)[0].title()

    chunks = await index_document(qdrant, text, {
        "doc_id": doc_id,
        "title": title,
        "doc_type": doc_type,
        "source": doc_id,
        "file_name": doc_id,
    })

    return {
        "status": "success",
        "doc_id": doc_id,
        "title": title,
        "doc_type": doc_type,
        "chunks": chunks,
        "message": f"Successfully indexed {chunks} chunks from {doc_id} into Qdrant & pgvector",
    }


@router.get("/list")
async def list_documents():
    """List all Qdrant collections."""
    try:
        qdrant = await get_qdrant()
        collections = qdrant.get_collections()
        return {"collections": [c.name for c in collections.collections]}
    except Exception as e:
        return {"error": str(e), "collections": []}


@router.get("/items")
async def list_document_items():
    """List distinct indexed documents with metadata from Qdrant / pgvector."""
    docs = []
    # 1. Try querying pgvector table
    try:
        from backend.db.postgres import execute_query
        rows = await execute_query("""
            SELECT
                doc_id,
                metadata->>'title' AS title,
                metadata->>'doc_type' AS doc_type,
                COUNT(*) AS chunk_count,
                MIN(created_at) AS created_at
            FROM document_embeddings
            GROUP BY doc_id, metadata->>'title', metadata->>'doc_type'
            ORDER BY created_at DESC
        """)
        if rows:
            for r in rows:
                docs.append({
                    "doc_id": r["doc_id"],
                    "title": r["title"] or r["doc_id"],
                    "doc_type": r["doc_type"] or "report",
                    "chunk_count": r["chunk_count"],
                    "source": "PostgreSQL pgvector & Qdrant",
                    "created_at": str(r["created_at"]) if r.get("created_at") else None,
                })
            return {"documents": docs, "total": len(docs)}
    except Exception:
        pass

    # 2. Fallback to scrolling Qdrant points
    try:
        from backend.rag.indexer import COLLECTION
        qdrant = await get_qdrant()
        records, _ = qdrant.scroll(collection_name=COLLECTION, limit=100, with_payload=True)
        seen = {}
        for rec in records:
            p = rec.payload or {}
            d_id = p.get("doc_id") or p.get("file_name") or "unknown"
            if d_id not in seen:
                seen[d_id] = {
                    "doc_id": d_id,
                    "title": p.get("title") or d_id,
                    "doc_type": p.get("doc_type") or "report",
                    "chunk_count": 1,
                    "source": "Qdrant",
                }
            else:
                seen[d_id]["chunk_count"] += 1
        docs = list(seen.values())
        return {"documents": docs, "total": len(docs)}
    except Exception as e:
        return {"documents": [], "total": 0, "error": str(e)}
