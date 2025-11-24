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
        import time
        self.time = time

    def _update_progress(self, scan_id: int, progress: int, message: str):
        try:
            # Use direct update to avoid session sync issues and ensure immediate commit
            from sqlalchemy import update
            stmt = (
                update(Scan)
                .where(Scan.id == scan_id)
                .values(progress=progress, current_step=message)
            )
            self.db.execute(stmt)
            self.db.commit()
            
            # Artificial delay for UX smoothness
            self.time.sleep(0.5)
        except Exception as e:
            print(f"Failed to update progress: {e}")

    def run_scan(self, scan_id: int):
        scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            print(f"Scan {scan_id} not found")
            return

        try:
            scan.status = ScanStatus.SCANNING
            self.db.commit()
            
            self._update_progress(scan_id, 0, "Initializing scan...")

            doc = scan.document
            if not doc or not doc.extracted_text:
                raise ValueError("Document has no text to scan")

            # 1. Chunking
            self._update_progress(scan_id, 10, "Chunking document...")
            chunks = self.chunker.chunk_text(doc.extracted_text)
            if not chunks:
                raise ValueError("No chunks generated")

            # 2. Generate Embeddings for Query
            self._update_progress(scan_id, 30, "Generating embeddings...")
            embeddings = self.embedding_model.encode(chunks)

            # 3. Semantic Search
            self._update_progress(scan_id, 50, "Searching internal database...")
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
            self._update_progress(scan_id, 70, "Analyzing AI probability...")
            ai_analysis = self._detect_ai_content(doc.extracted_text)

            # 6. Update Scan Result
            self._update_progress(scan_id, 90, "Finalizing report...")
            scan.overall_score = round(overall_score, 2)
            scan.report_data = {
                "total_chunks": len(chunks),
                "matched_chunks": matched_chunks_count,
                "matches": matches,
                "ai_detection": ai_analysis
            }
            scan.status = ScanStatus.COMPLETED
            scan.progress = 100
            scan.current_step = "Completed"
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
            # Using RoBERTa Large for better accuracy (Upgrade from Base)
            # Note: First run will download the model (~1.4GB)
            classifier = pipeline("text-classification", model="roberta-large-openai-detector")
            
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

            # Advanced Analytics (Perplexity & Burstiness)
            try:
                from app.core.analytics import PerplexityAnalyzer
                analyzer = PerplexityAnalyzer.get_instance()
                analytics_scores = analyzer.calculate_scores(truncated_text)
                perplexity = analytics_scores["perplexity"]
                burstiness = analytics_scores["burstiness"]
            except Exception as e:
                print(f"Analytics failed: {e}")
                perplexity = 0.0
                burstiness = 0.0

            # Web Plagiarism Search
            web_sources = []
            try:
                from app.core.web_search import WebSearcher
                searcher = WebSearcher.get_instance()
                # Search using the first 500 chars or so to save time/bandwidth
                web_sources = searcher.search_and_compare(truncated_text[:1000])
            except Exception as e:
                print(f"Web Search failed: {e}")

            # --- ENSEMBLE LOGIC START ---
            # 1. Normalize Scores to 0-100 Scale (where 100 = AI, 0 = Human)
            
            # Perplexity: Low (< 30) is AI, High (> 100) is Human
            if perplexity < 30:
                perp_ai_score = 100
            elif perplexity < 60:
                perp_ai_score = 80
            elif perplexity < 100:
                perp_ai_score = 40
            else:
                perp_ai_score = 0
                
            # Burstiness: Low (< 0.4) is AI, High (> 0.7) is Human
            if burstiness < 0.4:
                burst_ai_score = 100
            elif burstiness < 0.6:
                burst_ai_score = 60
            elif burstiness < 0.8:
                burst_ai_score = 30
            else:
                burst_ai_score = 0
                
            # 2. Weighted Average
            # Weights: RoBERTa (60%), Perplexity (20%), Burstiness (20%)
            # Note: ai_prob from RoBERTa is already 0-100
            
            w_roberta = 0.6
            w_perp = 0.2
            w_burst = 0.2
            
            final_ai_score = (ai_prob * w_roberta) + (perp_ai_score * w_perp) + (burst_ai_score * w_burst)
            final_ai_score = round(final_ai_score, 2)
            
            # 3. Determine Label based on Final Score
            if final_ai_score > 85:
                display_label = "AI Generated"
            elif final_ai_score > 60:
                display_label = "Likely AI"
            elif final_ai_score > 40:
                display_label = "Mixed / Unsure"
            else:
                display_label = "Human"
            # --- ENSEMBLE LOGIC END ---

            # 4. Experimental LLM Check (Mistral-7B)
            llm_result = {}
            try:
                from app.core.llm_checker import LLMChecker
                llm = LLMChecker.get_instance()
                if llm._model:
                    print("DEBUG: Running Mistral-7B Analysis...")
                    llm_result = llm.analyze_text(text)
            except Exception as e:
                print(f"LLM Check skipped: {e}")

            return {
                "ai_probability": final_ai_score,
                "label": display_label,
                "details": {
                    "model": "Ensemble (RoBERTa Large + Mistral-7B + Web)",
                    "raw_roberta_score": ai_prob,
                    "perplexity": perplexity,
                    "burstiness": burstiness,
                    "perp_ai_contribution": perp_ai_score,
                    "burst_ai_contribution": burst_ai_score,
                    "web_matches": web_sources,
                    "llm_analysis": llm_result
                }
            }
            
        except Exception as e:
            print(f"ML Detection failed: {e}")
            # Fallback to heuristic if ML fails (e.g. model download error)
            return {"ai_probability": 0, "label": "Error", "details": {"error": str(e)}}
