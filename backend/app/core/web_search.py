import logging
import re
import asyncio
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from difflib import SequenceMatcher
from app.core.crawler import AsyncCrawler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSearcher:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.ddgs = DDGS()
        self.crawler = AsyncCrawler.get_instance()

    def search_and_compare(self, text: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        Searches the web for the given text and compares content to find plagiarism.
        Returns a list of sources with similarity scores.
        Note: This method is now a wrapper to run the async version synchronously if needed,
        or we should update the caller to be async. 
        For now, we'll run the event loop here if not already running, or assume caller handles async.
        However, detection.py calls this synchronously.
        To support async without breaking changes, we can use asyncio.run() or loop.run_until_complete().
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we are already in an async loop (e.g. FastAPI), we should await.
                # But since this method signature is sync, we might have an issue.
                # Best practice: Update detection.py to be async.
                # For this MVP step, let's try to run it.
                # Actually, detection.py is synchronous.
                # We can create a new loop for this operation if safe, or use nest_asyncio.
                import nest_asyncio
                nest_asyncio.apply()
                return loop.run_until_complete(self._search_and_compare_async(text, num_results))
            else:
                return loop.run_until_complete(self._search_and_compare_async(text, num_results))
        except RuntimeError:
            # Fallback for new loop
            return asyncio.run(self._search_and_compare_async(text, num_results))

    async def _search_and_compare_async(self, text: str, num_results: int = 5) -> List[Dict[str, Any]]:
        if not text or len(text.strip()) < 50:
            return []

        # 1. Generate Search Queries
        queries = self._generate_queries(text)
        logger.info(f"Generated queries: {queries}")

        found_sources = []
        seen_urls = set()
        urls_to_scrape = []
        url_metadata = {} # Map URL to {title, snippet}

        # 2. Perform Search (DDGS is sync, but fast enough)
        for query in queries:
            try:
                logger.info(f"Searching for: {query}")
                # DDGS returns a generator, convert to list
                # Use region='wt-wt' for global results (avoids local redirects like Zhihu)
                results = list(self.ddgs.text(query, region='wt-wt', max_results=5))
                logger.info(f"Found {len(results)} results for query.")
                
                if not results:
                    continue

                for res in results:
                    url = res['href']
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    urls_to_scrape.append(url)
                    url_metadata[url] = {
                        "title": res['title'],
                        "snippet": res.get('body', '')
                    }
            except Exception as e:
                logger.error(f"Search failed for query '{query}': {e}")
                continue

        if not urls_to_scrape:
            return []

        # 3. Parallel Scrape using Playwright
        logger.info(f"Scraping {len(urls_to_scrape)} URLs in parallel...")
        scraped_contents = await self.crawler.fetch_multiple(urls_to_scrape)

        # 4. Compare
        for url, content in scraped_contents.items():
            meta = url_metadata.get(url, {})
            snippet = meta.get("snippet", "")
            
            # If scraping failed (empty content), fallback to snippet
            page_text = content if content.strip() else snippet
            
            similarity = self._calculate_containment(original_text=text, page_text=page_text)
            logger.info(f"URL: {url}, Similarity: {similarity:.4f}")
            
            if similarity > 0.05:
                found_sources.append({
                    "url": url,
                    "title": meta.get("title", "Unknown"),
                    "similarity": round(similarity * 100, 2),
                    "snippet": snippet[:200] + "..."
                })

        # Sort and Filter
        found_sources.sort(key=lambda x: x['similarity'], reverse=True)
        
        if found_sources and found_sources[0]['similarity'] > 80:
            return found_sources[:1]
            
        return found_sources[:2]

    def _generate_queries(self, text: str) -> List[str]:
        """
        Extracts unique phrases from the text to use as search queries.
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        long_sentences = [s.strip() for s in sentences if len(s.split()) > 15]
        
        if not long_sentences:
            words = text.split()
            if len(words) > 20:
                return [" ".join(words[:25])]
            return [text[:150]]
            
        long_sentences.sort(key=len, reverse=True)
        
        queries = []
        for s in long_sentences[:2]:
            words = s.split()
            if len(words) > 25:
                queries.append(" ".join(words[:25]))
            else:
                queries.append(s)
        return queries

    def _calculate_containment(self, original_text: str, page_text: str) -> float:
        """
        Calculates Containment Similarity.
        """
        if not page_text:
            return 0.0
            
        original_words = set(original_text.lower().split())
        page_words = set(page_text.lower().split())
        
        if not original_words:
            return 0.0
            
        intersection = len(original_words.intersection(page_words))
        containment = intersection / len(original_words)
        
        return float(containment)
