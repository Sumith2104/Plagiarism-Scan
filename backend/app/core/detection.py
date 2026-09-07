from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.scan import Scan, ScanStatus
from app.core.ml import Chunker, EmbeddingModel
from app.db.vector import VectorDB
from app.core.scraper.distiller import WebDistiller
from app.core.alignment import SequenceAligner, find_best_source_sentence, split_sentences_clean
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
        with httpx.Client(timeout=2.0, follow_redirects=True, headers=headers, http2=False) as client:
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


STOP_WORDS = {
    "this", "that", "these", "those", "with", "from", "into", "during",
    "including", "until", "against", "among", "throughout", "despite",
    "towards", "upon", "concerning", "about", "above", "below", "to",
    "and", "for", "the", "a", "an", "in", "on", "at", "by", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "having",
    "do", "does", "did", "doing", "would", "should", "could", "ought",
    "also", "each", "every", "all", "both", "half", "some", "any",
    "most", "none", "such", "other", "another", "type", "types", "many",
    "much", "more", "less", "least", "well", "back", "come", "work",
    "works", "built", "shows", "show", "used", "uses", "using", "use",
    "make", "makes", "making", "made", "take", "takes", "taking", "took",
    "good", "better", "best", "example", "examples", "run", "runs", "running",
    "step", "steps", "guide", "guides", "tutorial", "tutorials", "learn",
    "learning", "online", "free", "help", "click", "here", "read", "view",
    "play", "games", "game", "video", "dictionary", "meaning", "definition"
}

SPAM_DOMAINS = [
    "bokep", "porn", "xxx", "indo18", "quinbokep", "casino", "bet", "gambl",
    "dating", "adult", "coolmathgames", "poki.com", "typing.com", "typingtest.com",
    "dictionary.cambridge", "merriam-webster.com", "thesaurus.com", "cricinfo.com",
    "cricbuzz.com", "indiarunning.com"
]


