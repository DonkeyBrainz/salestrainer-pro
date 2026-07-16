"""Personas API endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.personas import PERSONAS, PERSONAS_BY_DIFFICULTY
from app.agents.state import CustomerPersona, Difficulty

router = APIRouter(prefix="/api/v1/personas")


class PersonaResponse(BaseModel):
    """Persona data for frontend display."""

    id: str
    name: str
    backstory: str
    looking_for: str
    difficulty: str
    property_id: str | None = None
    objections: list[str] = []


class EvaluationPersonaResponse(BaseModel):
    """Persona data for evaluation mode - hides identifying information."""

    id: str
    backstory: str
    difficulty: str


class PersonaListResponse(BaseModel):
    """List of personas."""

    personas: list[PersonaResponse]


class EvaluationPersonaListResponse(BaseModel):
    """List of personas for evaluation mode."""

    personas: list[EvaluationPersonaResponse]


def _persona_to_response(persona: CustomerPersona) -> PersonaResponse:
    """Convert CustomerPersona to API response.

    LOW_REGARD personas withhold their matched property: the trainee must
    discover the buyer's needs through CORE and recommend a property
    themselves, rather than being told upfront which one to pitch.
    """
    reveals_property = persona.difficulty != Difficulty.LOW_REGARD
    return PersonaResponse(
        id=persona.id,
        name=persona.name,
        backstory=persona.backstory,
        looking_for=persona.looking_for,
        difficulty=persona.difficulty.value,
        property_id=persona.property_id if reveals_property else None,
        objections=persona.objections,
    )


def _persona_to_evaluation_response(persona: CustomerPersona) -> EvaluationPersonaResponse:
    """Convert CustomerPersona to evaluation API response (hides name and looking_for)."""
    return EvaluationPersonaResponse(
        id=persona.id,
        backstory=persona.backstory,
        difficulty=persona.difficulty.value,
    )


@router.get("", response_model=PersonaListResponse)
async def list_personas() -> PersonaListResponse:
    """List all available personas for training mode.

    Returns personas that are not evaluation-only.
    """
    training_personas = [p for p in PERSONAS.values() if not p.is_evaluation_only]
    personas = [_persona_to_response(p) for p in training_personas]
    return PersonaListResponse(personas=personas)


@router.get("/evaluation", response_model=EvaluationPersonaListResponse)
async def list_evaluation_personas() -> EvaluationPersonaListResponse:
    """List personas available for evaluation mode.

    Returns only medium and low regard personas that are evaluation-only.
    Names and looking_for info are hidden to avoid giving unfair information.
    """
    medium = PERSONAS_BY_DIFFICULTY.get(Difficulty.MEDIUM_REGARD, [])
    low = PERSONAS_BY_DIFFICULTY.get(Difficulty.LOW_REGARD, [])
    eval_personas = [p for p in medium + low if p.is_evaluation_only]
    personas = [_persona_to_evaluation_response(p) for p in eval_personas]
    return EvaluationPersonaListResponse(personas=personas)
