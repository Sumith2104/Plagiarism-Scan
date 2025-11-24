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
        """Initialize the browser instance."""
        async with self._lock:
            if self._browser is None:
                logger.info("Starting Playwright Browser...")
                self.playwright = await async_playwright().start()
                self._browser = await self.playwright.chromium.launch(headless=True)
                self._context = await self._browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                logger.info("Playwright Browser started.")

    async def stop(self):
        """Close the browser instance."""
        if self._browser:
            await self._browser.close()
            await self.playwright.stop()
            self._browser = None
            self._context = None
            logger.info("Playwright Browser stopped.")

    async def fetch_page_content(self, url: str, timeout: int = 30000) -> str:
        """
        Fetches page content using a headless browser.
        Handles dynamic JS content.
        """
        if not self._browser:
            await self.start()

        page = await self._context.new_page()
        content = ""
        try:
            # Go to URL with timeout
            # networkidle is safer for dynamic pages but slower. 
            # If it times out, we catch it.
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            
            # Small wait to ensure JS execution if needed, or just proceed.
            # await page.wait_for_load_state("networkidle", timeout=5000) 
            
            # Extract text content from body
            content = await page.evaluate("document.body.innerText")
            
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
        finally:
            await page.close()
            
        return content

    async def fetch_multiple(self, urls: list) -> Dict[str, str]:
        """
        Fetches multiple URLs in parallel.
        """
        tasks = [self.fetch_page_content(url) for url in urls]
        results = await asyncio.gather(*tasks)
        return dict(zip(urls, results))
