"""Tests for Atomic Manifest Publication and Rollback"""
import pytest
import os
import shutil
from core.tokenizer import Tokenizer
from core.index.manager import IndexManager
from core.index.manifest import ManifestValidationError
from core.distributed.fault_injection import FaultInjectionHarness


@pytest.fixture
def temp_index_manager(tmp_path):
    storage_dir = os.path.join(tmp_path, "index_test")
    im = IndexManager(storage_dir=storage_dir, tokenizer=Tokenizer())
    yield im
    if os.path.exists(storage_dir):
        shutil.rmtree(storage_dir, ignore_errors=True)


def test_atomic_publication_and_rollback(temp_index_manager):
    im = temp_index_manager
    im.index_document(1, "First Title", "First Body")
    m1 = im.commit()
    assert m1.generation == 2
    assert m1.total_live_docs == 1

    im.index_document(2, "Second Title", "Second Body")
    m2 = im.commit()
    assert m2.generation == 3
    assert m2.total_live_docs == 2

    # Rollback to generation 2
    rolled = im.rollback_manifest()
    assert rolled is not None
    assert rolled.generation == 2
    assert im.manifest_manager.current_manifest.generation == 2


def test_corrupted_checksum_rejection(temp_index_manager):
    im = temp_index_manager
    harness = FaultInjectionHarness(im)
    res = harness.test_corrupted_segment_rejection()
    assert res["passed"] is True
    assert res["status"] == "PASSED"
