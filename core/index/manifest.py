"""
Segment Manifest & Safe Atomic Publication Subsystem
Provides zero-downtime atomic publication of index updates, validation checks,
and rollback capabilities for fault tolerance and regression prevention.
"""

from typing import Dict, List, Set, Any, Optional
import os
import json
import hashlib
import time


class ManifestValidationError(Exception):
    """Raised when an index manifest fails validation during publication."""
    pass


class Manifest:
    """
    Metadata tracking the current active view of the index.
    Readers always load from the latest atomically published manifest.
    """
    def __init__(
        self,
        generation: int = 1,
        active_segment_ids: Optional[List[str]] = None,
        tombstones: Optional[Set[int]] = None,
        segment_checksums: Optional[Dict[str, str]] = None,
        total_live_docs: int = 0,
        published_at: Optional[float] = None
    ):
        self.generation = generation
        self.active_segment_ids = active_segment_ids or []
        self.tombstones: Set[int] = tombstones or set()
        self.segment_checksums = segment_checksums or {}
        self.total_live_docs = total_live_docs
        self.published_at = published_at or time.time()
        self.manifest_hash = self.compute_hash()

    def compute_hash(self) -> str:
        payload = {
            "generation": self.generation,
            "segments": sorted(self.active_segment_ids),
            "tombstones": sorted(list(self.tombstones)),
            "checksums": self.segment_checksums,
            "total_live_docs": self.total_live_docs
        }
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "active_segment_ids": self.active_segment_ids,
            "tombstones": list(self.tombstones),
            "segment_checksums": self.segment_checksums,
            "total_live_docs": self.total_live_docs,
            "published_at": self.published_at,
            "manifest_hash": self.manifest_hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Manifest":
        m = cls(
            generation=data["generation"],
            active_segment_ids=data.get("active_segment_ids", []),
            tombstones=set(data.get("tombstones", [])),
            segment_checksums=data.get("segment_checksums", {}),
            total_live_docs=data.get("total_live_docs", 0),
            published_at=data.get("published_at", time.time())
        )
        m.manifest_hash = data.get("manifest_hash", m.compute_hash())
        return m


class ManifestManager:
    """
    Coordinates atomic publication, version rollback, and validation.
    """
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.manifests_dir = os.path.join(base_dir, "manifests")
        self.current_manifest_path = os.path.join(self.manifests_dir, "current_manifest.json")
        os.makedirs(self.manifests_dir, exist_ok=True)
        
        self.history: List[Manifest] = []
        self.current_manifest = self._load_or_create_initial()

    def _load_or_create_initial(self) -> Manifest:
        if os.path.exists(self.current_manifest_path):
            try:
                with open(self.current_manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                manifest = Manifest.from_dict(data)
                self.history.append(manifest)
                return manifest
            except Exception:
                pass
        
        initial = Manifest(generation=1)
        self._write_manifest_file(initial, self.current_manifest_path)
        self.history.append(initial)
        return initial

    def _write_manifest_file(self, manifest: Manifest, target_path: str) -> None:
        temp_path = f"{target_path}.tmp.{manifest.generation}.{int(time.time()*1000)}"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)
        
        # Atomic replace
        os.replace(temp_path, target_path)

    def validate_manifest(self, manifest: Manifest, segments_map: Dict[str, Any]) -> None:
        """
        Validates manifest invariants before atomic publication:
        1. All referenced segments exist and match their registered checksums.
        2. Generation is strictly increasing.
        3. No negative live doc counts.
        """
        if manifest.generation <= self.current_manifest.generation:
            raise ManifestValidationError(
                f"New generation {manifest.generation} must be greater than current {self.current_manifest.generation}"
            )
            
        for seg_id in manifest.active_segment_ids:
            if seg_id not in segments_map:
                raise ManifestValidationError(f"Segment {seg_id} listed in manifest but not found in storage")
            seg = segments_map[seg_id]
            expected_checksum = manifest.segment_checksums.get(seg_id)
            if expected_checksum and seg.checksum != expected_checksum:
                raise ManifestValidationError(
                    f"Checksum mismatch for segment {seg_id}. Expected {expected_checksum}, found {seg.checksum}"
                )

        if manifest.total_live_docs < 0:
            raise ManifestValidationError(f"Invalid negative live doc count: {manifest.total_live_docs}")

    def publish_new_version(
        self,
        active_segment_ids: List[str],
        tombstones: Set[int],
        segment_checksums: Dict[str, str],
        total_live_docs: int,
        segments_map: Dict[str, Any]
    ) -> Manifest:
        """
        Creates and atomically publishes a new manifest generation.
        """
        next_gen = self.current_manifest.generation + 1
        new_manifest = Manifest(
            generation=next_gen,
            active_segment_ids=active_segment_ids,
            tombstones=tombstones,
            segment_checksums=segment_checksums,
            total_live_docs=total_live_docs
        )

        # 1. Validate
        self.validate_manifest(new_manifest, segments_map)

        # 2. Archive previous generation
        gen_archive_path = os.path.join(self.manifests_dir, f"manifest_gen_{new_manifest.generation}.json")
        self._write_manifest_file(new_manifest, gen_archive_path)

        # 3. Atomically update current_manifest.json
        self._write_manifest_file(new_manifest, self.current_manifest_path)

        # 4. Update memory pointer
        self.current_manifest = new_manifest
        self.history.append(new_manifest)
        return new_manifest

    def rollback(self) -> Optional[Manifest]:
        """
        Rolls back current manifest to the previous generation if available.
        """
        if len(self.history) <= 1:
            return None
        
        self.history.pop()  # Remove current
        previous = self.history[-1]
        
        self._write_manifest_file(previous, self.current_manifest_path)
        self.current_manifest = previous
        return previous
