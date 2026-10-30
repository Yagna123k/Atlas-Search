"""Tests for Delta and Variable-Byte Compression"""
import pytest
from core.index.compression import (
    delta_encode, delta_decode,
    vbyte_encode, vbyte_decode,
    compress_postings, decompress_postings
)


def test_delta_roundtrip():
    doc_ids = [10, 25, 40, 105, 500, 1000]
    deltas = delta_encode(doc_ids)
    assert deltas == [10, 15, 15, 65, 395, 500]
    decoded = delta_decode(deltas)
    assert decoded == doc_ids


def test_vbyte_roundtrip():
    numbers = [0, 1, 127, 128, 255, 16384, 1000000]
    encoded = vbyte_encode(numbers)
    decoded = vbyte_decode(encoded)
    assert decoded == numbers


def test_postings_compression_roundtrip():
    doc_ids = [5, 12, 18]
    term_freqs = [2, 1, 3]
    positions = [[0, 4], [2], [1, 5, 9]]

    compressed = compress_postings(doc_ids, term_freqs, positions)
    assert isinstance(compressed, bytes)
    assert len(compressed) > 0

    d_ids, d_tfs, d_pos = decompress_postings(compressed)
    assert d_ids == doc_ids
    assert d_tfs == term_freqs
    assert d_pos == positions
