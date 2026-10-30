"""
Query-Document Feature Extractor for Learning-to-Rank (LTR)
Extracts lexical, semantic, metadata, intent, and freshness features
with feature explanations and attribution support.
"""

from typing import Dict, List, Any, Optional
import math
import time
import numpy as np
from core.tokenizer import Tokenizer


FEATURE_NAMES = [
    "bm25_score",
    "dense_score",
    "title_match_ratio",
    "body_coverage_ratio",
    "language_affinity",
    "freshness_score",
    "length_ratio",
    "channel_consensus",
]


class FeatureExtractor:
    """
    Extracts numerical feature vectors for (query, document) pairs.
    """
    def __init__(self, tokenizer: Optional[Tokenizer] = None):
        self.tokenizer = tokenizer or Tokenizer()
        
        # Recognized programming language / technology tokens
        self.tech_languages = {
            "python", "java", "jvm", "rust", "go", "golang", "c++", "cpp",
            "csharp", "c#", "javascript", "typescript", "node", "ruby", "php"
        }

    def detect_query_language(self, query: str) -> Optional[str]:
        """Infers programming language intent from query text."""
        tokens = self.tokenizer.tokenize(query)
        for t in tokens:
            if t in self.tech_languages:
                if t in ("golang", "go"):
                    return "go"
                if t in ("jvm", "java"):
                    return "java"
                if t in ("cpp", "c++"):
                    return "c++"
                return t
        return None

    def extract_features(
        self,
        query: str,
        doc: Dict[str, Any],
        avg_doc_length: float = 100.0,
        current_time: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Extracts all named features for a single candidate document.
        """
        now = current_time or time.time()
        q_tokens = self.tokenizer.tokenize(query)
        q_token_set = set(q_tokens) if q_tokens else set()
        
        title = doc.get("title", "")
        body = doc.get("body", "")
        title_tokens = set(self.tokenizer.tokenize(title))
        body_tokens = set(self.tokenizer.tokenize(body))

        # 1. Lexical BM25 score (normalized)
        bm25_raw = float(doc.get("lexical_score") or 0.0)
        bm25_norm = min(1.0, bm25_raw / 25.0) if bm25_raw > 0 else 0.0

        # 2. Dense semantic score
        dense_raw = float(doc.get("dense_score") or 0.0)
        dense_norm = max(0.0, min(1.0, dense_raw))

        # 3. Title exact term match ratio
        if q_token_set:
            title_matches = len(q_token_set & title_tokens)
            title_ratio = title_matches / len(q_token_set)
        else:
            title_ratio = 0.0

        # 4. Body term coverage ratio
        if q_token_set:
            body_matches = len(q_token_set & body_tokens)
            body_coverage = body_matches / len(q_token_set)
        else:
            body_coverage = 0.0

        # 5. Language Affinity Feature:
        # Detects mismatch between query technology intent and doc metadata
        query_lang = self.detect_query_language(query)
        doc_lang = doc.get("language", "generic").lower()
        if query_lang:
            if doc_lang == query_lang or (query_lang == "java" and doc_lang == "jvm"):
                language_affinity = 1.0  # Perfect compatibility
            elif doc_lang in self.tech_languages and doc_lang != query_lang:
                language_affinity = -1.0  # Conflicting language penalty (e.g. Java doc for Python query)
            else:
                language_affinity = 0.0  # Generic doc
        else:
            language_affinity = 0.2 if doc_lang != "generic" else 0.0

        # 6. Freshness decay: exp(-0.0000001 * delta_seconds)
        doc_ts = float(doc.get("timestamp") or now)
        delta_seconds = max(0.0, now - doc_ts)
        # Half-life of approx 60 days
        half_life_seconds = 60 * 24 * 3600
        freshness = math.exp(-math.log(2) * (delta_seconds / half_life_seconds))

        # 7. Document length ratio
        doc_len = len(title_tokens) + len(body_tokens)
        length_ratio = min(3.0, (doc_len / avg_doc_length)) if avg_doc_length > 0 else 1.0

        # 8. Channel consensus: retrieved by both BM25 and Dense
        prov = doc.get("channel_provenance", "")
        if prov == "both":
            channel_consensus = 1.0
        elif prov in ("lexical", "dense"):
            channel_consensus = 0.5
        else:
            channel_consensus = 0.2

        features = {
            "bm25_score": round(bm25_norm, 4),
            "dense_score": round(dense_norm, 4),
            "title_match_ratio": round(title_ratio, 4),
            "body_coverage_ratio": round(body_coverage, 4),
            "language_affinity": round(language_affinity, 4),
            "freshness_score": round(freshness, 4),
            "length_ratio": round(length_ratio, 4),
            "channel_consensus": round(channel_consensus, 4),
        }
        return features

    def to_feature_vector(self, features_dict: Dict[str, float]) -> np.ndarray:
        """Converts feature dictionary to ordered numpy vector."""
        return np.array([features_dict[name] for name in FEATURE_NAMES], dtype=np.float32)
