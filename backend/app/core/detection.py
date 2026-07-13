from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.scan import Scan, ScanStatus
from app.core.ml import Chunker, EmbeddingModel
from app.db.vector import VectorDB
import math
import re


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
            from sqlalchemy import update
            stmt = (
                update(Scan)
                .where(Scan.id == scan_id)
                .values(progress=progress, current_step=message)
            )
            self.db.execute(stmt)
            self.db.commit()
            self.time.sleep(0.3)
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
            if not doc:
                doc = self.db.query(Document).filter(Document.id == scan.document_id).first()

            if not doc or not doc.extracted_text:
                raise ValueError("Document has no text to scan")

            # 1. Chunking
            self._update_progress(scan_id, 10, "Chunking document...")
            chunks = self.chunker.chunk_text(doc.extracted_text)
            if not chunks:
                raise ValueError("No chunks generated")

            # 2. Generate Embeddings
            self._update_progress(scan_id, 25, "Generating embeddings...")
            embeddings = self.embedding_model.encode(chunks)

            # 3. Internal DB semantic search (compare against other indexed docs)
            self._update_progress(scan_id, 45, "Searching internal document library...")
            internal_matches = []
            matched_chunks_count = 0

            for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                results = self.vector_db.search(
                    vector, limit=5, score_threshold=0.60,
                    exclude_document_id=doc.id
                )
                if results:
                    best = max(results, key=lambda x: x["score"])
                    internal_matches.append({
                        "chunk_index": i,
                        "chunk_text": chunk,
                        "best_match": {
                            "source_doc_id": best["document_id"],
                            "text": best["text"],
                            "score": round(best["score"], 4),
                            "source": "internal_library"
                        }
                    })
                    matched_chunks_count += 1

            internal_score = (matched_chunks_count / len(chunks)) * 100 if chunks else 0.0

            # 4. Web search plagiarism (DuckDuckGo — checks internet sources)
            self._update_progress(scan_id, 65, "Checking against web sources...")
            web_matches = []
            web_score = 0.0
            try:
                web_matches, web_score = self._web_plagiarism_check(doc.extracted_text, chunks)
            except Exception as e:
                print(f"Web plagiarism check skipped: {e}")

            # 5. Combined score (internal takes priority, web adds to it)
            overall_score = round(max(internal_score, web_score), 2)
            # If both found matches, blend them
            if internal_score > 0 and web_score > 0:
                overall_score = round(min(100, (internal_score * 0.6 + web_score * 0.4)), 2)

            # 6. AI Detection
            self._update_progress(scan_id, 80, "Analyzing AI content probability...")
            ai_analysis = self._detect_ai_content(doc.extracted_text)

            # 7. Finalise
            self._update_progress(scan_id, 95, "Finalizing report...")
            scan.overall_score = overall_score
            scan.report_data = {
                "total_chunks": len(chunks),
                "matched_chunks": matched_chunks_count,
                "internal_score": round(internal_score, 2),
                "web_score": round(web_score, 2),
                "matches": internal_matches,
                "web_matches": web_matches[:10],  # top 10 web sources
                "ai_detection": ai_analysis
            }
            scan.status = ScanStatus.COMPLETED
            scan.progress = 100
            scan.current_step = "Completed"
            self.db.commit()
            print(f"Scan {scan_id} done. Internal:{internal_score:.1f}% Web:{web_score:.1f}% Final:{overall_score}% AI:{ai_analysis.get('ai_probability')}%")

        except Exception as e:
            print(f"Scan failed: {e}")
            scan.status = ScanStatus.FAILED
            scan.report_data = {"error": str(e)}
            self.db.commit()
            import traceback
            traceback.print_exc()

    # ─────────────────────────────────────────────────────────
    # WEB PLAGIARISM CHECK — DuckDuckGo Search
    # Searches sentences from the document on the web and
    # measures how many return direct matches.
    # ─────────────────────────────────────────────────────────
    def _web_plagiarism_check(self, full_text: str, chunks: List[str]):
        """
        Search key sentences from the document against the web.
        Returns (web_matches_list, web_score_percent).
        """
        import re
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            print("duckduckgo-search not installed, skipping web check.")
            return [], 0.0

        # Extract the most "quotable" sentences (medium length, likely prose)
        sentences = re.split(r'(?<=[.!?])\s+', full_text.strip())
        # Pick sentences between 10-30 words — most likely to be plagiarised
        candidates = [s.strip() for s in sentences if 10 <= len(s.split()) <= 35]

        if not candidates:
            # Fallback: take first 200 chars of each chunk
            candidates = [c[:200] for c in chunks[:5] if len(c) > 50]

        # Limit to 5 searches to stay fast
        search_sentences = candidates[:5]
        web_matches = []
        matched_sentences = 0

        for sentence in search_sentences:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(
                        f'"{sentence}"',
                        max_results=3,
                        safesearch='off'
                    ))
                if results:
                    matched_sentences += 1
                    for r in results[:2]:
                        web_matches.append({
                            "sentence": sentence,
                            "source_title": r.get("title", ""),
                            "source_url": r.get("href", r.get("url", "")),
                            "snippet": r.get("body", "")[:200],
                            "match_type": "exact_quote"
                        })
                    print(f"Web match found for: '{sentence[:60]}...'")
            except Exception as e:
                print(f"DuckDuckGo search error: {e}")
                continue

        web_score = (matched_sentences / len(search_sentences)) * 100 if search_sentences else 0.0
        print(f"Web check: {matched_sentences}/{len(search_sentences)} sentences matched online => {web_score:.1f}%")
        return web_matches, web_score

    # ─────────────────────────────────────────────────────────
    # AI CONTENT DETECTION — Robust multi-signal heuristics
    # Works 100% offline, no ML model downloads required.
    # ─────────────────────────────────────────────────────────
    def _detect_ai_content(self, text: str) -> Dict[str, Any]:
        try:
            if not text or len(text.strip()) < 50:
                return {"ai_probability": 0, "label": "Insufficient Data", "details": {}}

            text = text[:4000]  # Cap for speed

            sentences = self._split_sentences(text)
            if len(sentences) < 2:
                return {"ai_probability": 0, "label": "Insufficient Data", "details": {}}

            # ── Signal 1: Sentence Length Uniformity ─────────────────
            # AI text has very uniform sentence lengths (low std-dev)
            lengths = [len(s.split()) for s in sentences if len(s.split()) > 2]
            if not lengths:
                return {"ai_probability": 0, "label": "Insufficient Data", "details": {}}

            mean_len = sum(lengths) / len(lengths)
            variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
            std_dev = math.sqrt(variance)
            burstiness = std_dev / mean_len if mean_len > 0 else 0
            # Low burstiness (<0.35) → AI. High (>0.65) → Human.
            burstiness_score = max(0, min(100, (1 - (burstiness / 0.65)) * 100))

            # ── Signal 2: Vocabulary Richness (Type-Token Ratio) ──────
            # AI text reuses words more predictably.
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            unique_words = set(words)
            ttr = len(unique_words) / len(words) if words else 0
            # Low TTR (<0.35) → AI. High (>0.6) → Human.
            ttr_score = max(0, min(100, (1 - (ttr / 0.55)) * 100))

            # ── Signal 3: Transition Word Overuse ─────────────────────
            # AI text overuses transitional phrases
            transitions = [
                "furthermore", "moreover", "additionally", "consequently",
                "therefore", "thus", "however", "nevertheless", "in conclusion",
                "it is important to note", "it is worth noting", "in summary",
                "to sum up", "in other words", "as a result", "for instance",
                "for example", "this ensures", "this allows", "this enables",
                "it should be noted", "one can", "one must", "can be seen",
                "plays a crucial role", "plays an important role", "delves into",
                "it is essential", "it is crucial", "comprehensive", "multifaceted"
            ]
            text_lower = text.lower()
            transition_count = sum(text_lower.count(t) for t in transitions)
            words_count = len(words)
            transition_density = (transition_count / max(words_count, 1)) * 1000
            # >10 per 1000 words → likely AI
            transition_score = min(100, transition_density * 7)

            # ── Signal 4: Avg Sentence Length ─────────────────────────
            # AI often writes longer, complete sentences (18–28 words avg)
            avg_sent_len = mean_len
            if avg_sent_len > 22:
                sent_len_score = min(100, (avg_sent_len - 22) * 8)
            elif avg_sent_len > 18:
                sent_len_score = 40
            else:
                sent_len_score = max(0, (avg_sent_len - 8) * 4)

            # ── Signal 5: Punctuation Pattern ─────────────────────────
            # AI text has very few exclamation marks, contractions, colloquialisms
            contractions = len(re.findall(
                r"\b(don't|won't|can't|isn't|aren't|wasn't|weren't|I'm|I've|I'll|we're|they're|it's|that's|there's)\b",
                text, re.IGNORECASE
            ))
            exclamations = text.count("!")
            informal_indicators = contractions + exclamations * 2
            # Low informal → likely AI
            informal_score = max(0, 100 - informal_indicators * 15)

            # ── Weighted Ensemble ──────────────────────────────────────
            final_score = (
                burstiness_score   * 0.30 +
                ttr_score          * 0.25 +
                transition_score   * 0.25 +
                sent_len_score     * 0.10 +
                informal_score     * 0.10
            )
            final_score = round(min(100, max(0, final_score)), 1)

            # Label
            if final_score >= 80:
                label = "AI Generated"
            elif final_score >= 60:
                label = "Likely AI"
            elif final_score >= 40:
                label = "Mixed / Unsure"
            else:
                label = "Likely Human"

            print(f"AI Detection scores -- burstiness:{burstiness_score:.1f} ttr:{ttr_score:.1f} transitions:{transition_score:.1f} sent_len:{sent_len_score:.1f} informal:{informal_score:.1f} => FINAL:{final_score}")

            return {
                "ai_probability": final_score,
                "label": label,
                "details": {
                    "model": "Heuristic Ensemble (Burstiness + TTR + Transitions + Sentence Length + Informality)",
                    "burstiness_score": round(burstiness_score, 1),
                    "vocabulary_richness_score": round(ttr_score, 1),
                    "transition_word_score": round(transition_score, 1),
                    "sentence_length_score": round(sent_len_score, 1),
                    "informality_score": round(informal_score, 1),
                    "avg_sentence_length": round(avg_sent_len, 1),
                    "type_token_ratio": round(ttr, 3),
                    "burstiness_raw": round(burstiness, 3),
                }
            }

        except Exception as e:
            print(f"AI Detection failed: {e}")
            import traceback
            traceback.print_exc()
            return {"ai_probability": 0, "label": "Error", "details": {"error": str(e)}}

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex."""
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 10]
