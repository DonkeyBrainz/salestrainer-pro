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

        # Should have 10 training personas (all real estate buyer archetypes)
        assert len(personas) == 10

        training_ids = {
            "optimistic_renovator",
            "anxious_first_timer",
            "practical_family",
            "urban_minimalist",
            "privacy_remote_worker",
            "scaling_investor",
            "wealthy_skeptic",
            "landlord_investor",
            "school_obsessed_parent",
            "lifestyle_retiree",
        }
        returned_ids = {p["id"] for p in personas}
        assert returned_ids == training_ids

    async def test_response_structure(self, client: AsyncClient) -> None:
        """Should return personas with correct structure."""
        response = await client.get("/api/v1/personas")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        persona = data["personas"][0]

        assert "id" in persona
        assert "name" in persona
        assert "backstory" in persona
        assert "looking_for" in persona
        assert "difficulty" in persona


class TestListEvaluationPersonasEndpoint:
    """Tests for GET /api/v1/personas/evaluation endpoint."""

    async def test_returns_only_eval_personas(self, client: AsyncClient) -> None:
        """Should return only evaluation-only personas (none currently defined)."""
        response = await client.get("/api/v1/personas/evaluation")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "personas" in data
        personas = data["personas"]

        # No eval-only personas defined; all 10 real estate personas are training personas
        assert len(personas) == 0

    async def test_hides_persona_details(self, client: AsyncClient) -> None:
        """Eval personas should not expose name or looking_for."""
        response = await client.get("/api/v1/personas/evaluation")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        personas = data["personas"]

        for persona in personas:
            assert "id" in persona
            assert "backstory" in persona
            assert "difficulty" in persona
            assert "name" not in persona
            assert "looking_for" not in persona
