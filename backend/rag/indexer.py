from pathlib import Path
import uuid

COLLECTION = "cortexflow_documents"
VECTOR_DIM = 768

# Lazy embedder — only loaded on first use to avoid slow container startup
_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(
            "nomic-ai/nomic-embed-text-v1",
            trust_remote_code=True,
        )
    return _embedder


async def init_collection(qdrant):
    """Create Qdrant collection if it doesn't exist."""
    from qdrant_client.models import Distance, VectorParams

    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
        print(f"✅ Created Qdrant collection: {COLLECTION}")


async def index_document(qdrant, content: str, metadata: dict) -> int:
    """Index a document with semantic chunking. Returns number of chunks indexed."""
    from qdrant_client.models import PointStruct

    embedder = get_embedder()
    chunks = semantic_chunk(content)
    points = []

    for i, chunk in enumerate(chunks):
        embedding = embedder.encode(chunk).tolist()
        chunk_meta = {
            **metadata,
            "content": chunk,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=chunk_meta,
            )
        )
        # Also index into pgvector
        try:
            from backend.db.postgres import insert_pgvector_document
            await insert_pgvector_document(
                doc_id=metadata.get("doc_id", "doc"),
                content=chunk,
                embedding=embedding,
                metadata=chunk_meta,
            )
        except Exception as pg_err:
            pass  # Fail gracefully if table not yet migrated

    qdrant.upsert(collection_name=COLLECTION, points=points)
    return len(points)


def semantic_chunk(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks respecting sentence boundaries."""
    sentences = text.replace("\n", " ").split(". ")
    chunks = []
    current_chunk: list[str] = []
    current_size = 0

    for sentence in sentences:
        words = sentence.split()
        if current_size + len(words) > chunk_size and current_chunk:
            chunks.append(". ".join(current_chunk) + ".")
            overlap_sentences = current_chunk[-2:] if len(current_chunk) > 2 else current_chunk
            current_chunk = list(overlap_sentences)
            current_size = sum(len(s.split()) for s in current_chunk)

        current_chunk.append(sentence)
        current_size += len(words)

    if current_chunk:
        chunks.append(". ".join(current_chunk))

    return chunks if chunks else [text]


async def index_all_documents(qdrant, docs_path: str):
    """Index all .txt documents in a directory tree."""
    docs_dir = Path(docs_path)
    total = 0

    for file_path in docs_dir.rglob("*.txt"):
        try:
            content = file_path.read_text(encoding="utf-8")
            doc_type = file_path.parent.name  # reports / policies / product_docs

            chunks = await index_document(qdrant, content, {
                "doc_id": str(file_path.stem),
                "title": file_path.stem.replace("_", " ").title(),
                "doc_type": doc_type,
                "source": str(file_path),
                "file_name": file_path.name,
            })
            total += chunks
            print(f"  📄 Indexed: {file_path.name} ({chunks} chunks)")
        except Exception as e:
            print(f"  ⚠️  Failed to index {file_path.name}: {e}")

    print(f"✅ Total document chunks indexed: {total}")
    return total
