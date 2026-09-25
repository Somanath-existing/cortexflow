from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.api.routes import chat, documents, analytics
from backend.db.postgres import init_db
from backend.db.neo4j import init_neo4j, seed_knowledge_graph


import asyncio


async def _background_seed_indexing():
    try:
        from qdrant_client import QdrantClient
        from backend.core.config import settings
        from backend.rag.indexer import init_collection, index_all_documents, COLLECTION

        qdrant = QdrantClient(url=settings.qdrant_url)
        await init_collection(qdrant)

        # Check if already indexed in Qdrant
        count_result = qdrant.count(collection_name=COLLECTION)
        if count_result.count == 0:
            print("📚 Background indexing seed documents into Qdrant & pgvector...")
            await index_all_documents(qdrant, "/app/documents")
            print("✅ Background document indexing complete!")
        else:
            print(f"📚 Qdrant already has {count_result.count} document chunks")
            # Also check if PostgreSQL pgvector has rows
            try:
                from backend.db.postgres import execute_query
                pg_rows = await execute_query("SELECT COUNT(*) AS cnt FROM document_embeddings")
                if pg_rows and pg_rows[0].get("cnt", 0) == 0:
                    print("📚 Seeding document chunks into PostgreSQL pgvector...")
                    await index_all_documents(qdrant, "/app/documents")
                    print("✅ PostgreSQL pgvector seeded successfully!")
            except Exception as pg_err:
                print(f"⚠️  pgvector seed check note: {pg_err}")
    except Exception as e:
        print(f"⚠️  Document indexing warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    print("🚀 Starting CortexFlow backend...")

    # 1. PostgreSQL
    await init_db()

    # 2. Neo4j (optional — warn if down)
    try:
        await init_neo4j()
        await seed_knowledge_graph()
    except Exception as e:
        print(f"⚠️  Neo4j init warning: {e}")

    # 3. Index seed documents into Qdrant in background (non-blocking)
    asyncio.create_task(_background_seed_indexing())

    print("✅ CortexFlow backend ready")
    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    print("🛑 CortexFlow backend shutting down...")


app = FastAPI(
    title="CortexFlow API",
    description="MCP-Powered Autonomous Enterprise Data Worker",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cortexflow"}
