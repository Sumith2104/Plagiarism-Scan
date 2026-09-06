# from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
from typing import List, Dict, Any
import uuid

# ─────────────────────────────────────────────────────────────
# SINGLETON: Qdrant local mode only supports ONE open connection
# at a time. We keep one global client for the entire app.
# ─────────────────────────────────────────────────────────────
_qdrant_singleton = None

def _get_global_client():
    global _qdrant_singleton
    if _qdrant_singleton is not None:
        return _qdrant_singleton

    from qdrant_client import QdrantClient
    if settings.QDRANT_URL and settings.QDRANT_URL not in (":memory:", "local"):
        _qdrant_singleton = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
    else:
        import os
        storage_path = os.path.abspath("qdrant_storage")
        os.makedirs(storage_path, exist_ok=True)
        try:
            _qdrant_singleton = QdrantClient(path=storage_path)
        except Exception as lock_err:
            print(f"WARNING: Qdrant storage locked: {lock_err}. Falling back to in-memory mode.")
            _qdrant_singleton = QdrantClient(":memory:")

    # Ensure collection exists
    collection_name = "plagiascan_chunks"
    try:
        _qdrant_singleton.get_collection(collection_name)
    except Exception:
        try:
            print(f"Creating Qdrant collection: {collection_name}")
            _qdrant_singleton.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
            )
        except Exception as create_err:
            print(f"WARNING: Could not create collection: {create_err}")

    return _qdrant_singleton


class VectorDB:
    def __init__(self):
        self.collection_name = "plagiascan_chunks"

    def _get_client(self):
        """Always return the process-wide singleton client."""
        return _get_global_client()

    def upsert_chunks(self, document_id: int, chunks: List[str], embeddings: List[List[float]]):
        client = self._get_client()
        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}_{i}"))
            points.append(models.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "document_id": document_id,
                    "chunk_index": i,
                    "text": chunk
                }
            ))

        client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        print(f"Upserted {len(points)} chunks for document {document_id}")

    def search(self, vector: List[float], limit: int = 5, score_threshold: float = 0.7, exclude_document_id: int = None) -> List[Dict[str, Any]]:
        client = self._get_client()

        filter_condition = None
        if exclude_document_id is not None:
            filter_condition = models.Filter(
                must_not=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=exclude_document_id)
                    )
                ]
            )

        try:
            results = client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filter_condition
            )
        except Exception:
            try:
                response = client.query_points(
                    collection_name=self.collection_name,
                    query=vector,
                    limit=limit,
                    score_threshold=score_threshold,
                    query_filter=filter_condition,
                    with_payload=True
                )
                results = response.points
            except Exception as ex:
                print(f"Vector search exception: {ex}")
                return []

        return [
            {
                "document_id": hit.payload["document_id"],
                "chunk_index": hit.payload["chunk_index"],
                "text": hit.payload["text"],
                "score": hit.score
            }
            for hit in results
        ]

    def delete_document(self, document_id: int):
        """Delete all chunks associated with a document."""
        client = self._get_client()
        try:
            filter_condition = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id)
                    )
                ]
            )
            client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=filter_condition
                )
            )
            print(f"Deleted vectors for document {document_id}")
        except Exception as e:
            print(f"Failed to delete vectors for document {document_id}: {e}")
