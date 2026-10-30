"""
Atlas Search Tokenizer & Text Normalizer
Production-grade tokenization with position tracking, programming term preservation,
stemming, and configurable stop-word filtering.
"""

from typing import List, Tuple, Set, Optional
import re
import unicodedata

# Standard Information Retrieval stop words (can be omitted for exact phrase search)
DEFAULT_STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than",
    "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
    "this", "those", "through", "to", "too", "under", "until", "up", "very",
    "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
    "what", "what's", "when", "when's", "where", "where's", "which", "while",
    "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't",
    "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves"
}

# Regex pattern that preserves programming terms (c++, c#, .net, v8, p99, python3, etc.)
# and handles hyphenated phrases / underscores
TOKEN_PATTERN = re.compile(
    r"[a-zA-Z0-9]+(?:[+#]+|\.[a-zA-Z0-9]+)*|[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*",
    re.IGNORECASE
)


class SimpleStemmer:
    """
    Lightweight, deterministic suffix-stripping stemmer based on Lovins/Porter heuristics.
    Standardizes plural forms, gerunds, and past tenses without external dependencies.
    """
    SUFFIXES = [
        ("sses", "ss"),
        ("ies", "i"),
        ("ization", "ize"),
        ("ational", "ate"),
        ("fulness", "ful"),
        ("ousness", "ous"),
        ("iveness", "ive"),
        ("ational", "ate"),
        ("ational", "ate"),
        ("ing", ""),
        ("ed", ""),
        ("ly", ""),
        ("es", "e"),
        ("s", ""),
    ]

    @classmethod
    def stem(cls, word: str) -> str:
        if len(word) <= 3:
            return word
        w = word.lower()
        # Handle sibilant plurals: indexes -> index, boxes -> box, searches -> search
        if w.endswith(("xes", "ches", "shes", "zes")):
            return w[:-2]
        for suffix, replacement in cls.SUFFIXES:
            if w.endswith(suffix):
                stemmed = w[:-len(suffix)] + replacement
                if len(stemmed) >= 3:
                    return stemmed
        return w


class Tokenizer:
    """
    Production Tokenizer with configurable stemming, stop-word removal,
    and term position extraction for inverted index generation.
    """
    def __init__(
        self,
        use_stemming: bool = True,
        remove_stopwords: bool = True,
        min_token_length: int = 1,
        max_token_length: int = 64,
        stop_words: Optional[Set[str]] = None
    ):
        self.use_stemming = use_stemming
        self.remove_stopwords = remove_stopwords
        self.min_token_length = min_token_length
        self.max_token_length = max_token_length
        self.stop_words = stop_words if stop_words is not None else DEFAULT_STOP_WORDS

    def normalize(self, text: str) -> str:
        """Unicode normalization (NFKC) and case folding."""
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKC", text)
        return normalized.lower()

    def tokenize_with_positions(self, text: str) -> List[Tuple[str, int]]:
        """
        Tokenizes text and returns a list of (token, position) tuples.
        Positions correspond to token indices (0-indexed).
        """
        normalized = self.normalize(text)
        raw_tokens = TOKEN_PATTERN.findall(normalized)
        
        result: List[Tuple[str, int]] = []
        for pos, raw_token in enumerate(raw_tokens):
            if len(raw_token) < self.min_token_length or len(raw_token) > self.max_token_length:
                continue
            if self.remove_stopwords and raw_token in self.stop_words:
                continue
            
            token = SimpleStemmer.stem(raw_token) if self.use_stemming else raw_token
            result.append((token, pos))
            
        return result

    def tokenize(self, text: str) -> List[str]:
        """Returns just the list of token strings."""
        return [token for token, _ in self.tokenize_with_positions(text)]

    def extract_ngrams(self, tokens: List[str], n: int = 2) -> List[str]:
        """Generates n-grams for phrase boosting."""
        if len(tokens) < n:
            return []
        return ["_".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]
