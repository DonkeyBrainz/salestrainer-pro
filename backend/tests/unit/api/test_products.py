"""Unit tests for products API endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient) -> None:
    """Test listing all product collections."""
    response = await client.get("/api/v1/products")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "categories" in data
    categories = data["categories"]

    # Verify we have all 5 product collections
    category_ids = [cat["id"] for cat in categories]
    assert "bracken" in category_ids
    assert "calden" in category_ids
    assert "modero" in category_ids
    assert "neo" in category_ids
    assert "whitehaven" in category_ids

    # Verify structure of a collection
    bracken = next(c for c in categories if c["id"] == "bracken")
    assert "name" in bracken
    assert "description" in bracken
    assert "types" in bracken
    assert bracken["types"] == []  # Collection-based, no sub-types


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient) -> None:
    """Test listing category IDs only."""
    response = await client.get("/api/v1/products/categories")

    assert response.status_code == status.HTTP_200_OK
    category_ids = response.json()

    assert isinstance(category_ids, list)
    assert len(category_ids) == 5
    assert set(category_ids) == {"bracken", "calden", "modero", "neo", "whitehaven"}


@pytest.mark.asyncio
async def test_products_have_all_required_fields(client: AsyncClient) -> None:
    """Test that all product collections have required fields."""
    response = await client.get("/api/v1/products")
    data = response.json()

    for category in data["categories"]:
        assert category["id"], f"Category missing id: {category}"
        assert category["name"], f"Category missing name: {category}"
        assert category["description"], f"Category missing description: {category}"
        assert isinstance(category["types"], list), f"Category types not a list: {category}"


@pytest.mark.asyncio
async def test_collection_count(client: AsyncClient) -> None:
    """Test that we have exactly 5 collections."""
    response = await client.get("/api/v1/products")
    data = response.json()

    assert len(data["categories"]) == 5
