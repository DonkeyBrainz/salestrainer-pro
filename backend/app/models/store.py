"""Store models for the org visibility hierarchy (store -> region -> national)."""

from pydantic import BaseModel


class Store(BaseModel):
    """A physical store location, grouped under a region."""

    store_id: str
    name: str  # "Houston", "Kinston"
    region: str  # "TX", "NC", "SC"
