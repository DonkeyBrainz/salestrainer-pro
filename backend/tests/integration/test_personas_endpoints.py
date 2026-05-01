"""Integration tests for Personas API endpoints."""

from fastapi import status
from httpx import AsyncClient


class TestListPersonasEndpoint:
    """Tests for GET /api/v1/personas endpoint."""

    async def test_returns_only_training_personas(self, client: AsyncClient) -> None:
        """Should return only non-evaluation personas for training mode."""
        response = await client.get("/api/v1/personas")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "personas" in data
        personas = data["personas"]

        # Should have 5 training personas
        assert len(personas) == 5

        # Verify all are training personas (not eval-only)
        training_ids = {
            "eager_newlywed",
            "busy_parent",
            "skeptical_shopper",
            "demanding_professional",
            "price_resistant",
        }
        returned_ids = {p["id"] for p in personas}
        assert returned_ids == training_ids

    async def test_response_structure(self, client: AsyncClient) -> None:
        """Should return personas with correct structure."""
        response = await client.get("/api/v1/personas")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        persona = data["personas"][0]

        # Check required fields
        assert "id" in persona
        assert "name" in persona
        assert "backstory" in persona
        assert "looking_for" in persona
        assert "difficulty" in persona


class TestListEvaluationPersonasEndpoint:
    """Tests for GET /api/v1/personas/evaluation endpoint."""

    async def test_returns_only_eval_personas(self, client: AsyncClient) -> None:
        """Should return only evaluation-only personas (medium and hard)."""
        response = await client.get("/api/v1/personas/evaluation")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "personas" in data
        personas = data["personas"]

        # Should have 6 eval-only personas
        assert len(personas) == 6

        # Verify all are eval-only personas
        eval_ids = {
            "tech_savvy_millennial",
            "empty_nester",
            "young_professional",
            "luxury_renovator",
            "frugal_retiree",
            "indecisive_couple_rep",
        }
        returned_ids = {p["id"] for p in personas}
        assert returned_ids == eval_ids

    async def test_only_medium_and_hard_difficulty(self, client: AsyncClient) -> None:
        """Should only return medium and low regard personas."""
        response = await client.get("/api/v1/personas/evaluation")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        personas = data["personas"]

        # Verify no high regard personas
        difficulties = {p["difficulty"] for p in personas}
        assert "high_regard" not in difficulties
        assert "medium_regard" in difficulties
        assert "low_regard" in difficulties

    async def test_hides_persona_details(self, client: AsyncClient) -> None:
        """Should not include name or looking_for to avoid giving unfair information."""
        response = await client.get("/api/v1/personas/evaluation")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        personas = data["personas"]

        for persona in personas:
            # Should have id, backstory, difficulty
            assert "id" in persona
            assert "backstory" in persona
            assert "difficulty" in persona

            # Should NOT have name or looking_for
            assert "name" not in persona
            assert "looking_for" not in persona
