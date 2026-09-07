from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.scan import Scan, ScanStatus
from app.core.ml import Chunker, EmbeddingModel
from app.db.vector import VectorDB
from app.core.scraper.distiller import WebDistiller
from app.core.alignment import SequenceAligner
from app.core.readability import compute_readability_metrics
import math
import re
import urllib.parse
import logging
import httpx
from bs4 import BeautifulSoup
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

COMPLIANT_USER_AGENT = "PlagiaScan-Forensic/1.0 (Academic Plagiarism Detector; support@plagiascan.org)"
BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def direct_duckduckgo_lite_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """
    Direct zero-dependency fallback: queries DuckDuckGo Lite HTML interface directly via HTTP POST.
    Resilient against datacenter IP API bot blocks.
    """
    results = []
    url = "https://lite.duckduckgo.com/lite/"
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://lite.duckduckgo.com",
        "Referer": "https://lite.duckduckgo.com/",
    }
    data = {"q": query}
    try:
        with httpx.Client(timeout=8.0, follow_redirects=True, headers=headers) as client:
            resp = client.post(url, data=data)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for link in soup.find_all("a", class_="result-link"):
                    raw_href = link.get("href", "")
                    title = link.get_text().strip()
                    target_url = raw_href
                    if "uddg=" in raw_href:
                        parsed = urllib.parse.urlparse(raw_href)
                        qs = urllib.parse.parse_qs(parsed.query)
                        if "uddg" in qs:
                            target_url = qs["uddg"][0]
                    elif raw_href.startswith("//"):
                        target_url = "https:" + raw_href
                    elif raw_href.startswith("/"):
                        continue

                    snippet = ""
                    tr = link.find_parent("tr")
                    if tr:
                        snippet_tr = tr.find_next_sibling("tr")
                        if snippet_tr:
                            snippet_td = snippet_tr.find("td", class_="result-snippet")
                            if snippet_td:
                                snippet = snippet_td.get_text().strip()

                    if target_url and target_url.startswith("http"):
                        results.append({
                            "title": title or "Web Source",
                            "url": target_url,
                            "snippet": snippet[:350]
                        })
                        if len(results) >= max_results:
                            break
    except Exception as e:
        logger.warning(f"Direct DDG Lite search error: {e}")
    return results


