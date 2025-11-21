from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
from typing import List, Dict, Any
import uuid

class VectorDB:
    def __init__(self):
        # Use settings for Qdrant configuration (Cloud or Local)
        if settings.QDRANT_URL and settings.QDRANT_URL != ":memory:":
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
        else:
            # Fallback to local storage if no URL provided
            self.client = QdrantClient(path="qdrant_storage")
        self.collection_name = "plagiascan_chunks"
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            print(f"Creating collection {self.collection_name}...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
            )

    def upsert_chunks(self, document_id: int, chunks: List[str], embeddings: List[List[float]]):
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
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        print(f"Upserted {len(points)} chunks for document {document_id}")

    def search(self, vector: List[float], limit: int = 5, score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        try:
            # Try using search first (standard API)
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit,
                score_threshold=score_threshold
            )
        except AttributeError:
            # Fallback to query_points (newer API or specific to local mode)
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True
            )
            results = response.points

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
        """Delete all chunks associated with a document"""
        try:
            # Create filter for document_id
            filter_condition = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id)
                    )
                ]
            )
            
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=filter_condition
                )
            )
            print(f"Deleted vectors for document {document_id}")
        except Exception as e:
            print(f"Failed to delete vectors for document {document_id}: {e}")
