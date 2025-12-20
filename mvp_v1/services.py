from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class DocumentVault:
    """
    Simple in-memory document vault for managing secure file references.

    In production this would be backed by encrypted storage / object store.
    For now we focus on:
    - Passports
    - COEs
    - Educational transcripts
    """

    # Structure: candidate_id -> doc_type -> path
    _storage: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def store_document(self, candidate_id: str, doc_type: str, path: str) -> None:
        """
        Store or update a document path for a candidate.

        doc_type is expected to be one of:
        - "passport"
        - "coe"
        - "transcript"
        (but we keep it generic for future expansion).
        """
        if candidate_id not in self._storage:
            self._storage[candidate_id] = {}
        self._storage[candidate_id][doc_type] = path

    def get_document(self, candidate_id: str, doc_type: str) -> str | None:
        """Return the stored document path for a given candidate and type."""
        return self._storage.get(candidate_id, {}).get(doc_type)

    def has_all_core_documents(self, candidate_id: str) -> bool:
        """
        Check if a candidate has all core SOW-mandated documents:
        - passport
        - coe
        - at least one transcript
        """
        docs = self._storage.get(candidate_id, {})
        return bool(
            docs.get("passport")
            and docs.get("coe")
            and docs.get("transcript")
        )


