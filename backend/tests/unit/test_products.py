"""Unit tests for product catalog lookup helper."""

from app.api.products import get_product_details


class TestGetProductDetails:
    """Tests for get_product_details function."""

    def test_valid_collection(self) -> None:
        """Should return category for a valid collection ID."""
        category, ptype = get_product_details("bracken")

        assert category is not None
        assert category.id == "bracken"
        assert category.name == "Bracken"
        assert ptype is None

    def test_valid_collection_no_type(self) -> None:
        """Should return category with None type (collections have no sub-types)."""
        category, ptype = get_product_details("calden")

        assert category is not None
        assert category.id == "calden"
        assert ptype is None

    def test_invalid_category(self) -> None:
        """Should return (None, None) for unknown category."""
        category, ptype = get_product_details("nonexistent")

        assert category is None
        assert ptype is None

    def test_valid_category_invalid_type(self) -> None:
        """Should return category with None type when type not found."""
        category, ptype = get_product_details("modero", "nonexistent_type")

        assert category is not None
        assert category.id == "modero"
        assert ptype is None

    def test_all_collections_accessible(self) -> None:
        """Should find all defined collections."""
        for cat_id in ["bracken", "calden", "modero", "neo", "whitehaven"]:
            category, _ = get_product_details(cat_id)
            assert category is not None, f"Collection '{cat_id}' not found"
