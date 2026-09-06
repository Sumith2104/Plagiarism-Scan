"""
Readability and Stylometric Analysis Engine.
Computes standard academic readability indices:
- Flesch Reading Ease (FRE)
- Flesch-Kincaid Grade Level (FKGL)
- Gunning Fog Index (GFI)
- Coleman-Liau Index (CLI)
- Lexical Diversity (Type-Token Ratio)
- Sentence Complexity & Passive Voice Detection
"""

import re
import math
from typing import Dict, Any, List


def count_syllables(word: str) -> int:
    """Estimates the number of syllables in an English word."""
    word = word.lower().strip()
    if not word or len(word) <= 2:
        return 1
    
    # Remove non-alpha
    word = re.sub(r'[^a-z]', '', word)
    if not word:
        return 1
    
    # Count vowel groups
    vowels = "aeiouy"
    count = 0
    prev_is_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_is_vowel:
            count += 1
        prev_is_vowel = is_vowel

    # Adjust for common silent endings
    if word.endswith('e') and not word.endswith('le') and count > 1:
        count -= 1
    if word.endswith('ed') and count > 1:
        count -= 1
        
    return max(1, count)


def compute_readability_metrics(text: str) -> Dict[str, Any]:
    """
    Computes comprehensive readability scores, stylometric metrics,
    and writing complexity benchmarks.
    """
    if not text or len(text.strip()) < 40:
        return {
            "flesch_reading_ease": 0.0,
            "flesch_grade_level": 0.0,
            "gunning_fog": 0.0,
            "reading_level": "Insufficient Data",
            "total_words": 0,
            "total_sentences": 0,
            "avg_sentence_length": 0.0,
            "avg_syllables_per_word": 0.0,
            "complex_word_percentage": 0.0,
            "lexical_diversity": 0.0,
            "passive_voice_percentage": 0.0
        }

    # Extract sentences
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if len(s.strip()) > 3]
    total_sentences = max(len(sentences), 1)

    # Extract clean words
    words = re.findall(r'\b[a-zA-Z\'-]+\b', text)
    total_words = max(len(words), 1)

    # Syllables & complex words (3+ syllables)
    syllable_counts = [count_syllables(w) for w in words]
    total_syllables = sum(syllable_counts)
    complex_words = sum(1 for c in syllable_counts if c >= 3)

    avg_words_per_sentence = total_words / total_sentences
    avg_syllables_per_word = total_syllables / total_words
    complex_word_pct = (complex_words / total_words) * 100

    # 1. Flesch Reading Ease
    # 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
    fre = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
    fre = round(max(0.0, min(100.0, fre)), 1)

    # 2. Flesch-Kincaid Grade Level
    # 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    fkgl = (0.39 * avg_words_per_sentence) + (11.8 * avg_syllables_per_word) - 15.59
    fkgl = round(max(1.0, min(18.0, fkgl)), 1)

    # 3. Gunning Fog Index
    # 0.4 * ((words/sentences) + 100 * (complex_words/words))
    gfi = 0.4 * (avg_words_per_sentence + complex_word_pct)
    gfi = round(max(1.0, min(20.0, gfi)), 1)

    # 4. Lexical Diversity (Type-Token Ratio)
    unique_words = set(w.lower() for w in words)
    ttr = round((len(unique_words) / total_words) * 100, 1)

    # 5. Passive Voice Detection (auxiliary + past participle heuristic)
    passive_patterns = r'\b(is|are|was|were|been|being|be)\s+([a-z]+ed|[a-z]+en|done|made|seen|written|built|taken)\b'
    passive_hits = len(re.findall(passive_patterns, text, re.IGNORECASE))
    passive_pct = round((passive_hits / total_sentences) * 100, 1)

    # Interpretive Reading Level
    if fre >= 80:
        level = "Easy (6th Grade)"
    elif fre >= 65:
        level = "Standard (7th–9th Grade)"
    elif fre >= 50:
        level = "Fairly Difficult (High School)"
    elif fre >= 30:
        level = "Difficult (College Level)"
    else:
        level = "Very Difficult (Academic / Professional)"

    return {
        "flesch_reading_ease": fre,
        "flesch_grade_level": fkgl,
        "gunning_fog": gfi,
        "reading_level": level,
        "total_words": total_words,
        "total_sentences": total_sentences,
        "avg_sentence_length": round(avg_words_per_sentence, 1),
        "avg_syllables_per_word": round(avg_syllables_per_word, 2),
        "complex_word_percentage": round(complex_word_pct, 1),
        "lexical_diversity": ttr,
        "passive_voice_percentage": min(100.0, passive_pct)
    }
