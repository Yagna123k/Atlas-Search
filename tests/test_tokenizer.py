"""Tests for Tokenizer and Normalizer"""
import pytest
from core.tokenizer import Tokenizer, SimpleStemmer


def test_tokenizer_normalization():
    tokenizer = Tokenizer()
    normalized = tokenizer.normalize("PYTHON 3.13 & C++ Search Engine")
    assert "python" in normalized
    assert "c++" in normalized


def test_tokenizer_positions():
    tokenizer = Tokenizer(remove_stopwords=False, use_stemming=False)
    tokens_with_pos = tokenizer.tokenize_with_positions("reduce memory usage in python")
    tokens = [t for t, _ in tokens_with_pos]
    positions = [p for _, p in tokens_with_pos]
    
    assert "reduce" in tokens
    assert "memory" in tokens
    assert "python" in tokens
    assert positions == [0, 1, 2, 3, 4]


def test_stemmer_heuristics():
    assert SimpleStemmer.stem("profiling") == "profil"
    assert SimpleStemmer.stem("allocations") == "allocation"
    assert SimpleStemmer.stem("indexes") == "index"