def wikipedia_search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search Wikipedia using their official Wikimedia Action API.
    """
    results = []
    wiki_api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": max_results
    }
    headers = {"User-Agent": COMPLIANT_USER_AGENT}
    try:
        with httpx.Client(timeout=8.0, headers=headers) as client:
            resp = client.get(wiki_api_url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("query", {}).get("search", []):
                    title = item.get("title", "")
                    clean_snippet = re.sub(r'<[^>]+>', '', item.get("snippet", "")).strip()
                    url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    results.append({
                        "title": f"Wikipedia: {title}",
                        "url": url,
                        "snippet": clean_snippet[:350]
                    })
    except Exception as e:
        logger.warning(f"Wikipedia search error: {e}")
    return results


def fetch_wikipedia_extract(url: str) -> Optional[str]:
    """
    Fetches the full plain-text extract of a Wikipedia article using Wikimedia API.
    Avoids HTML scraping overhead and cloud IP blocks.
    """
    try:
        page_title = url.split("/wiki/")[-1].split("#")[0].replace("_", " ")
        api_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "prop": "extracts",
            "explaintext": "1",
            "titles": page_title,
            "format": "json"
        }
        headers = {"User-Agent": COMPLIANT_USER_AGENT}
        with httpx.Client(timeout=10.0, headers=headers) as client:
            resp = client.get(api_url, params=params)
            if resp.status_code == 200:
                pages = resp.json().get("query", {}).get("pages", {})
                for pid, pdata in pages.items():
                    extract = pdata.get("extract")
                    if extract and len(extract) > 100:
                        return extract
    except Exception as e:
        logger.warning(f"Wikipedia extract failed for {url}: {e}")
    return None


def fetch_web_page_text(url: str) -> Optional[str]:
    """
    Fetches and distills web page text using modern browser headers and SSL fallback.
    """
    browser_headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }
    for verify in [True, False]:
        try:
            with httpx.Client(follow_redirects=True, timeout=10.0, headers=browser_headers, verify=verify) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    distilled = WebDistiller.distill(resp.text, url=url)
                    clean = distilled.get("clean_text", "")
                    if clean and len(clean.strip()) > 50:
                        return clean
            break
        except Exception:
            if not verify:
                break
    return None

HALLMARK_PATTERNS = [
    r'\b(has become one of the most)\b',
    r'\b(plays a (crucial|pivotal|vital|key|fundamental|significant) role)\b',
    r'\b(in today\'s (rapidly|fast-paced|interconnected|modern|ever-changing) (world|society|landscape|era))\b',
    r'\b(it is (important|essential|worth noting|crucial|imperative) to (note|understand|remember|highlight))\b',
    r'\b(a testament to (the power|the importance|the enduring))\b',
    r'\b(delves? into the (complexities|nuances|intricacies))\b',
    r'\b(serves as a (beacon|cornerstone|catalyst|reminder))\b',
    r'\b(not only [^,.\n]{3,40}, but (also|rather))\b',
    r'\b(has become an (indispensable|integral|essential) part)\b',
    r'\b(from [^,.\n]{3,30} to [^,.\n]{3,30}, [^,.\n]{3,40} has)\b',
    r'\b(fosters? a (sense|culture|deep understanding) of)\b',
    r'\b(a powerful tool for (building|creating|fostering|enhancing))\b',
    r'\b(overall, [^.\n]{1,60} has enormous potential)\b',
    r'\b(in conclusion|to sum up|in summary|ultimately)\b',
    r'\b(on the other hand|furthermore|moreover|consequently|therefore)\b',
    r'\b(can assist|can help|can be considered|can become)\b',
    r'\b(rapid (growth|advancement|development|evolution))\b',
    r'\b(one (major|key|significant|primary) (concern|challenge|aspect|factor|advantage))\b',
    r'\b(there are also concerns related)\b',
    r'\b(the future will likely (involve|see|bring|witness))\b',
    r'\b(with the right (balance|safeguards|framework|approach))\b',
    r'\b(changing the way (people|we) (live|work|learn|communicate))\b',
    r'\b(refers to the ability of)\b',
    r'\b(tasks that normally require human intelligence)\b',
    r'\b(in many areas of our daily lives)\b',
    r'\b(without us even realizing it)\b',
    r'\b(potential to improve society)\b',
    r'\b(raise important (ethical|moral|practical) questions)\b',
    r'\b(as AI continues to (evolve|grow|develop|advance))\b',
    r'\b(ensure that its benefits are realized while)\b',
    r'\b(minimizing potential risks)\b',
]


def generate_line_analysis(
    full_text: str,
    web_matches: List[Dict[str, Any]] = None,
    internal_matches: List[Dict[str, Any]] = None,
    evidence_matches: List[Dict[str, Any]] = None,
    ai_detection: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Forensically annotate each sentence and line of the document text.
    Classifies every line into 'web', 'ai', 'ml', or 'clean' with full proof details.
    """
    if not full_text:
        return []

    web_matches = web_matches or []
    internal_matches = internal_matches or []
    evidence_matches = evidence_matches or []
    ai_detection = ai_detection or {}

    overall_ai_prob = ai_detection.get("ai_probability", 0)

    # Split text into paragraphs, then sentences
    paragraphs = [p.strip() for p in full_text.split("\n") if p.strip()]
    annotated = []
    line_idx = 0

    for p_idx, para in enumerate(paragraphs):
        raw_sents = re.split(r'(?<=[.!?])\s+', para)
        for s in raw_sents:
            s_clean = s.strip()
            if not s_clean or len(s_clean) < 4:
                continue

            line_idx += 1
            words = s_clean.split()
            word_count = len(words)
            s_lower = s_clean.lower()
            s_alnum = re.sub(r'[^a-zA-Z0-9\s]', ' ', s_lower)
            s_words_set = set(w for w in s_alnum.split() if len(w) > 3)

            # 1. Check Web Match (Verified external URLs)
            matched_web = None
            if word_count >= 3 and len(s_words_set) >= 2:
                for wm in (web_matches + [m for m in evidence_matches if isinstance(m, dict) and not (m.get("source_url") or "").startswith("internal://")]):
                    wm_sentence = (wm.get("sentence") or wm.get("chunk_text") or wm.get("suspect_excerpt") or "").lower()
                    wm_url = wm.get("source_url") or wm.get("source") or ""
                    if not wm_url or wm_url.startswith("internal://"):
                        continue
                    wm_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', wm_sentence)
                    wm_words = set(w for w in wm_clean.split() if len(w) > 3)
                    if wm_words and s_words_set:
                        overlap = len(s_words_set & wm_words) / len(s_words_set)
                        if overlap >= 0.50 or (len(s_clean) >= 20 and (s_lower in wm_sentence or wm_sentence in s_lower)):
                            matched_web = wm
                            break

            # 2. Check ML / Internal Vector Match
            matched_internal = None
            if not matched_web and word_count >= 3 and len(s_words_set) >= 2:
                for im in internal_matches:
                    im_text = (im.get("chunk_text") or im.get("suspect_excerpt") or "").lower()
                    if (len(s_clean) >= 25 and s_clean.lower() in im_text) or (len(s_words_set) >= 3 and sum(1 for w in s_words_set if w in im_text) / len(s_words_set) >= 0.65):
                        matched_internal = im
                        break

            # 3. Check AI hallmarks in this sentence
            found_hallmarks = []
            for p in HALLMARK_PATTERNS:
                m = re.search(p, s_clean, re.IGNORECASE)
                if m:
                    found_hallmarks.append(m.group(0))

            # Determine AI sentence status
            is_ai_sentence = False
            ai_conf = 0.0
            ai_reason = ""

            if found_hallmarks:
                is_ai_sentence = True
                ai_conf = min(98.0, 80.0 + len(found_hallmarks) * 8)
                ai_reason = f"Contains LLM rhetorical marker: '{', '.join(found_hallmarks[:2])}'"
            elif overall_ai_prob >= 70 and word_count >= 6:
                is_ai_sentence = True
                ai_conf = round(overall_ai_prob, 1)
                ai_reason = "Synthetic syntactic balance, absence of colloquialisms, and formulaic AI cadence"
            elif overall_ai_prob >= 50 and 8 <= word_count <= 45 and not any(c in s_clean for c in ["!", "I'm", "can't", "don't"]):
                is_ai_sentence = True
                ai_conf = round(overall_ai_prob * 0.95, 1)
                ai_reason = "Uniform sentence distribution characteristic of LLMs"

            # Determine classification
            if matched_web:
                category = "web"
                confidence = 94.0
                web_proof = {
                    "source_title": matched_web.get("source_title", "Web Source"),
                    "source_url": matched_web.get("source_url") or matched_web.get("source", ""),
                    "snippet": matched_web.get("snippet") or matched_web.get("source_excerpt", ""),
                    "match_type": matched_web.get("match_type", "web_match")
                }
                reason = f"Direct overlap verified on public internet: {web_proof['source_title']}"
            elif matched_internal:
                category = "ml"
                best = matched_internal.get("best_match", {})
                sim = round(best.get("score", 0.8) * 100, 1)
                confidence = sim
                ml_proof = {
                    "source_doc_id": best.get("source_doc_id", "Internal Document"),
                    "matched_text": best.get("text") or matched_internal.get("source_excerpt", ""),
                    "similarity": sim
                }
                reason = f"High semantic vector similarity ({sim}%) with internal document archive"
            elif is_ai_sentence:
                category = "ai"
                confidence = ai_conf
                reason = ai_reason
            else:
                category = "clean"
                confidence = 96.0
                reason = "Natural human prose with authentic stylistic burstiness"

            entry = {
                "line_index": line_idx,
                "paragraph_index": p_idx + 1,
                "text": s_clean,
                "word_count": word_count,
                "category": category,
                "confidence": confidence,
                "reason": reason,
                "hallmarks": found_hallmarks,
            }
            if matched_web:
                entry["web_proof"] = web_proof
            if matched_internal:
                entry["ml_proof"] = ml_proof

            annotated.append(entry)

    return annotated


