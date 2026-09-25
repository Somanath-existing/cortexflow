"""
Run this script after docker-compose up to index documents into Qdrant.
Usage: python data/seed/seed_documents.py
"""
import asyncio
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid
import os

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = "cortexflow_documents"
VECTOR_DIM = 768
DOCS_PATH = Path(os.getenv("DOCS_PATH", Path(__file__).parent.parent / "documents"))


def semantic_chunk(text: str, chunk_size: int = 400) -> list[str]:
    sentences = text.replace('\n', ' ').split('. ')
    chunks = []
    current_chunk = []
    current_size = 0
    for sentence in sentences:
        words = sentence.split()
        if current_size + len(words) > chunk_size and current_chunk:
            chunks.append('. '.join(current_chunk) + '.')
            current_chunk = []
            current_size = 0
        current_chunk.append(sentence)
        current_size += len(words)
    if current_chunk:
        chunks.append('. '.join(current_chunk))
    return chunks if chunks else [text]


async def main():
    print(f"Connecting to Qdrant at {QDRANT_URL}...")
    qdrant = QdrantClient(url=QDRANT_URL)

    # Create collection
    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION in existing:
        print(f"Collection '{COLLECTION}' already exists. Recreating...")
        qdrant.delete_collection(COLLECTION)

    qdrant.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
    )
    print(f"✅ Created collection: {COLLECTION}")

    print("Loading embedding model...")
    embedder = SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)

    total_chunks = 0
    for file_path in DOCS_PATH.rglob("*.txt"):
        content = file_path.read_text(encoding="utf-8")
        doc_type = file_path.parent.name
        chunks = semantic_chunk(content)
        points = []

        for i, chunk in enumerate(chunks):
            embedding = embedder.encode(chunk).tolist()
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "doc_id": file_path.stem,
                    "title": file_path.stem.replace("_", " ").title(),
                    "doc_type": doc_type,
                    "source": str(file_path),
                    "file_name": file_path.name,
                    "content": chunk,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            ))

        qdrant.upsert(collection_name=COLLECTION, points=points)
        total_chunks += len(chunks)
        print(f"  ✅ Indexed: {file_path.name} ({len(chunks)} chunks)")

    print(f"\n✅ Done. Total chunks indexed: {total_chunks}")


if __name__ == "__main__":
    asyncio.run(main())
