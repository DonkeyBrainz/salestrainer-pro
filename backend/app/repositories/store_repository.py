"""Store repository for Firestore persistence.

Stores are seeded once (see scratchpad seed script) and read-only from the
API's perspective for now -- no create/update/delete endpoints exist yet.
"""

from typing import Any

from app.models.store import Store
from app.repositories.base import BaseRepository


class StoreRepository(BaseRepository):
    """Repository for store data in Firestore."""

    _collection_name = "stores"

    async def get_by_id(self, store_id: str) -> Store | None:
        """Get store by store_id."""
        doc = await self.collection.document(store_id).get()
        if not doc.exists:
            return None
        return self._doc_to_store(doc.id, doc.to_dict())

    async def list_all(self) -> list[Store]:
        """List every store in the org."""
        docs = await self.collection.get()
        return [self._doc_to_store(doc.id, doc.to_dict()) for doc in docs]

    async def list_by_region(self, region: str) -> list[Store]:
        """List all stores in a given region."""
        query = self.collection.where("region", "==", region)
        docs = await query.get()
        return [self._doc_to_store(doc.id, doc.to_dict()) for doc in docs]

    def _doc_to_store(self, doc_id: str, data: dict[str, Any] | None) -> Store:
        """Convert Firestore document to Store model."""
        if data is None:
            raise ValueError("Document data is None")

        return Store(
            store_id=doc_id,
            name=data["name"],
            region=data["region"],
        )
