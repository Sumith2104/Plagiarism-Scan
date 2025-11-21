from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.scan import Scan, ScanStatus
from app.core.ml import Chunker, EmbeddingModel
from app.db.vector import VectorDB

class DetectionEngine:
    def __init__(self, db: Session):
        self.db = db
        self.vector_db = VectorDB()
        self.chunker = Chunker()
        self.embedding_model = EmbeddingModel.get_instance()

    def run_scan(self, scan_id: int):
        scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            print(f"Scan {scan_id} not found")
            return

        try:
            scan.status = ScanStatus.SCANNING
            self.db.commit()

            doc = scan.document
            if not doc or not doc.extracted_text:
                raise ValueError("Document has no text to scan")

            # 1. Chunking
            chunks = self.chunker.chunk_text(doc.extracted_text)
            if not chunks:
                raise ValueError("No chunks generated")

            # 2. Generate Embeddings for Query
            embeddings = self.embedding_model.encode(chunks)

            # 3. Semantic Search
            matches = []
            total_similarity = 0.0
            matched_chunks_count = 0

            for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                # Search for similar vectors
                # Exclude current document from results (filter logic needed in VectorDB)
                # For MVP, we'll just filter in python
                results = self.vector_db.search(vector, limit=5, score_threshold=0.8)
                
                chunk_matches = []
                for res in results:
                    if str(res["document_id"]) == str(doc.id):
                        continue # Skip self-match
                    
                    chunk_matches.append({
                        "source_doc_id": res["document_id"],
                        "text": res["text"],
                        "score": res["score"]
                    })
                
                if chunk_matches:
                    best_match = max(chunk_matches, key=lambda x: x["score"])
                    matches.append({
                        "chunk_index": i,
                        "chunk_text": chunk,
                        "best_match": best_match
                    })
                    total_similarity += best_match["score"]
                    matched_chunks_count += 1

            # 4. Score Calculation (Simple Average of Matched Chunks)
            # This is a naive score. A better score would consider coverage.
            overall_score = 0.0
            if len(chunks) > 0:
                # Percentage of chunks that had a match > threshold
                overall_score = (matched_chunks_count / len(chunks)) * 100

            # 5. AI Detection (Heuristic)
            ai_analysis = self._detect_ai_content(doc.extracted_text)

            # 6. Update Scan Result
            scan.overall_score = round(overall_score, 2)
            scan.report_data = {
                "total_chunks": len(chunks),
                "matched_chunks": matched_chunks_count,
                "matches": matches,
                "ai_detection": ai_analysis
            }
            scan.status = ScanStatus.COMPLETED
            self.db.commit()
            print(f"Scan {scan_id} completed. Score: {overall_score}")

        except Exception as e:
            print(f"Scan failed: {e}")
            scan.status = ScanStatus.FAILED
            scan.report_data = {"error": str(e)}
            self.db.commit()
            import traceback
            traceback.print_exc()

    def _detect_ai_content(self, text: str) -> Dict[str, Any]:
        """
        ML-Based AI Detection using RoBERTa
        Uses a pre-trained Transformer model to classify text as Real vs Fake (AI).
        """
        try:
            from transformers import pipeline
            
            # Truncate text to 512 tokens (model limit) to avoid errors
            # A rough char limit of 2000 is safe for 512 tokens
            truncated_text = text[:2000]
            
            if len(truncated_text) < 50:
                 return {"ai_probability": 0, "label": "Insufficient Data"}

            # Initialize pipeline (lazy load would be better for performance, but this is safer for now)
            # Using a standard model for AI detection
            # Note: First run will download the model (~500MB)
            classifier = pipeline("text-classification", model="roberta-base-openai-detector")
            
            result = classifier(truncated_text)[0]
            # result is like {'label': 'Fake', 'score': 0.99} or {'label': 'Real', 'score': 0.99}
            
            label = result['label'] # 'Fake' (AI) or 'Real' (Human)
            score = result['score']
            
            ai_prob = 0.0
            if label == 'Fake':
                ai_prob = round(score * 100, 2)
            else:
                ai_prob = round((1 - score) * 100, 2)
                
            display_label = "Human"
            if ai_prob > 90:
                display_label = "AI Generated"
            elif ai_prob > 60:
                display_label = "Likely AI"
            elif ai_prob > 40:
                display_label = "Mixed / Unsure"
            else:
                display_label = "Human"

            return {
                "ai_probability": ai_prob,
                "label": display_label,
                "details": {
                    "model": "roberta-base-openai-detector",
                    "raw_label": label,
                    "confidence": round(score, 4)
                }
            }
            
        except Exception as e:
            print(f"ML Detection failed: {e}")
            # Fallback to heuristic if ML fails (e.g. model download error)
            return {"ai_probability": 0, "label": "Error", "details": {"error": str(e)}}
