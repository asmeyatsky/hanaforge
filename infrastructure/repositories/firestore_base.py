"""Firestore base — shared async client management for all Firestore repositories."""

from __future__ import annotations

from typing import Any

from google.cloud.firestore_v1 import AsyncClient


class FirestoreBase:
    """Base class providing a lazy-initialised Firestore async client.

    All Firestore repository implementations inherit from this to share
    a single client instance per repository object.
    """

    def __init__(self, project_id: str | None = None, database: str = "(default)") -> None:
        self._project_id = project_id
        self._database = database
        self._client: AsyncClient | None = None

    @property
    def client(self) -> AsyncClient:
        """Return the cached async Firestore client, creating it on first access."""
        if self._client is None:
            self._client = AsyncClient(
                project=self._project_id,
                database=self._database,
            )
        return self._client

    def _collection(self, path: str) -> Any:
        """Shorthand for client.collection(path)."""
        return self.client.collection(path)

    def _doc(self, collection_path: str, doc_id: str) -> Any:
        """Shorthand for client.collection(path).document(doc_id)."""
        return self.client.collection(collection_path).document(doc_id)