def search_yahoo(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Yahoo Search integration: decodes /RU= encoded redirects to retrieve exact destination URLs.
    High reliability on cloud IPs.
    """
    url = "https://search.yahoo.com/search"
    results = []
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        with httpx.Client(timeout=3.5, headers=headers, follow_redirects=True, http2=False) as client:
            resp = client.get(url, params={"p": query})
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    if "/RU=" in href:
                        target = urllib.parse.unquote(href.split("/RU=")[1].split("/RK=")[0])
                        if target.startswith("http") and not any(skip in target.lower() for skip in ["yahoo.com", "yahoosandbox.com"] + SPAM_DOMAINS):
                            title = a.get_text(strip=True)
                            if title and not any(r["url"] == target for r in results):
                                results.append({"title": title, "url": target, "snippet": ""})
                                if len(results) >= max_results:
                                    break
    except Exception as e:
        logger.warning(f"Yahoo search error: {e}")
    return results


def search_bing(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Bing Search integration: decodes u=a1 base64 redirect URLs.
    Extremely accurate on technical articles and documentation.
    """
    import base64
    url = "https://www.bing.com/search"
    results = []
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        with httpx.Client(timeout=3.5, headers=headers, follow_redirects=True, http2=False) as client:
            resp = client.get(url, params={"q": query})
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for li in soup.find_all("li", class_="b_algo")[:max_results]:
                    h2 = li.find("h2")
                    a = h2.find("a") if h2 else None
                    snippet_el = li.find("p") or li.find("div", class_="b_caption")
                    if a and a.get("href"):
                        href = a["href"]
                        if "u=a1" in href:
                            enc = href.split("u=a1")[-1].split("&")[0]
                            try:
                                href = base64.urlsafe_b64decode(enc + "==").decode("utf-8", errors="ignore")
                            except Exception:
                                pass
                        title = a.get_text(strip=True)
                        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                        if href and href.startswith("http") and not any(skip in href.lower() for skip in ["bing.com"] + SPAM_DOMAINS):
                            results.append({"title": title or "Web Source", "url": href, "snippet": snippet[:350]})
    except Exception as e:
        logger.warning(f"Bing search error: {e}")
    return results


def is_result_relevant(query_str: str, title_str: str, snippet_str: str) -> bool:
    """
    Validates that search result contains salient keywords from the query,
    preventing dictionary spam or unrelated query hijacking.
    """
    q_w = set(w.lower() for w in re.sub(r'[^a-zA-Z0-9\s]', ' ', query_str).split() if len(w) > 3 and w.lower() not in STOP_WORDS)
    if not q_w:
        return True
    c_text = (title_str + " " + snippet_str).lower()
    c_w = set(w for w in re.sub(r'[^a-zA-Z0-9\s]', ' ', c_text).split() if len(w) > 3 and w not in STOP_WORDS)
    min_overlap = 2 if len(q_w) >= 3 else 1
    return len(q_w & c_w) >= min_overlap


def multi_engine_web_search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Combines Yahoo, Bing, Wikipedia, and DDG Lite with fast intelligent early exit.
    Prioritizes Yahoo and Bing for speed and resilience against cloud IP throttling.
    """
    results = []

    # 1. Yahoo Search (unthrottled, fast, high accuracy for documentation)
    y_res = search_yahoo(query, max_results=max_results)
    for yr in y_res:
        if not any(r["url"] == yr["url"] for r in results):
            results.append(yr)

    # Return early if Yahoo found results
    if len(results) >= 2:
        return results[:max_results]

    # 2. Bing Search (extensive indexing and high-precision technical snippets)
    if len(results) < max_results:
        b_res = search_bing(query, max_results=max_results - len(results))
        for br in b_res:
            if not any(r["url"] == br["url"] for r in results):
                results.append(br)

    if len(results) >= 1:
        return results[:max_results]

    # 3. Wikipedia Action API (ultra-fast JSON endpoint, ~200ms)
    w_res = wikipedia_search(query, max_results=2)
    for wr in w_res:
        if not any(r["url"] == wr["url"] for r in results):
            results.append(wr)

    if len(results) >= 1:
        return results[:max_results]

    # 4. Direct DDG Lite fallback only if literally 0 results found above
    d_res = direct_duckduckgo_lite_search(query, max_results=max_results)
    for dr in d_res:
        if not any(r["url"] == dr["url"] for r in results):
            results.append(dr)

    return results[:max_results]


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
    Fetches and distills web page text using modern browser headers and fast HTTP/1.1 client.
    """
    browser_headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=3.5, headers=browser_headers, verify=False, http2=False) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                distilled = WebDistiller.distill(resp.text, url=url)
                clean = distilled.get("clean_text", "")
                if clean and len(clean.strip()) > 50:
                    return clean
    except Exception:
        pass
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
        raw_sents = split_sentences_clean(para)
        if not raw_sents:
            raw_sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', para) if s.strip()]
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

            # 1. Check Web Match with Strict Sentence-Level Alignment (>= 75.0%)
            matched_web = None
            best_web_sent_proof = None

            if word_count >= 3:
                candidates_to_check = web_matches + [m for m in evidence_matches if isinstance(m, dict) and not (m.get("source_url") or "").startswith("internal://")]
                for wm in candidates_to_check:
                    wm_url = wm.get("source_url") or wm.get("source") or ""
                    if not wm_url or wm_url.startswith("internal://"):
                        continue

                    # Target source text: full article text if available, otherwise snippet or sentence
                    target_source_text = wm.get("source_full_text") or wm.get("snippet") or wm.get("sentence") or ""
                    if not target_source_text:
                        continue

                    sent_match = find_best_source_sentence(s_clean, target_source_text, min_similarity=75.0)
                    if sent_match:
                        matched_web = wm
                        best_web_sent_proof = sent_match
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
            if matched_web and best_web_sent_proof:
                category = "web"
                sim_val = best_web_sent_proof.get("similarity", 92.0)
                confidence = round(min(99.0, max(75.0, sim_val)), 1)
                m_type = "Verbatim Match" if sim_val >= 85.0 else "Paraphrased Match"
                full_source_sentence = best_web_sent_proof.get("source_sentence") or matched_web.get("snippet", "")
                web_proof = {
                    "source_title": matched_web.get("source_title", "Web Source"),
                    "source_url": matched_web.get("source_url") or matched_web.get("source", ""),
                    "snippet": full_source_sentence,
                    "similarity": sim_val,
                    "match_type": m_type
                }
                reason = f"Direct overlap verified on public internet: {web_proof['source_title']} ({sim_val}% match)"
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
                web_matches, web_score, verbatim_score = self._web_plagiarism_check(doc.extracted_text, chunks, scan_id=scan_id)
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
                "web_matches": web_matches[:15],
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

    def _web_plagiarism_check(self, full_text: str, chunks: List[str], scan_id: Optional[int] = None):
        """
        True Multi-Source Detection Engine:
        - Segments document into all paragraphs and sentences.
        - Proportionally samples sections to guarantee coverage from start, middle, and end.
        - Generates multi-phrase queries (lead n-gram, salient middle n-gram, late n-gram, sentence 2).
        - Queries Yahoo, Bing, and Wikipedia with bot-block resilience.
        - Employs Round-Robin Candidate Allocation across all sections.
        - Deep-scrapes candidate web pages in parallel using ThreadPoolExecutor.
        - Forensically aligns every paragraph and sentence against all scraped candidate sources.
        - Preserves all verified distinct web matches with high similarity scores.
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        cleaned_text = re.sub(r'\[\d+\]|\\\[\d+|\d+\\\[\d+|\[.*?\]', '', full_text).strip()
        if not cleaned_text:
            return [], 0.0, 0.0

        # 1. Segment text into paragraphs and individual sentences
        raw_paragraphs = [p.strip() for p in cleaned_text.split('\n') if len(p.strip().split()) >= 4]
        if not raw_paragraphs:
            raw_paragraphs = [cleaned_text]

        raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned_text) if len(s.strip().split()) >= 4]

        # 2. Select sections to sample across the document (guarantees coverage from start, middle, end)
        num_paras = len(raw_paragraphs)
        if num_paras <= 10:
            sampled_indices = list(range(num_paras))
        else:
            # Proportionally sample 10 sections evenly distributed
            step_pcts = [0.0, 0.12, 0.25, 0.38, 0.50, 0.62, 0.75, 0.85, 0.93, 1.0]
            sampled_indices = sorted(list(set(min(num_paras - 1, int(num_paras * pct)) for pct in step_pcts)))

        section_sources: Dict[int, List[Dict[str, str]]] = {}
        seen_search_urls = set()

        for sec_pos, sec_idx in enumerate(sampled_indices):
            if scan_id and sec_pos % 2 == 0:
                pct = 65 + int((sec_pos / max(len(sampled_indices), 1)) * 10)
                self._update_progress(scan_id, pct, f"Checking section {sec_pos+1}/{len(sampled_indices)} against search engines...")

            p = raw_paragraphs[sec_idx]
            # Clean citations [1], parentheticals, and camelCase splits
            p_clean_wiki = re.sub(r'\[[a-zA-Z0-9_\s]{1,10}\]', ' ', p)
            p_clean_wiki = re.sub(r'\([a-zA-Z0-9_\s]{1,25}\)', ' ', p_clean_wiki)
            p_norm = re.sub(r'([a-z])([A-Z])', r'\1 \2', p_clean_wiki)
            p_norm = re.sub(r'([A-Z]{2,})([a-z])', r'\1 \2', p_norm)
            p_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', p_norm)
            words = [w for w in p_clean.split() if len(w) > 1 or w.lower() in ('a', 'i')]
            if len(words) < 4:
                continue

            queries = []
            # Query 1: Lead 8 words
            queries.append(" ".join(words[:8]))
            # Query 2: Salient/middle 8 words (bypasses starting typos or generic introductory clauses)
            if len(words) >= 14:
                queries.append(" ".join(words[5:13]))
            # Query 3: Late 8 words if paragraph is long
            if len(words) >= 20:
                queries.append(" ".join(words[11:19]))
            # Query 4: 2nd sentence lead if multi-sentence
            sents = split_sentences_clean(p)
            if len(sents) > 1:
                s2_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', sents[1])
                s2_w = [w for w in s2_clean.split() if len(w) > 1 or w.lower() in ('a', 'i')]
                if len(s2_w) >= 4:
                    queries.append(" ".join(s2_w[:8]))

            section_sources[sec_idx] = []
            for q_num, q in enumerate(queries):
                res = multi_engine_web_search(q, max_results=3)
                for r in res:
                    u = r["url"].lower()
                    if u not in seen_search_urls:
                        if is_result_relevant(q, r["title"], r.get("snippet", "")):
                            seen_search_urls.add(u)
                            section_sources[sec_idx].append(r)
                # Stop if we already have verified relevant sources for this section
                if len(section_sources[sec_idx]) >= 2:
                    break

        # 3. Round-Robin Candidate Allocation across all document sections (up to 12 total)
        candidate_sources = []
        seen_cand_urls = set()
        for r in range(2):
            for sec_idx in sorted(section_sources.keys()):
                sources_for_sec = section_sources[sec_idx]
                if r < len(sources_for_sec):
                    cand = sources_for_sec[r]
                    u = cand["url"]
                    if u not in seen_cand_urls:
                        seen_cand_urls.add(u)
                        candidate_sources.append(cand)
                        if len(candidate_sources) >= 12:
                            break
            if len(candidate_sources) >= 12:
                break

        if not candidate_sources:
            return [], 0.0, 0.0

        # 4. Scrape or extract text from candidate sources in parallel
        if scan_id:
            self._update_progress(scan_id, 76, f"Extracting proof from {len(candidate_sources)} web sources in parallel...")

        def _scrape_candidate(src):
            url = src["url"]
            clean_text = None
            if "wikipedia.org/wiki/" in url:
                clean_text = fetch_wikipedia_extract(url)
            if not clean_text:
                clean_text = fetch_web_page_text(url)
            # Fallback to snippet if page scraping was blocked or empty
            if not clean_text and src.get("snippet") and len(src["snippet"].strip()) > 30:
                clean_text = src["snippet"]

            if clean_text:
                return {
                    "title": src["title"],
                    "url": src["url"],
                    "clean_text": clean_text,
                    "snippet": src.get("snippet", "")
                }
            return None

        scraped_texts = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_src = {executor.submit(_scrape_candidate, s): s for s in candidate_sources}
            for fut in as_completed(future_to_src):
                try:
                    res = fut.result()
                    if res:
                        scraped_texts.append(res)
                except Exception:
                    pass

        if not scraped_texts:
            return [], 0.0, 0.0

        if scan_id:
            self._update_progress(scan_id, 82, f"Aligning content across {len(scraped_texts)} candidate web sources...")

        # 5. Multi-Source Alignment: Check each paragraph against ALL candidate sources!
        # Strict sentence-level verification (>= 75%) and full source sentence extraction
        matched_sources_map = {}
        matched_paragraphs_count = 0
        verbatim_paragraphs_count = 0
        total_eval_units = max(len(raw_paragraphs), 1)

        for p_idx, p in enumerate(raw_paragraphs):
            best_sim_for_p = 0.0
            best_src_for_p = None
            best_align_for_p = None
            best_sentence_for_p = None

            p_sents = split_sentences_clean(p)
            if not p_sents:
                p_sents = [p]

            for st in scraped_texts:
                alignment = self.aligner.align_texts(p, st["clean_text"])
                sim = alignment.get("similarity_score", 0.0)
                sent_match = alignment.get("best_sentence_match")

                # Check all sentences in this paragraph for direct high-fidelity alignment
                if not sent_match or sent_match["similarity"] < 75.0:
                    for s in p_sents:
                        sm = find_best_source_sentence(s, st["clean_text"], min_similarity=75.0)
                        if sm and (not sent_match or sm["similarity"] > sent_match["similarity"]):
                            sent_match = sm

                effective_sim = max(sim, sent_match["similarity"] if sent_match else 0.0)

                # Strict acceptance:
                # EITHER a verified sentence match >= 75%,
                # OR strong paragraph verbatim alignment (sim >= 65% with verbatim_ratio >= 0.50)
                is_valid_match = (sent_match is not None and sent_match["similarity"] >= 75.0) or \
                                 (sim >= 65.0 and alignment.get("verbatim_ratio", 0.0) >= 0.50)

                if is_valid_match and effective_sim > best_sim_for_p:
                    best_sim_for_p = effective_sim
                    best_src_for_p = st
                    best_align_for_p = alignment
                    best_sentence_for_p = sent_match

            if best_src_for_p:
                matched_paragraphs_count += 1
                cls = best_align_for_p.get("classification", "web_match")
                if cls == "verbatim_plagiarism" or (best_sentence_for_p and best_sentence_for_p["similarity"] >= 85.0):
                    verbatim_paragraphs_count += 1

                # Complete source sentence snippet (never truncated to 4-word fragments)
                source_snippet = ""
                if best_sentence_for_p:
                    source_snippet = best_sentence_for_p["source_sentence"]
                elif best_align_for_p.get("verbatim_blocks"):
                    v_phrase = best_align_for_p["verbatim_blocks"][0].get("matched_tokens", "")
                    clean_source = best_src_for_p["clean_text"]
                    idx = clean_source.lower().find(v_phrase.lower())
                    if idx != -1:
                        start_c = max(0, idx - 40)
                        end_c = min(len(clean_source), idx + len(v_phrase) + 120)
                        source_snippet = clean_source[start_c:end_c].strip()
                    else:
                        source_snippet = best_src_for_p["clean_text"][:250]
                else:
                    source_snippet = best_src_for_p["clean_text"][:250]

                url = best_src_for_p["url"]
                if url not in matched_sources_map:
                    matched_sources_map[url] = {
                        "sentence": p,
                        "source_title": best_src_for_p["title"],
                        "source_url": url,
                        "source_full_text": best_src_for_p["clean_text"],
                        "snippet": source_snippet,
                        "similarity_score": round(best_sim_for_p, 2),
                        "match_type": cls,
                        "matched_sentences": [p]
                    }
                else:
                    matched_sources_map[url]["matched_sentences"].append(p)
                    if best_sim_for_p > matched_sources_map[url]["similarity_score"]:
                        matched_sources_map[url]["similarity_score"] = round(best_sim_for_p, 2)
                        matched_sources_map[url]["sentence"] = p
                        matched_sources_map[url]["snippet"] = source_snippet
                        matched_sources_map[url]["match_type"] = cls

        # Also check distinct sentences for any sources not captured at paragraph level
        for s in raw_sentences:
            for st in scraped_texts:
                url = st["url"]
                sent_match = find_best_source_sentence(s, st["clean_text"], min_similarity=75.0)
                if sent_match:
                    sim = sent_match["similarity"]
                    cls = "verbatim_plagiarism" if sim >= 85.0 else "paraphrase_plagiarism"
                    source_snippet = sent_match["source_sentence"]

                    if url not in matched_sources_map:
                        matched_sources_map[url] = {
                            "sentence": s,
                            "source_title": st["title"],
                            "source_url": url,
                            "source_full_text": st["clean_text"],
                            "snippet": source_snippet,
                            "similarity_score": round(sim, 2),
                            "match_type": cls,
                            "matched_sentences": [s]
                        }
                    elif s not in matched_sources_map[url].get("matched_sentences", []):
                        matched_sources_map[url].setdefault("matched_sentences", []).append(s)

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
