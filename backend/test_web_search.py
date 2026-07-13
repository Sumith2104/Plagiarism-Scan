import asyncio
import logging
from app.core.web_search import WebSearcher

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_search():
    searcher = WebSearcher.get_instance()
    
    # Text from a known source (e.g., Python Wikipedia page)
    text = """
    Python is a high-level, general-purpose programming language. Its design philosophy emphasizes code readability with the use of significant indentation.
    Python is dynamically typed and garbage-collected. It supports multiple programming paradigms, including structured (particularly procedural), object-oriented and functional programming.
    """
    
    print("Starting search test...")
    results = await searcher._search_and_compare_async(text)
    
    with open("test_output.txt", "w", encoding="utf-8") as f:
        f.write(f"Found {len(results)} matches:\n")
        for res in results:
            f.write(f"- [{res['similarity']}%] {res['title']} ({res['url']})\n")

if __name__ == "__main__":
    asyncio.run(test_search())
