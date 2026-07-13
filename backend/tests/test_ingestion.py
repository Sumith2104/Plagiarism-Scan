import os
import pytest
from app.core.ingestion import TextExtractor
from app.core.cleaning import TextCleaner

def test_text_cleaner():
    raw = "Hello   World! \n\n This is a test."
    cleaned = TextCleaner.clean(raw)
    assert "Hello World!" in cleaned
    assert "This is a test." in cleaned
    assert "\n" in cleaned # Should preserve line breaks between paragraphs

def test_normalization():
    raw = "Hello, World!"
    norm = TextCleaner.normalize_for_matching(raw)
    assert norm == "hello world"

# Mocking file operations would be better, but for now we'll skip actual file reading
# unless we create temp files.
def test_extractor_file_not_found():
    with pytest.raises(FileNotFoundError):
        TextExtractor.extract("non_existent_file.txt", "text/plain")
