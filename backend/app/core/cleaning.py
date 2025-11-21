import re
import string

class TextCleaner:
    @staticmethod
    def clean(text: str) -> str:
        if not text:
            return ""
        
        # 1. Normalize whitespace (replace tabs, newlines, multiple spaces with single space)
        # We might want to keep newlines for paragraph structure, but for basic matching, single line is often easier.
        # Let's keep paragraphs separated by newline, but clean within them.
        
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                # Remove control characters
                line = "".join(ch for ch in line if ch.isprintable())
                # Normalize spaces
                line = re.sub(r'\s+', ' ', line)
                cleaned_lines.append(line)
        
        return "\n".join(cleaned_lines)

    @staticmethod
    def normalize_for_matching(text: str) -> str:
        """
        Aggressive normalization for lexical matching (lowercase, remove punctuation).
        """
        text = text.lower()
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
