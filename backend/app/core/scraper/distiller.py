"""
Web Distiller: Extracts clean, readable prose from raw HTML or web responses.
Removes headers, footers, navigation bars, cookie banners, advertisements,
scripts, and sidebars to isolate the core article content for comparison.
"""

from typing import Dict, Any, Optional
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class WebDistiller:
    """
    Cleans raw HTML into distilled text prose suitable for plagiarism comparison.
    """

    # Elements that are typically boilerplate or non-content
    BOILERPLATE_TAGS = [
        "nav", "header", "footer", "aside", "script", "style", "noscript",
        "iframe", "svg", "form", "button", "input", "textarea", "select"
    ]

    # Class / ID substrings that signal ads, comments, or boilerplate
    BOILERPLATE_PATTERNS = re.compile(
        r'(comment|advert|banner|cookie|gdpr|sidebar|nav|menu|social|footer|header|promo|widget|signup|newsletter)',
        re.IGNORECASE
    )

    @classmethod
    def distill(cls, html_content: str, url: str = "") -> Dict[str, Any]:
        """
        Distills raw HTML into clean, readable text.
        Returns a dict with title, clean_text, word_count, domain.
        """
        if not html_content or not html_content.strip():
            return {
                "title": "",
                "clean_text": "",
                "word_count": 0,
                "domain": urlparse(url).netloc if url else ""
            }

        try:
            soup = BeautifulSoup(html_content, "html.parser")
        except Exception:
            # Fallback simple tag stripping
            clean = re.sub(r'<[^>]+>', ' ', html_content)
            clean = re.sub(r'\s+', ' ', clean).strip()
            return {
                "title": "",
                "clean_text": clean,
                "word_count": len(clean.split()),
                "domain": urlparse(url).netloc if url else ""
            }

        # 1. Extract Page Title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text().strip()

        # 2. Decompose known boilerplate tags
        for tag in cls.BOILERPLATE_TAGS:
            for el in soup.find_all(tag):
                el.decompose()

        # 3. Decompose elements matching boilerplate class or id
        for el in soup.find_all(True):
            try:
                classes = " ".join(el.get("class", [])) if isinstance(el.get("class"), list) else str(el.get("class", ""))
                elem_id = str(el.get("id", ""))
                if cls.BOILERPLATE_PATTERNS.search(classes) or cls.BOILERPLATE_PATTERNS.search(elem_id):
                    # Only decompose if it doesn't contain the main article or massive content
                    if len(el.get_text()) < 800:
                        el.decompose()
            except Exception:
                continue

        # 4. Target primary content container if available (<article>, <main>, role="main")
        main_content = (
            soup.find("article") or
            soup.find("main") or
            soup.find("div", attrs={"role": "main"}) or
            soup.find("div", class_=re.compile(r'(content|article|body|post)', re.I)) or
            soup.body or
            soup
        )

        # 5. Extract text paragraphs
        paragraphs = []
        for p in main_content.find_all(["p", "h1", "h2", "h3", "h4", "li"]):
            text = p.get_text().strip()
            # Only keep substantive text blocks (>= 20 characters)
            if len(text) >= 20:
                paragraphs.append(text)

        if not paragraphs:
            # Fallback to whole body text if no paragraph structure found
            raw_text = main_content.get_text(separator=" ")
            clean_text = re.sub(r'\s+', ' ', raw_text).strip()
        else:
            clean_text = "\n\n".join(paragraphs)

        domain = urlparse(url).netloc if url else ""

        return {
            "title": title,
            "clean_text": clean_text,
            "word_count": len(clean_text.split()),
            "domain": domain
        }
