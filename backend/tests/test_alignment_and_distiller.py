from app.core.alignment import SequenceAligner
from app.core.scraper.distiller import WebDistiller

def test_sequence_aligner_verbatim():
    aligner = SequenceAligner()
    text_a = "Artificial intelligence and machine learning are revolutionizing modern healthcare and diagnostics."
    text_b = "Artificial intelligence and machine learning are revolutionizing modern healthcare and diagnostics everywhere."
    
    result = aligner.align_texts(text_a, text_b)
    assert result["similarity_score"] > 80
    assert result["classification"] == "verbatim_plagiarism"
    assert len(result["verbatim_blocks"]) >= 1

def test_sequence_aligner_citations():
    text = 'As noted by researchers, "deep learning has achieved unprecedented accuracy in medical imaging" (Smith et al., 2023) [4].'
    citations = SequenceAligner.extract_citations(text)
    
    types = [c["type"] for c in citations]
    assert "direct_quote" in types
    assert "parenthetical_citation" in types
    assert "numeric_citation" in types

def test_web_distiller():
    raw_html = """
    <html>
      <head><title>Test Article Page</title></head>
      <body>
        <nav><a href="/">Home</a><a href="/about">About</a></nav>
        <header><h1>Welcome to Our Site</h1></header>
        <article>
          <h2>The History of Computing</h2>
          <p>Alan Turing is widely considered to be the father of theoretical computer science and artificial intelligence.</p>
          <p>During the Second World War, Turing was a leading participant in wartime codebreaking at Bletchley Park.</p>
        </article>
        <div class="sidebar-advert">Buy our product now! Click here for 50% off discount.</div>
        <footer><p>&copy; 2026 Test Inc. All rights reserved.</p></footer>
      </body>
    </html>
    """
    distilled = WebDistiller.distill(raw_html, url="https://example.com/article")
    assert distilled["title"] == "Test Article Page"
    assert "Alan Turing" in distilled["clean_text"]
    assert "Buy our product" not in distilled["clean_text"]
    assert "Home" not in distilled["clean_text"]
    assert distilled["word_count"] > 10
