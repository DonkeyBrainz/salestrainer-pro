"""Unit tests for objection lookup service."""

import pytest

from app.data.objections import ObjectionCategory
from app.services.objection_service import (
    ObjectionLookupService,
    get_objection_service,
    init_objection_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service() -> ObjectionLookupService:
    """Create an ObjectionLookupService instance."""
    return ObjectionLookupService()


# =============================================================================
# Detection Tests
# =============================================================================


class TestDetectObjection:
    """Tests for detect_objection method."""

    def test_detects_price_objection(self, service: ObjectionLookupService) -> None:
        """Should detect a price-related objection."""
        result = service.detect_objection("That's more than I wanted to spend.")

        assert result is not None
        assert result["category"] == ObjectionCategory.PRICE

    def test_detects_timing_objection(self, service: ObjectionLookupService) -> None:
        """Should detect a timing-related objection."""
        result = service.detect_objection("I need to think about it for a while.")

        assert result is not None
        assert result["category"] == ObjectionCategory.TIMING

    def test_detects_authority_objection(self, service: ObjectionLookupService) -> None:
        """Should detect an authority-related objection."""
        result = service.detect_objection("I need to talk to my spouse first.")

        assert result is not None
        assert result["category"] == ObjectionCategory.AUTHORITY

    def test_detects_competition_objection(self, service: ObjectionLookupService) -> None:
        """Should detect a competition-related objection."""
        result = service.detect_objection("I saw this cheaper at another store.")

        assert result is not None
        assert result["category"] == ObjectionCategory.COMPETITION

    def test_detects_trust_objection(self, service: ObjectionLookupService) -> None:
        """Should detect a trust-related objection."""
        result = service.detect_objection("I'm not sure about the quality of this.")

        assert result is not None
        assert result["category"] == ObjectionCategory.TRUST

    def test_detects_logistics_objection(self, service: ObjectionLookupService) -> None:
        """Should detect a logistics-related objection."""
        result = service.detect_objection("I need to measure my space first.")

        assert result is not None
        assert result["category"] == ObjectionCategory.LOGISTICS

    def test_no_match_for_unrelated_message(self, service: ObjectionLookupService) -> None:
        """Should return None for messages that aren't objections."""
        result = service.detect_objection("This sofa looks really comfortable!")

        assert result is None

    def test_case_insensitive(self, service: ObjectionLookupService) -> None:
        """Should match regardless of case."""
        result = service.detect_objection("I NEED TO THINK ABOUT IT.")

        assert result is not None
        assert result["category"] == ObjectionCategory.TIMING

    def test_empty_message(self, service: ObjectionLookupService) -> None:
        """Should return None for empty message."""
        result = service.detect_objection("")

        assert result is None

    def test_partial_match_below_threshold(self, service: ObjectionLookupService) -> None:
        """Should not match with too few overlapping keywords."""
        result = service.detect_objection("I have a question about the color options.")

        assert result is None


# =============================================================================
# Resolution Context Tests
# =============================================================================


class TestGetResolutionContext:
    """Tests for get_resolution_context method."""

    def test_formats_resolution_context(self, service: ObjectionLookupService) -> None:
        """Should format objection entry into resolution context string."""
        objection = service.detect_objection("That's more than I wanted to spend.")
        assert objection is not None

        context = service.get_resolution_context(objection)

        assert "price" in context.lower()
        assert objection["resolution_hint"] in context
        assert objection["difficulty"] in context

    def test_includes_category_and_difficulty(self, service: ObjectionLookupService) -> None:
        """Should include category and difficulty in output."""
        objection = service.detect_objection("I need to talk to my spouse first.")
        assert objection is not None

        context = service.get_resolution_context(objection)

        assert "authority" in context
        assert "firm" in context


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingleton:
    """Tests for module-level singleton management."""

    def test_get_raises_when_not_initialized(self) -> None:
        """Should raise RuntimeError when service not initialized."""
        import app.services.objection_service as module

        module._objection_service = None

        with pytest.raises(RuntimeError, match="Objection service not initialized"):
            get_objection_service()

    def test_init_and_get(self) -> None:
        """Should initialize and retrieve singleton."""
        import app.services.objection_service as module

        module._objection_service = None

        init_objection_service()
        service = get_objection_service()
        assert isinstance(service, ObjectionLookupService)

        # Cleanup
        module._objection_service = None
