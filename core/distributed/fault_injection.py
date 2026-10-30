"""
Fault Injection and Resilience Verification Subsystem
Executes automated failure-injection scenarios to prove systems-level reliability:
1. Worker crash & failover
2. Corrupted index segment rejection
3. Atomic rollback to previous manifest
4. Concurrent indexing under query load
"""

from typing import Dict, List, Any
import time
import concurrent.futures
from core.index.manager import IndexManager
from core.index.segment import Segment
from core.index.manifest import ManifestValidationError
from core.distributed.coordinator import DistributedCoordinator, ShardWorker


class FaultInjectionHarness:
    """
    Simulates production failure modes and measures recovery behavior.
    """
    def __init__(self, index_manager: IndexManager):
        self.index_manager = index_manager

    def test_worker_crash_and_recovery(self) -> Dict[str, Any]:
        """
        Scenario 1: A shard worker abruptly crashes mid-query.
        Verifies coordinator recovers, isolates failure, and returns partial results.
        """
        w1 = ShardWorker("shard-us-east-1", self.index_manager)
        w2 = ShardWorker("shard-us-west-2", self.index_manager)
        w3 = ShardWorker("shard-eu-central-1", self.index_manager)
        
        coordinator = DistributedCoordinator(shards=[w1, w2, w3], timeout_seconds=0.3)

        # Baseline: All 3 healthy
        base_resp = coordinator.scatter_gather("memory profiling", top_k=5)
        
        # Inject crash on w2
        w2.is_healthy = False
        t_crash_start = time.perf_counter()
        fault_resp = coordinator.scatter_gather("memory profiling", top_k=5)
        recovery_time_ms = (time.perf_counter() - t_crash_start) * 1000.0

        # Restore w2
        w2.is_healthy = True
        restored_resp = coordinator.scatter_gather("memory profiling", top_k=5)

        passed = (
            base_resp["responding_shards"] == 3 and
            fault_resp["failed_shards"] == ["shard-us-west-2"] and
            fault_resp["responding_shards"] == 2 and
            restored_resp["responding_shards"] == 3
        )

        return {
            "test_name": "worker_crash_and_failover",
            "passed": passed,
            "baseline_shards": base_resp["responding_shards"],
            "failed_shard_identified": fault_resp["failed_shards"],
            "degraded_mode_active": fault_resp["degraded_mode"],
            "recovery_time_ms": round(recovery_time_ms, 2),
            "status": "PASSED" if passed else "FAILED"
        }

    def test_corrupted_segment_rejection(self) -> Dict[str, Any]:
        """
        Scenario 2: An indexing worker finishes building a segment, but a bitflip
        or partial write causes a checksum validation mismatch.
        Verifies manifest validator blocks publication and leaves active manifest untouched.
        """
        initial_gen = self.index_manager.manifest_manager.current_manifest.generation
        
        # Create a malicious/corrupted segment with bogus checksum
        bad_seg = Segment("seg_corrupted_test")
        bad_seg.add_document(999, "Corrupted Title", "Corrupted Body")
        bad_seg.freeze()
        bad_seg.checksum = "00000000deadbeefbadchecksum00000000"  # Tampered hash
        
        self.index_manager.segments[bad_seg.segment_id] = bad_seg

        validation_caught = False
        try:
            self.index_manager.manifest_manager.publish_new_version(
                active_segment_ids=[bad_seg.segment_id],
                tombstones=set(),
                segment_checksums={bad_seg.segment_id: "expected_legit_hash"},
                total_live_docs=1,
                segments_map=self.index_manager.segments
            )
        except ManifestValidationError:
            validation_caught = True

        current_gen = self.index_manager.manifest_manager.current_manifest.generation
        passed = validation_caught and (current_gen == initial_gen)

        return {
            "test_name": "corrupted_segment_rejection",
            "passed": passed,
            "manifest_generation_preserved": current_gen == initial_gen,
            "checksum_mismatch_caught": validation_caught,
            "status": "PASSED" if passed else "FAILED"
        }

    def test_atomic_rollback(self) -> Dict[str, Any]:
        """
        Scenario 3: An experimental index release causes a relevance regression.
        Verifies system atomically rolls back to the prior manifest generation.
        """
        gen_before = self.index_manager.manifest_manager.current_manifest.generation
        
        # Add a dummy doc and commit
        self.index_manager.index_document(8888, "Temp Doc", "Temp Body")
        new_manifest = self.index_manager.commit()
        gen_after_commit = new_manifest.generation
        
        # Trigger rollback
        rolled_back = self.index_manager.rollback_manifest()
        gen_after_rollback = rolled_back.generation if rolled_back else -1

        passed = (gen_after_commit == gen_before + 1) and (gen_after_rollback == gen_before)

        return {
            "test_name": "atomic_manifest_rollback",
            "passed": passed,
            "generation_before": gen_before,
            "generation_after_commit": gen_after_commit,
            "generation_after_rollback": gen_after_rollback,
            "status": "PASSED" if passed else "FAILED"
        }
