from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from backend.core.config import settings
from decimal import Decimal

engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def _serialize_row(row: dict) -> dict:
    """Convert non-JSON-serializable types (Decimal, etc.) to Python builtins."""
    return {
        k: float(v) if isinstance(v, Decimal) else v
        for k, v in row.items()
    }


async def init_db():
    async with engine.begin() as conn:
        # Just verify connectivity
        await conn.execute(text("SELECT 1"))
    print("✅ PostgreSQL connected")


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def execute_query(sql: str, params: dict = None) -> list[dict]:
    """Safe read-only query execution. Only allows SELECT statements."""
    stripped = sql.strip().upper()
    if not stripped.startswith("SELECT"):
        raise ValueError("Only SELECT queries allowed via this interface")

    async with AsyncSessionLocal() as session:
        result = await session.execute(text(sql), params or {})
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return [_serialize_row(r) for r in rows]


async def get_schema() -> dict:
    """Returns all table names and their columns."""
    sql = """
    SELECT
        table_name,
        column_name,
        data_type,
        is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position
    """
    rows = await execute_query(sql)
    schema: dict = {}
    for row in rows:
        table = row["table_name"]
        if table not in schema:
            schema[table] = []
        schema[table].append({
            "column": row["column_name"],
            "type": row["data_type"],
            "nullable": row["is_nullable"],
        })
    return schema


async def insert_pgvector_document(doc_id: str, content: str, embedding: list[float], metadata: dict = None) -> bool:
    """Insert a document chunk with its embedding into the PostgreSQL pgvector table."""
    import json
    emb_str = f"[{','.join(str(x) for x in embedding)}]"
    meta_json = json.dumps(metadata or {})
    sql = """
    INSERT INTO document_embeddings (doc_id, content, embedding, metadata)
    VALUES (:doc_id, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(text(sql), {
                "doc_id": doc_id,
                "content": content,
                "embedding": emb_str,
                "metadata": meta_json,
            })
    return True


async def search_pgvector(embedding: list[float], top_k: int = 5, doc_type: str = None) -> list[dict]:
    """Execute cosine similarity vector search using PostgreSQL pgvector HNSW index."""
    import json
    emb_str = f"[{','.join(str(x) for x in embedding)}]"
    sql = """
    SELECT
        doc_id,
        content,
        metadata,
        ROUND((1 - (embedding <=> CAST(:emb AS vector)))::numeric, 3) AS similarity
    FROM document_embeddings
    WHERE (:doc_type IS NULL OR metadata->>'doc_type' = :doc_type)
    ORDER BY embedding <=> CAST(:emb AS vector)
    LIMIT :limit
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(text(sql), {
            "emb": emb_str,
            "doc_type": doc_type,
            "limit": top_k,
        })
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return [_serialize_row(r) for r in rows]
