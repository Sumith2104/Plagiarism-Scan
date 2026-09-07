"""
Advanced Sequence Alignment and Fragment Matching Module.
Implements Longest Common Subsequence (LCS), n-gram containment,
and local alignment to identify verbatim copying, mosaic plagiarism,
patchwriting (synonym replacement), and clause reordering.
"""

from typing import List, Dict, Any, Tuple, Optional
import re
from difflib import SequenceMatcher


class SequenceAligner:
    """
    Computes fine-grained alignment between two text segments.
    Detects:
      - Exact / Verbatim copying
      - Patchwriting / Near-verbatim (synonym substitutions or small deletions)
      - Mosaic plagiarism (interspersed fragments from a source)
    """

    def __init__(self, min_matching_tokens: int = 4):
        self.min_matching_tokens = min_matching_tokens

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenize into lowercase words while keeping words clean."""
        return re.findall(r'\b[a-zA-Z0-9_\'-]+\b', text.lower())

    def compute_lcs(self, tokens_a: List[str], tokens_b: List[str]) -> List[str]:
        """
        Computes the Longest Common Subsequence between two token lists.
        Used to measure structural phrase borrowing even when words are inserted.
        """
        n, m = len(tokens_a), len(tokens_b)
        if n == 0 or m == 0:
            return []

        # Optimization for memory: cap to max 400 tokens to keep execution fast.
        max_len = 400
        tokens_a = tokens_a[:max_len]
        tokens_b = tokens_b[:max_len]
        n, m = len(tokens_a), len(tokens_b)

        dp = [[0] * (m + 1) for _ in range(n + 1)]

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if tokens_a[i - 1] == tokens_b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        # Traceback to reconstruct the LCS tokens
        lcs_tokens = []
        i, j = n, m
        while i > 0 and j > 0:
            if tokens_a[i - 1] == tokens_b[j - 1]:
                lcs_tokens.append(tokens_a[i - 1])
                i -= 1
                j -= 1
            elif dp[i - 1][j] >= dp[i][j - 1]:
                i -= 1
            else:
                j -= 1

        lcs_tokens.reverse()
        return lcs_tokens

    def _find_best_window(self, tokens_a: List[str], tokens_b: List[str], window_size: int = 350, step: int = 150) -> Tuple[List[str], int]:
        """
        Finds the sub-sequence of tokens_b that best overlaps with tokens_a.
        Returns (best_tokens_b, offset_in_original_b).
        """
        if len(tokens_b) <= window_size:
            return tokens_b, 0

        # Emphasize salient words (> 2 chars)
        salient_a = set(w for w in tokens_a if len(w) > 2)
        if not salient_a:
            salient_a = set(tokens_a)

        best_overlap = -1
        best_start = 0

        for start in range(0, len(tokens_b), step):
            end = min(len(tokens_b), start + window_size)
            window_set = set(tokens_b[start:end])
            overlap = len(salient_a.intersection(window_set))
            if overlap > best_overlap:
                best_overlap = overlap
                best_start = start
            if end >= len(tokens_b):
                break

        slice_start = max(0, best_start - 30)
        slice_end = min(len(tokens_b), best_start + window_size + 30)
        return tokens_b[slice_start:slice_end], slice_start

    def align_texts(self, text_a: str, text_b: str) -> Dict[str, Any]:
        """
        Aligns text_a (suspect text) against text_b (candidate source).
        Returns alignment metrics, classified matching blocks, and an overall similarity score.
        """
        if not text_a or not text_b:
            return {
                "similarity_score": 0.0,
                "lcs_length": 0,
                "lcs_ratio": 0.0,
                "verbatim_blocks": [],
                "mosaic_blocks": [],
                "classification": "no_match"
            }

        tokens_a = self.tokenize(text_a)
        tokens_b = self.tokenize(text_b)

        if not tokens_a or not tokens_b:
            return {
                "similarity_score": 0.0,
                "lcs_length": 0,
                "lcs_ratio": 0.0,
                "verbatim_blocks": [],
                "mosaic_blocks": [],
                "classification": "no_match"
            }

        # Locate the most relevant window in tokens_b to align against
        window_b, offset_b = self._find_best_window(tokens_a, tokens_b)

        # 1. Longest Common Subsequence against the focused window
        lcs = self.compute_lcs(tokens_a, window_b)
        lcs_len = len(lcs)
        lcs_ratio = (lcs_len / len(tokens_a)) if tokens_a else 0.0

        # 2. Detailed matching blocks using SequenceMatcher
        matcher = SequenceMatcher(None, tokens_a, window_b)
        matching_blocks = matcher.get_matching_blocks()

        verbatim_blocks = []
        total_verbatim_tokens = 0

        for block in matching_blocks:
            # block has a, b, size
            if block.size >= self.min_matching_tokens:
                matched_phrase = " ".join(tokens_a[block.a : block.a + block.size])
                verbatim_blocks.append({
                    "suspect_start": block.a,
                    "suspect_end": block.a + block.size,
                    "source_start": offset_b + block.b,
                    "source_end": offset_b + block.b + block.size,
                    "token_count": block.size,
                    "matched_tokens": matched_phrase
                })
                total_verbatim_tokens += block.size

        verbatim_ratio = (total_verbatim_tokens / len(tokens_a)) if tokens_a else 0.0

        # 3. Mosaic Plagiarism Detection:
        # If there are multiple short matching blocks clustered within short distances,
        # it indicates fragments spliced together.
        mosaic_blocks = []
        if len(verbatim_blocks) >= 2:
            for i in range(len(verbatim_blocks) - 1):
                gap = verbatim_blocks[i + 1]["suspect_start"] - verbatim_blocks[i]["suspect_end"]
                if 0 < gap <= 8:  # 1-8 filler words between copied segments
                    mosaic_blocks.append({
                        "block_1": verbatim_blocks[i]["matched_tokens"],
                        "block_2": verbatim_blocks[i + 1]["matched_tokens"],
                        "intervening_gap_tokens": gap
                    })

        # 4. Containment / Jaccard Token Metric
        set_a = set(tokens_a)
        set_b = set(tokens_b)
        containment = (len(set_a.intersection(set_b)) / len(set_a)) if set_a else 0.0

        # 5. Composite Score Calculation
        # Verbatim weight: 50%, LCS (structure): 30%, Vocabulary Containment: 20%
        composite_score = (verbatim_ratio * 0.50) + (lcs_ratio * 0.30) + (containment * 0.20)
        composite_score = round(min(1.0, max(0.0, composite_score)) * 100, 2)

        # 6. Categorization
        if composite_score >= 70 or verbatim_ratio >= 0.65:
            classification = "verbatim_plagiarism"
        elif mosaic_blocks and composite_score >= 35:
            classification = "mosaic_plagiarism"
        elif composite_score >= 40:
            classification = "paraphrase_plagiarism"
        elif composite_score >= 20:
            classification = "loose_overlap"
        else:
            classification = "negligible"

        return {
            "similarity_score": composite_score,
            "verbatim_ratio": round(verbatim_ratio, 4),
            "lcs_length": lcs_len,
            "lcs_ratio": round(lcs_ratio, 4),
            "containment": round(containment, 4),
            "verbatim_blocks": verbatim_blocks,
            "mosaic_blocks": mosaic_blocks,
            "classification": classification
        }

    @staticmethod
    def extract_citations(text: str) -> List[Dict[str, Any]]:
        """
        Extracts cited segments, bracketed references [1], (Author, 2023),
        and direct quote strings ("...") so they can be exempted or audited.
        """
        citations = []

        # 1. Quoted text: "..." or '...'
        quote_pattern = r'["“]([^"”]{10,500})["”]'
        for match in re.finditer(quote_pattern, text):
            citations.append({
                "type": "direct_quote",
                "text": match.group(1),
                "start": match.start(),
                "end": match.end()
            })

        # 2. Parenthetical citations: (Smith et al., 2020), (Johnson & Lee, 2021)
        citation_pattern = r'\(([A-Z][a-zA-Z\s.,&]+?,\s*\d{4}[^)]*)\)'
        for match in re.finditer(citation_pattern, text):
            citations.append({
                "type": "parenthetical_citation",
                "citation": match.group(1),
                "start": match.start(),
                "end": match.end()
            })

        # 3. Numeric citations: [1], [2-4], [12]
        numeric_pattern = r'\[\s*(\d+(?:\s*[-–,]\s*\d+)*)\s*\]'
        for match in re.finditer(numeric_pattern, text):
            citations.append({
                "type": "numeric_citation",
                "citation": f"[{match.group(1)}]",
                "start": match.start(),
                "end": match.end()
            })

        return citations
