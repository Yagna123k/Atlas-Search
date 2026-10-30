"""
Immutable Index Segment
Implements an append-only, immutable inverted index segment with compressed postings,
positional indexing, document metadata, and cryptographic checksum validation.
"""

from typing import Dict, List, Any, Optional, Tuple
import os
import json
import hashlib
import time
from core.tokenizer import Tokenizer
from core.index.compression import compress_postings, decompress_postings


class Segment:
    """
    An immutable index segment. Once frozen, its contents cannot be altered,
    ensuring safe lock-free concurrent reads while new segments are constructed.
    """
    def __init__(self, segment_id: str, tokenizer: Optional[Tokenizer] = None):
        self.segment_id = segment_id
        self.tokenizer = tokenizer or Tokenizer()
        
        # Raw term postings during build: term -> {doc_id: [positions]}
        self._raw_postings: Dict[str, Dict[int, List[int]]] = {}
        
        # Frozen compressed postings: term -> compressed_bytes
        self.compressed_postings: Dict[str, bytes] = {}
        
        # Document metadata store: doc_id -> dict
        self.documents: Dict[int, Dict[str, Any]] = {}
        
        # Document lengths (token count)
        self.doc_lengths: Dict[int, int] = {}
        
        # Document frequency (number of docs containing term): term -> int
        self.doc_frequencies: Dict[str, int] = {}
        
        self.total_docs: int = 0
        self.total_tokens: int = 0
        self.avg_doc_length: float = 0.0
        self.is_frozen: bool = False
        self.checksum: str = ""
        self.created_at: float = time.time()

    def add_document(self, doc_id: int, title: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Adds a document to the active segment before it is frozen."""
        if self.is_frozen:
            raise RuntimeError(f"Cannot add document {doc_id} to frozen segment {self.segment_id}")

        meta = metadata.copy() if metadata else {}
        meta["title"] = title
        meta["body"] = body
        meta["id"] = doc_id
        if "timestamp" not in meta:
            meta["timestamp"] = time.time()
        if "language" not in meta:
            meta["language"] = "generic"

        # Tokenize title and body with positions
        # Boost title positions: titles are tokenized first
        combined_text = f"{title} {body}"
        tokens_with_pos = self.tokenizer.tokenize_with_positions(combined_text)
        
        doc_len = len(tokens_with_pos)
        self.doc_lengths[doc_id] = doc_len
        self.total_tokens += doc_len
        self.documents[doc_id] = meta

        # Populate in-memory postings
        for token, pos in tokens_with_pos:
            if token not in self._raw_postings:
                self._raw_postings[token] = {}
            if doc_id not in self._raw_postings[token]:
                self._raw_postings[token][doc_id] = []
            self._raw_postings[token][doc_id].append(pos)

        self.total_docs += 1

    def freeze(self) -> None:
        """
        Compresses postings lists, calculates aggregate statistics,
        computes segment checksum, and marks segment as immutable.
        """
        if self.is_frozen:
            return

        self.avg_doc_length = (self.total_tokens / self.total_docs) if self.total_docs > 0 else 0.0

        hasher = hashlib.sha256()
        hasher.update(self.segment_id.encode("utf-8"))

        for term, doc_map in sorted(self._raw_postings.items()):
            sorted_doc_ids = sorted(doc_map.keys())
            self.doc_frequencies[term] = len(sorted_doc_ids)
            
            term_freqs = [len(doc_map[did]) for did in sorted_doc_ids]
            positions_list = [doc_map[did] for did in sorted_doc_ids]
            
            compressed = compress_postings(sorted_doc_ids, term_freqs, positions_list)
            self.compressed_postings[term] = compressed
            
            hasher.update(term.encode("utf-8"))
            hasher.update(compressed)

        # Clear raw map to free memory
        self._raw_postings.clear()
        
        self.checksum = hasher.hexdigest()
        self.is_frozen = True

    def get_postings(self, term: str) -> Tuple[List[int], List[int], List[List[int]]]:
        """
        Retrieves and decompresses postings for a given term.
        Returns: (doc_ids, term_frequencies, positions_list)
        """
        normalized_term = self.tokenizer.normalize(term)
        stemmed_term = self.tokenizer.tokenize(normalized_term)
        lookup_term = stemmed_term[0] if stemmed_term else normalized_term

        if not self.is_frozen:
            if lookup_term not in self._raw_postings:
                return [], [], []
            doc_map = self._raw_postings[lookup_term]
            sorted_dids = sorted(doc_map.keys())
            tf = [len(doc_map[d]) for d in sorted_dids]
            pos = [doc_map[d] for d in sorted_dids]
            return sorted_dids, tf, pos

        if lookup_term not in self.compressed_postings:
            return [], [], []

        return decompress_postings(self.compressed_postings[lookup_term])

    def serialize_metadata(self) -> Dict[str, Any]:
        """Serializes segment summary for manifest tracking."""
        return {
            "segment_id": self.segment_id,
            "total_docs": self.total_docs,
            "total_tokens": self.total_tokens,
            "avg_doc_length": self.avg_doc_length,
            "vocabulary_size": len(self.compressed_postings) if self.is_frozen else len(self._raw_postings),
            "checksum": self.checksum,
            "is_frozen": self.is_frozen,
            "created_at": self.created_at,
        }
