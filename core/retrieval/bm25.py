"""
BM25Okapi Retrieval Engine
Production BM25 ranking algorithm with term frequency saturation (k1),
document length normalization (b), title field boosting, and positional phrase proximity.
"""

from typing import Dict, List, Tuple, Any, Optional
import math
from core.tokenizer import Tokenizer
from core.index.manager import IndexManager


class BM25Retriever:
    """
    Implements BM25Okapi with field weighting and phrase proximity scoring.
    """
    def __init__(
        self,
        index_manager: IndexManager,
        k1: float = 1.2,
        b: float = 0.75,
        title_boost: float = 2.0,
        phrase_boost: float = 0.5
    ):
        self.index_manager = index_manager
        self.k1 = k1
        self.b = b
        self.title_boost = title_boost
        self.phrase_boost = phrase_boost
        self.tokenizer = index_manager.tokenizer

    def compute_idf(self, df: int, total_docs: int) -> float:
        """
        Standard Lucene/Robertson BM25 IDF with smoothing:
        ln(1 + (N - n + 0.5) / (n + 0.5))
        """
        if total_docs == 0:
            return 0.0
        return math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))

    def retrieve(
        self,
        query: str,
        top_k: int = 50,
        explain: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top_k candidates using BM25 across all active segments.
        Masks tombstoned documents.
        """
        query_tokens_with_pos = self.tokenizer.tokenize_with_positions(query)
        if not query_tokens_with_pos:
            return []

        query_terms = [t for t, _ in query_tokens_with_pos]
        unique_query_terms = list(dict.fromkeys(query_terms))

        # Gather aggregate statistics across active segments
        manifest = self.index_manager.manifest_manager.current_manifest
        active_segment_ids = manifest.active_segment_ids
        tombstones = self.index_manager.tombstones

        segments = [self.index_manager.segments[s] for s in active_segment_ids if s in self.index_manager.segments]
        if self.index_manager.active_writable_segment and self.index_manager.active_writable_segment.total_docs > 0:
            segments.append(self.index_manager.active_writable_segment)

        total_docs = sum(s.total_docs for s in segments)
        total_tokens = sum(s.total_tokens for s in segments)
        avgdl = (total_tokens / total_docs) if total_docs > 0 else 1.0

        # Term document frequencies across segments
        global_df: Dict[str, int] = {term: 0 for term in unique_query_terms}
        # Inverted index hits: term -> {doc_id: (tf, [positions], segment)}
        term_postings_map: Dict[str, Dict[int, Tuple[int, List[int], Any]]] = {t: {} for t in unique_query_terms}

        for seg in segments:
            for term in unique_query_terms:
                doc_ids, tfs, pos_list = seg.get_postings(term)
                valid_hits = 0
                for did, tf, positions in zip(doc_ids, tfs, pos_list):
                    if did in tombstones:
                        continue
                    term_postings_map[term][did] = (tf, positions, seg)
                    valid_hits += 1
                global_df[term] += valid_hits

        # Candidate doc scores accumulator: doc_id -> score
        doc_scores: Dict[int, float] = {}
        term_contributions: Dict[int, Dict[str, float]] = {}
        candidate_docs_info: Dict[int, Dict[str, Any]] = {}

        # Precompute IDFs
        idfs = {term: self.compute_idf(global_df[term], total_docs) for term in unique_query_terms}

        for term in unique_query_terms:
            idf = idfs[term]
            if idf <= 0:
                continue

            for doc_id, (tf, positions, seg) in term_postings_map[term].items():
                doc_len = seg.doc_lengths.get(doc_id, int(avgdl))
                doc_meta = seg.documents.get(doc_id, {})
                candidate_docs_info[doc_id] = doc_meta

                # BM25 term frequency saturation with length normalization
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / avgdl))
                term_score = idf * (numerator / denominator)

                # Check if term appears in title
                title_text = doc_meta.get("title", "")
                if term in self.tokenizer.tokenize(title_text):
                    term_score *= self.title_boost

                if doc_id not in doc_scores:
                    doc_scores[doc_id] = 0.0
                    term_contributions[doc_id] = {}

                doc_scores[doc_id] += term_score
                term_contributions[doc_id][term] = term_score

        # Phrase proximity bonus: check if adjacent query terms appear adjacent in doc
        if len(unique_query_terms) > 1 and self.phrase_boost > 0:
            for doc_id in doc_scores:
                seg_id = self.index_manager.doc_to_segment.get(doc_id)
                seg = self.index_manager.segments.get(seg_id) if seg_id else None
                if not seg and self.index_manager.active_writable_segment:
                    seg = self.index_manager.active_writable_segment

                # Check position distance between consecutive terms
                phrase_matches = 0
                for i in range(len(unique_query_terms) - 1):
                    t1, t2 = unique_query_terms[i], unique_query_terms[i + 1]
                    if doc_id in term_postings_map[t1] and doc_id in term_postings_map[t2]:
                        pos1 = term_postings_map[t1][doc_id][1]
                        pos2 = term_postings_map[t2][doc_id][1]
                        # Check if any position pair has distance 1
                        for p1 in pos1:
                            if (p1 + 1) in pos2:
                                phrase_matches += 1
                                break

                if phrase_matches > 0:
                    doc_scores[doc_id] += phrase_matches * self.phrase_boost

        # Sort candidates by score descending
        sorted_candidates = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for rank, (doc_id, score) in enumerate(sorted_candidates, start=1):
            doc = candidate_docs_info.get(doc_id) or self.index_manager.get_document(doc_id) or {}
            entry = {
                "doc_id": doc_id,
                "score": round(score, 4),
                "lexical_rank": rank,
                "title": doc.get("title", f"Doc {doc_id}"),
                "body": doc.get("body", ""),
                "language": doc.get("language", "generic"),
                "timestamp": doc.get("timestamp", 0),
            }
            if explain:
                entry["term_contributions"] = {
                    t: round(s, 4) for t, s in term_contributions.get(doc_id, {}).items()
                }
                entry["idfs"] = {t: round(idfs.get(t, 0.0), 4) for t in unique_query_terms}
            results.append(entry)

        return results
