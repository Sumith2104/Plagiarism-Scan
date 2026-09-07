import asyncio
import logging
from typing import Optional, Dict
from playwright.async_api import async_playwright, Browser, BrowserContext

logger = logging.getLogger(__name__)

class AsyncCrawler:
    _instance = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None
    _lock = asyncio.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self):
        """Initialize the browser instance if available."""
        async with self._lock:
            if self._browser is None:
                try:
                    logger.info("Attempting to start Playwright Browser...")
                    self.playwright = await async_playwright().start()
                    self._browser = await self.playwright.chromium.launch(headless=True)
                    self._context = await self._browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                    )
                    logger.info("Playwright Browser started successfully.")
                except Exception as e:
                    logger.warning(f"Playwright Browser could not be started (using HTTP fallback): {e}")
                    self._browser = None
                    self._context = None

    async def stop(self):
        """Close the browser instance."""
        if self._browser:
            try:
                await self._browser.close()
                await self.playwright.stop()
            except Exception:
                pass
            self._browser = None
            self._context = None
            logger.info("Playwright Browser stopped.")

    async def fetch_page_content(self, url: str, timeout: int = 20000) -> str:
        """
        Fetches page content using a headless browser if available, or httpx fallback.
        """
        if not self._browser:
            await self.start()

        if self._browser and self._context:
            try:
                page = await self._context.new_page()
                try:
                    await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                    content = await page.evaluate("document.body.innerText")
                    if content and len(content.strip()) > 30:
                        return content
                finally:
                    await page.close()
            except Exception as e:
                logger.warning(f"Playwright fetch failed for {url}, trying HTTP fallback: {e}")

        # Graceful HTTP fallback
        try:
            import httpx
            from app.core.scraper.distiller import WebDistiller
            browser_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=browser_headers, verify=False) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    distilled = WebDistiller.distill(resp.text, url=url)
                    return distilled.get("clean_text", "")
        except Exception as e:
            logger.warning(f"HTTP fallback scraping failed for {url}: {e}")

        return ""

    async def fetch_multiple(self, urls: list) -> Dict[str, str]:
        """
        Fetches multiple URLs in parallel.
        """
        tasks = [self.fetch_page_content(url) for url in urls]
        results = await asyncio.gather(*tasks)
        return dict(zip(urls, results))