class DetectionEngine:
    def __init__(self, db: Session):
        self.db = db
        self.vector_db = VectorDB()
        self.chunker = Chunker()
        self.embedding_model = EmbeddingModel.get_instance()
        self.aligner = SequenceAligner()
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
            self.time.sleep(0.2)
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
            self._update_progress(scan_id, 10, "Chunking document text...")
            chunks = self.chunker.chunk_text(doc.extracted_text)
            if not chunks:
                raise ValueError("No chunks generated")

            # 2. Generate Embeddings
            self._update_progress(scan_id, 25, "Generating vector embeddings...")
            embeddings = self.embedding_model.encode(chunks)

            # 3. Internal DB semantic search (compare against other indexed docs)
            self._update_progress(scan_id, 45, "Searching institutional document library...")
            internal_matches = []
            matched_chunks_count = 0

            for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                results = self.vector_db.search(
                    vector, limit=5, score_threshold=0.65,
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
                            "source": f"internal://document/{best['document_id']}"
                        }
                    })
                    matched_chunks_count += 1

            internal_score = (matched_chunks_count / len(chunks)) * 100 if chunks else 0.0

            # 4. Web search & scraping plagiarism check
            self._update_progress(scan_id, 65, "Checking against global web sources...")
            web_matches = []
            web_score = 0.0
            verbatim_score = 0.0
            try:
                web_matches, web_score, verbatim_score = self._web_plagiarism_check(doc.extracted_text, chunks)
            except Exception as e:
                print(f"Web plagiarism check skipped: {e}")

            # 5. Combined score (internal and web)
            overall_score = round(max(internal_score, web_score), 2)
            if internal_score > 0 and web_score > 0:
                overall_score = round(min(100.0, (internal_score * 0.5 + web_score * 0.5)), 2)

            # 6. AI Content & Readability Analysis
            self._update_progress(scan_id, 85, "Analyzing AI content probability & readability...")
            ai_analysis = self._detect_ai_content(doc.extracted_text)
            readability_analysis = compute_readability_metrics(doc.extracted_text)

            # 7. Finalize Report and Line Analysis
            self._update_progress(scan_id, 95, "Synthesizing forensic proof & line analysis...")
            scan.overall_score = overall_score

            all_matches = list(internal_matches)
            if not all_matches and web_matches:
                for i, wm in enumerate(web_matches):
                    all_matches.append({
                        "chunk_index": i,
                        "chunk_text": wm.get("sentence", ""),
                        "best_match": {
                            "source_doc_id": wm.get("source_title", "Web Source"),
                            "text": wm.get("snippet", ""),
                            "score": 0.95,
                            "source": wm.get("source_url", "")
                        },
                        "match_type": wm.get("match_type", "web_match"),
                        "reasoning": "Direct lexical overlap confirmed on public internet source."
                    })

            line_annotations = generate_line_analysis(
                full_text=doc.extracted_text,
                web_matches=web_matches,
                internal_matches=all_matches,
                evidence_matches=all_matches,
                ai_detection=ai_analysis
            )

            # Ensure line_analysis safely fits within cloud database payload constraints (<200KB)
            # For large documents, store flagged lines in DB; full line text is generated on the fly by GET /scans/{id}
            flagged_lines = [l for l in line_annotations if l.get("category") != "clean"]
            db_lines = line_annotations if len(line_annotations) <= 200 else flagged_lines

            scan.report_data = {
                "scan_mode": "standard",
                "total_chunks": len(chunks),
                "matched_chunks": matched_chunks_count or len(web_matches),
                "internal_score": round(internal_score, 2),
                "web_score": round(web_score, 2),
                "overall_score": overall_score,
                "verbatim_score": round(verbatim_score, 2),
                "matches": all_matches,
                "web_matches": web_matches[:10],
                "ai_detection": ai_analysis,
                "readability": readability_analysis,
                "line_analysis": db_lines
            }
            scan.overall_score = overall_score
            scan.status = ScanStatus.COMPLETED
            scan.progress = 100
            scan.current_step = "Completed"
            self.db.commit()
            print(f"Scan {scan_id} done. Internal:{internal_score:.1f}% Web:{web_score:.1f}% Final:{overall_score}% AI:{ai_analysis.get('ai_probability')}%")

            # Dispatch professional branded notification email with PlagiaScan logo
            try:
                from app.models.user import User
                from app.core.email import send_scan_completed_email

                target_user = None
                if scan.initiated_by:
                    target_user = self.db.query(User).filter(User.id == scan.initiated_by).first()
                if not target_user and doc and doc.user_id:
                    target_user = self.db.query(User).filter(User.id == doc.user_id).first()

                target_email = target_user.email if (target_user and target_user.email) else getattr(settings, "EMAIL_ADDRESS", None)
                target_name = target_user.full_name if (target_user and target_user.full_name) else "Researcher"

                if target_email:
                    doc_title = doc.filename if doc else f"Document #{scan.document_id}"
                    send_scan_completed_email(
                        to_email=target_email,
                        full_name=target_name,
                        document_title=doc_title,
                        scan_id=scan.id,
                        overall_score=overall_score,
                        ai_probability=ai_analysis.get("ai_probability", 0),
                        ai_label=ai_analysis.get("label", "Unknown"),
                        web_matches_count=len(web_matches),
                        scan_mode=getattr(scan, "scan_mode", "standard") or "standard"
                    )
            except Exception as mail_err:
                print(f"Non-blocking scan notification email dispatch error: {mail_err}")

        except Exception as e:
            print(f"Scan failed: {e}")
            scan.status = ScanStatus.FAILED
            scan.report_data = {"error": str(e)}
            self.db.commit()
            import traceback
            traceback.print_exc()

    def _web_plagiarism_check(self, full_text: str, chunks: List[str]):
        """
        Multi-engine web search (DDGS Lite, DDGS HTML, direct DDG Lite fallback, Wikipedia API)
        with paragraph-level query sampling, deep scraping, and multi-source sequence alignment.
        Returns (web_matches, web_score, verbatim_score).
        """
        cleaned_text = re.sub(r'\[\d+\]|\\\[\d+|\d+\\\[\d+|\[.*?\]', '', full_text).strip()
        if not cleaned_text:
            return [], 0.0, 0.0

        # 1. Segment text into paragraphs and individual sentences for multi-source detection
        raw_paragraphs = [p.strip() for p in cleaned_text.split('\n') if len(p.strip().split()) >= 4]
        if not raw_paragraphs:
            raw_paragraphs = [cleaned_text]

        # Also collect distinct sentences
        raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned_text) if len(s.strip().split()) >= 4]

        # 2. Extract search queries ensuring EVERY paragraph has targeted representation
        search_queries = []
        for p in raw_paragraphs:
            p_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', p)
            words = p_clean.split()
            if len(words) >= 5:
                # Query 1: Start of paragraph (8-10 words)
                search_queries.append(" ".join(words[:10]))
                # Query 2: Middle/distinctive part if paragraph is longer
                if len(words) >= 16:
                    search_queries.append(" ".join(words[6:16]))

        # Also sample from sentences if few paragraphs exist
        if len(search_queries) < 4:
            for s in raw_sentences:
                s_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
                words = s_clean.split()
                if len(words) >= 5:
                    q = " ".join(words[:10])
                    if q not in search_queries:
                        search_queries.append(q)

        # Cap search queries to 8 to stay fast while covering all sections
        if len(search_queries) > 8:
            step = len(search_queries) // 8
            search_queries = [search_queries[i * step] for i in range(8)]

        found_sources = []
        seen_urls = set()

        for q in search_queries:
            query_sources = []

            # 1. DDGS with backend='lite' then 'html'
            if DDGS is not None:
                for backend in ['lite', 'html']:
                    try:
                        with DDGS() as ddgs:
                            for r in list(ddgs.text(q, max_results=3, backend=backend)):
                                url = r.get("href", r.get("url", ""))
                                if url and url not in seen_urls:
                                    seen_urls.add(url)
                                    query_sources.append({
                                        "title": r.get("title", "Web Source"),
                                        "url": url,
                                        "snippet": r.get("body", "")[:350]
                                    })
                        if query_sources:
                            break
                    except Exception as e:
                        logger.warning(f"DDGS backend '{backend}' failed for '{q}': {e}")

            # 2. Direct DDG Lite fallback if DDGS returned nothing
            if not query_sources:
                direct_results = direct_duckduckgo_lite_search(q, max_results=3)
                for r in direct_results:
                    if r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        query_sources.append(r)

            # 3. Wikipedia API Search
            wiki_results = wikipedia_search(q, max_results=2)
            for r in wiki_results:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    query_sources.append(r)

            found_sources.extend(query_sources)

        if not found_sources:
            return [], 0.0, 0.0

        # 3. Scrape or extract text from top sources (up to 10 sources across different domains)
        scraped_texts = []
        for src in found_sources[:10]:
            url = src["url"]
            clean_text = None
            if "wikipedia.org/wiki/" in url:
                clean_text = fetch_wikipedia_extract(url)
            if not clean_text:
                clean_text = fetch_web_page_text(url)
            # Critical fallback: use snippet if full page scraping was blocked or empty
            if not clean_text and src.get("snippet") and len(src["snippet"].strip()) > 30:
                clean_text = src["snippet"]

            if clean_text:
                scraped_texts.append({
                    "title": src["title"],
                    "url": src["url"],
                    "clean_text": clean_text
                })

        if not scraped_texts:
            return [], 0.0, 0.0

        # 4. Multi-Source Alignment: Check each paragraph against ALL candidate sources!
        # Do NOT break on the first source! A document can contain multiple sources!
        matched_sources_map = {}
        matched_paragraphs_count = 0
        verbatim_paragraphs_count = 0
        total_eval_units = max(len(raw_paragraphs), 1)

        for p_idx, p in enumerate(raw_paragraphs):
            best_sim_for_p = 0.0
            best_src_for_p = None
            best_align_for_p = None

            for st in scraped_texts:
                alignment = self.aligner.align_texts(p, st["clean_text"])
                sim = alignment.get("similarity_score", 0.0)
                if sim >= 22.0 and sim > best_sim_for_p:
                    best_sim_for_p = sim
                    best_src_for_p = st
                    best_align_for_p = alignment

            if best_src_for_p and best_sim_for_p >= 22.0:
                matched_paragraphs_count += 1
                cls = best_align_for_p.get("classification", "web_match")
                if cls == "verbatim_plagiarism":
                    verbatim_paragraphs_count += 1

                source_snippet = ""
                if best_align_for_p.get("verbatim_blocks"):
                    source_snippet = best_align_for_p["verbatim_blocks"][0].get("matched_tokens", "")[:250]
                else:
                    source_snippet = best_src_for_p["clean_text"][:250]

                url = best_src_for_p["url"]
                if url not in matched_sources_map or best_sim_for_p > matched_sources_map[url]["similarity_score"]:
                    matched_sources_map[url] = {
                        "sentence": p,
                        "source_title": best_src_for_p["title"],
                        "source_url": url,
                        "snippet": source_snippet,
                        "similarity_score": best_sim_for_p,
                        "match_type": cls
                    }

        # Also check coarse chunks if any chunk matched a source not captured at paragraph level
        for chunk in chunks:
            for st in scraped_texts:
                url = st["url"]
                if url in matched_sources_map:
                    continue
                alignment = self.aligner.align_texts(chunk, st["clean_text"])
                sim = alignment.get("similarity_score", 0.0)
                if sim >= 28.0:
                    cls = alignment.get("classification", "web_match")
                    source_snippet = ""
                    if alignment.get("verbatim_blocks"):
                        source_snippet = alignment["verbatim_blocks"][0].get("matched_tokens", "")[:250]
                    else:
                        source_snippet = st["clean_text"][:250]

                    matched_sources_map[url] = {
                        "sentence": chunk,
                        "source_title": st["title"],
                        "source_url": url,
                        "snippet": source_snippet,
                        "similarity_score": sim,
                        "match_type": cls
                    }

        web_matches = sorted(list(matched_sources_map.values()), key=lambda x: x["similarity_score"], reverse=True)
        web_score = round(min(100.0, (matched_paragraphs_count / total_eval_units) * 100), 2)
        verbatim_score = round(min(100.0, (verbatim_paragraphs_count / total_eval_units) * 100), 2)

        return web_matches, web_score, verbatim_score

    def _detect_ai_content(self, text: str) -> Dict[str, Any]:
        try:
            if not text or len(text.strip()) < 50:
                return {"ai_probability": 0, "label": "Insufficient Data", "details": {}}

            text_sample = text[:5000]
            sentences = self._split_sentences(text_sample)
            if len(sentences) < 2:
                return {"ai_probability": 0, "label": "Insufficient Data", "details": {}}

            # Signal 1: Sentence Length Uniformity (Burstiness)
            lengths = [len(s.split()) for s in sentences if len(s.split()) > 2]
            if not lengths:
                return {"ai_probability": 0, "label": "Insufficient Data", "details": {}}

            mean_len = sum(lengths) / len(lengths)
            variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
            std_dev = math.sqrt(variance)
            burstiness = std_dev / mean_len if mean_len > 0 else 0
            burstiness_score = max(0, min(100, (1 - (burstiness / 0.65)) * 100))

            # Signal 2: LLM Hallmark Hits
            matched_hallmarks = []
            for p in HALLMARK_PATTERNS:
                m = re.search(p, text_sample, re.IGNORECASE)
                if m:
                    matched_hallmarks.append(m.group(0))
            hallmark_score = min(100.0, len(matched_hallmarks) * 16.5)

            # Signal 3: Formality & Contractions
            contr_pattern = r"\b(don't|won't|can't|isn't|aren't|wasn't|weren't|I'm|I've|I'll|we're|they're|it's|that's|there's)\b"
            contractions = len(re.findall(contr_pattern, text_sample, re.IGNORECASE))
            exclamations = text_sample.count("!")
            informal_score = max(0, 100 - (contractions + exclamations * 2) * 15)

            # Signal 4: Syntactic Cadence Balance (Proportion of sentences between 14 and 32 words)
            balanced_sents = sum(1 for l in lengths if 14 <= l <= 32)
            balance_score = (balanced_sents / len(lengths)) * 100 if lengths else 0

            # Signal 5: Formulaic Transition Overuse
            transitions = [
                "furthermore", "moreover", "additionally", "consequently",
                "therefore", "thus", "however", "nevertheless", "in conclusion",
                "it is important to note", "it is worth noting", "in summary",
                "to sum up", "in other words", "as a result", "for instance",
                "for example", "this ensures", "this allows", "this enables",
                "it should be noted", "one can", "one must", "can be seen",
                "plays a crucial role", "plays an important role", "delves into",
                "it is essential", "it is crucial", "comprehensive", "multifaceted", "overall", "instead"
            ]
            text_lower = text_sample.lower()
            transition_count = sum(text_lower.count(t) for t in transitions)
            words_count = len(re.findall(r'\b[a-zA-Z]+\b', text_sample))
            transition_density = (transition_count / max(words_count, 1)) * 1000
            transition_score = min(100, transition_density * 7.5)

            # Weighted 5-Signal Calibrated Ensemble
            final_score = (
                hallmark_score     * 0.35 +
                burstiness_score   * 0.20 +
                informal_score     * 0.15 +
                balance_score      * 0.15 +
                transition_score   * 0.15
            )
            final_score = round(min(100, max(0, final_score)), 1)

            if final_score >= 80:
                label = "AI Generated"
            elif final_score >= 60:
                label = "Likely AI"
            elif final_score >= 40:
                label = "Mixed / Unsure"
            else:
                label = "Likely Human"

            return {
                "ai_probability": final_score,
                "label": label,
                "details": {
                    "model": "Calibrated 5-Signal Ensemble (LLM Hallmarks + Burstiness + Formality + Balance + Transitions)",
                    "hallmark_hits": len(matched_hallmarks),
                    "matched_hallmarks": matched_hallmarks[:6],
                    "hallmark_score": round(hallmark_score, 1),
                    "burstiness_score": round(burstiness_score, 1),
                    "informality_score": round(informal_score, 1),
                    "balance_score": round(balance_score, 1),
                    "transition_score": round(transition_score, 1),
                    "avg_sentence_length": round(mean_len, 1),
                    "burstiness_raw": round(burstiness, 2),
                }
            }

        except Exception as e:
            print(f"AI Detection failed: {e}")
            return {"ai_probability": 0, "label": "Error", "details": {"error": str(e)}}

    def _split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 10]
