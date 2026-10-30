"""
Index Manager
Coordinates multiple immutable index segments, concurrency, tombstones for updates/deletes,
segment compaction, and atomic manifest publishing.
"""

from typing import Dict, List, Set, Any, Optional, Tuple
import os
import time
import uuid
import threading
from core.tokenizer import Tokenizer
from core.index.segment import Segment
from core.index.manifest import ManifestManager, Manifest


class IndexManager:
    """
    Thread-safe, multi-segment index manager with atomic commits and background compaction.
    """
    def __init__(self, storage_dir: str, tokenizer: Optional[Tokenizer] = None):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        self.tokenizer = tokenizer or Tokenizer()
        self.manifest_manager = ManifestManager(storage_dir)
        
        # Segments currently loaded: segment_id -> Segment
        self.segments: Dict[str, Segment] = {}
        
        # In-flight writable segment
        self.active_writable_segment: Optional[Segment] = None
        self._new_writable_segment()
        
        # Lock for write operations (concurrent reads remain lock-free against immutable segments)
        self.write_lock = threading.Lock()
        
        # Live tombstones loaded from manifest
        self.tombstones: Set[int] = set(self.manifest_manager.current_manifest.tombstones)
        
        # Track doc_id mapping to primary segment
        self.doc_to_segment: Dict[int, str] = {}

    def _new_writable_segment(self) -> Segment:
        seg_id = f"seg_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
        seg = Segment(segment_id=seg_id, tokenizer=self.tokenizer)
        self.active_writable_segment = seg
        return seg

    def index_document(self, doc_id: int, title: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Indexes a document into the active writable segment.
        If document previously existed, old version is marked tombstone.
        """
        with self.write_lock:
            if doc_id in self.doc_to_segment:
                # Document update: mark existing as tombstoned
                self.tombstones.add(doc_id)
            
            # Remove from tombstones if re-adding
            self.tombstones.discard(doc_id)
            
            if self.active_writable_segment is None:
                self._new_writable_segment()
                
            self.active_writable_segment.add_document(doc_id, title, body, metadata)
            self.doc_to_segment[doc_id] = self.active_writable_segment.segment_id

    def delete_document(self, doc_id: int) -> bool:
        """Marks a document as deleted using a tombstone."""
        with self.write_lock:
            if doc_id in self.doc_to_segment and doc_id not in self.tombstones:
                self.tombstones.add(doc_id)
                return True
            return False

    def commit(self) -> Manifest:
        """
        Freezes the current writable segment and atomically publishes
        a new manifest generation with updated segment list and checksums.
        """
        with self.write_lock:
            if self.active_writable_segment is None or self.active_writable_segment.total_docs == 0:
                # Nothing new to commit, return current manifest
                return self.manifest_manager.current_manifest

            # 1. Freeze current writable segment
            frozen_seg = self.active_writable_segment
            frozen_seg.freeze()
            self.segments[frozen_seg.segment_id] = frozen_seg

            # 2. Prepare new manifest data
            active_segment_ids = [s for s in self.segments.keys() if s in self.manifest_manager.current_manifest.active_segment_ids]
            if frozen_seg.segment_id not in active_segment_ids:
                active_segment_ids.append(frozen_seg.segment_id)

            checksums = {seg_id: self.segments[seg_id].checksum for seg_id in active_segment_ids}
            
            # Calculate total live docs
            total_raw_docs = sum(self.segments[s].total_docs for s in active_segment_ids)
            live_docs = max(0, total_raw_docs - len(self.tombstones))

            # 3. Publish atomically
            new_manifest = self.manifest_manager.publish_new_version(
                active_segment_ids=active_segment_ids,
                tombstones=self.tombstones,
                segment_checksums=checksums,
                total_live_docs=live_docs,
                segments_map=self.segments
            )

            # 4. Open fresh writable segment for future writes
            self._new_writable_segment()
            return new_manifest

    def compact(self) -> Optional[Manifest]:
        """
        Merges all active immutable segments into a single consolidated segment,
        permanently purging tombstones and optimizing postings lists.
        """
        with self.write_lock:
            active_ids = self.manifest_manager.current_manifest.active_segment_ids
            if len(active_ids) <= 1 and not self.tombstones:
                return None  # Nothing to compact

            compact_id = f"compact_{int(time.time()*1000)}"
            compact_seg = Segment(segment_id=compact_id, tokenizer=self.tokenizer)

            for seg_id in active_ids:
                seg = self.segments.get(seg_id)
                if not seg:
                    continue
                for doc_id, doc_data in seg.documents.items():
                    if doc_id in self.tombstones:
                        continue  # Skip purged tombstones
                    meta = {k: v for k, v in doc_data.items() if k not in ("title", "body", "id")}
                    compact_seg.add_document(doc_id, doc_data["title"], doc_data["body"], meta)

            compact_seg.freeze()
            self.segments[compact_seg.segment_id] = compact_seg

            # Tombstones are now completely purged
            new_tombstones: Set[int] = set()
            new_checksums = {compact_seg.segment_id: compact_seg.checksum}
            
            # Update doc mapping
            for did in compact_seg.documents:
                self.doc_to_segment[did] = compact_seg.segment_id

            # Publish new manifest containing only the consolidated segment
            new_manifest = self.manifest_manager.publish_new_version(
                active_segment_ids=[compact_seg.segment_id],
                tombstones=new_tombstones,
                segment_checksums=new_checksums,
                total_live_docs=compact_seg.total_docs,
                segments_map=self.segments
            )
            
            # Clean up old segments from memory
            for old_id in active_ids:
                if old_id != compact_seg.segment_id and old_id in self.segments:
                    del self.segments[old_id]
                    
            self.tombstones = new_tombstones
            return new_manifest

    def rollback_manifest(self) -> Optional[Manifest]:
        """Rolls back to previous manifest generation."""
        with self.write_lock:
            rolled_back = self.manifest_manager.rollback()
            if rolled_back:
                self.tombstones = set(rolled_back.tombstones)
            return rolled_back

    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves document if not tombstoned."""
        if doc_id in self.tombstones:
            return None
        
        # Check active writable segment first
        if self.active_writable_segment and doc_id in self.active_writable_segment.documents:
            return self.active_writable_segment.documents[doc_id]

        # Check committed segments
        for seg_id in self.manifest_manager.current_manifest.active_segment_ids:
            seg = self.segments.get(seg_id)
            if seg and doc_id in seg.documents:
                return seg.documents[doc_id]
        return None

    def get_all_live_documents(self) -> Dict[int, Dict[str, Any]]:
        """Returns all documents not masked by tombstones."""
        all_docs: Dict[int, Dict[str, Any]] = {}
        for seg_id in self.manifest_manager.current_manifest.active_segment_ids:
            seg = self.segments.get(seg_id)
            if not seg:
                continue
            for doc_id, doc in seg.documents.items():
                if doc_id not in self.tombstones:
                    all_docs[doc_id] = doc
                    
        if self.active_writable_segment:
            for doc_id, doc in self.active_writable_segment.documents.items():
                if doc_id not in self.tombstones:
                    all_docs[doc_id] = doc
        return all_docs

    def get_statistics(self) -> Dict[str, Any]:
        """Returns engine index stats."""
        active_ids = self.manifest_manager.current_manifest.active_segment_ids
        total_indexed_docs = sum(self.segments[s].total_docs for s in active_ids if s in self.segments)
        return {
            "generation": self.manifest_manager.current_manifest.generation,
            "active_segments": len(active_ids),
            "total_live_docs": self.manifest_manager.current_manifest.total_live_docs,
            "tombstones_count": len(self.tombstones),
            "total_indexed_docs": total_indexed_docs,
            "manifest_hash": self.manifest_manager.current_manifest.manifest_hash,
            "history_depth": len(self.manifest_manager.history),
        }
