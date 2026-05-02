"""Service wrapper for customer agent interactions.

This module provides a service layer around the CustomerAgentGraph,
managing session initialization and message processing for roleplay sessions.
"""

import json
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.agents.customer_agent import CustomerAgentGraph
from app.agents.personas import get_persona
from app.agents.state import (
    CoreStageProgress,
    CustomerAgentState,
    CustomerPersona,
    Mood,
    RegardLevel,
)
from app.config import Settings
from app.models.session import Session
from app.models.transcript import MessageRole, Transcript


class CustomerAgentService:
    """Service for managing customer agent sessions.

    This service handles:
    - Session initialization with persona selection
    - Message processing through the agent graph
    - State retrieval for resuming sessions
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the service.

        Args:
            settings: Application settings with Gemini configuration.
        """
        self.settings = settings
        self.agent = CustomerAgentGraph(settings)

    async def start_session(
        self,
        session_id: str,
        user_id: str,
        persona_id: str,
    ) -> CustomerAgentState:
        """Start a new roleplay session with a customer persona.

        Args:
            session_id: Unique session identifier.
            user_id: User ID of the salesperson.
            persona_id: ID of the customer persona to use.

        Returns:
            Initial agent state.

        Raises:
            ValueError: If persona_id is not found.
        """
        persona = get_persona(persona_id)
        if not persona:
            raise ValueError(f"Persona '{persona_id}' not found")

        # Determine initial mood from persona's regard level
        initial_mood = self._initial_mood_from_regard(persona.initial_regard.value)

        # Initialize state from persona
        initial_state: CustomerAgentState = {
            "messages": [],
            "turn_count": 0,
            "persona": persona,
            "mood": initial_mood,
            "regard_level": persona.initial_regard,
            "objections_available": list(persona.objections),
            "objections_raised": [],
            "objections_resolved": [],
            "stage_progress": CoreStageProgress.model_construct(),
            "session_id": session_id,
            "user_id": user_id,
        }

        return initial_state

    async def process_message(
        self,
        session_id: str,
        user_message: str,
        current_state: CustomerAgentState,
    ) -> tuple[str, CustomerAgentState]:
        """Process a salesperson message and get customer response.

        Args:
            session_id: Session identifier (used as thread_id for checkpointing).
            user_message: The salesperson's message.
            current_state: Current agent state.

        Returns:
            Tuple of (customer_response, updated_state).
        """
        # Add user message to state
        updated_state: CustomerAgentState = {
            **current_state,
            "messages": list(current_state["messages"]) + [HumanMessage(content=user_message)],
        }

        # Invoke the graph
        result_state = await self.agent.invoke(updated_state, thread_id=session_id)

        # Extract response from last message
        last_message = result_state["messages"][-1]
        response_text = ""
        if isinstance(last_message, AIMessage):
            content = last_message.content
            response_text = content if isinstance(content, str) else str(content)

        return response_text, result_state

    async def get_session_state(self, session_id: str) -> CustomerAgentState | None:
        """Retrieve the current state for a session.

        Args:
            session_id: Session identifier.

        Returns:
            Current state or None if not found.
        """
        return self.agent.get_state(session_id)

    def _initial_mood_from_regard(self, regard: str) -> Mood:
        """Determine initial mood based on persona's regard level.

        Args:
            regard: Regard level value ("high", "low", "no").

        Returns:
            Corresponding initial mood.
        """
        mood_map = {
            "high": Mood.INTERESTED,
            "medium": Mood.NEUTRAL,
            "low": Mood.NEUTRAL,
            "no": Mood.SKEPTICAL,
        }
        return mood_map.get(regard, Mood.NEUTRAL)

    def serialize_state(self, state: CustomerAgentState) -> str:
        """Serialize agent state to JSON for persistence.

        Converts the agent state to a JSON string that can be stored in Firestore.
        Excludes non-serializable fields (messages, persona).

        Args:
            state: Current agent state.

        Returns:
            JSON string representation of the state.
        """
        # Extract serializable fields
        serializable: dict[str, Any] = {
            "turn_count": state.get("turn_count", 0),
            "mood": state.get("mood").value if state.get("mood") else None,
            "regard_level": (
                state.get("regard_level").value if state.get("regard_level") else None
            ),
            "objections_available": state.get("objections_available", []),
            "objections_raised": state.get("objections_raised", []),
            "objections_resolved": state.get("objections_resolved", []),
            "session_id": state.get("session_id"),
            "user_id": state.get("user_id"),
        }

        # Serialize stage_progress if present
        stage_progress = state.get("stage_progress")
        if stage_progress:
            serializable["stage_progress"] = stage_progress.model_dump()

        return json.dumps(serializable)

    def deserialize_state(
        self,
        snapshot_json: str,
        persona: CustomerPersona,
        messages: list[BaseMessage],
    ) -> CustomerAgentState:
        """Deserialize agent state from JSON snapshot.

        Reconstructs the full CustomerAgentState from a serialized snapshot,
        persona, and message history.

        Args:
            snapshot_json: JSON string from agent_state_snapshot.
            persona: The customer persona for this session.
            messages: Reconstructed message history.

        Returns:
            Restored CustomerAgentState.
        """
        data = json.loads(snapshot_json)

        # Reconstruct stage_progress
        stage_data = data.get("stage_progress", {})
        stage_progress = (
            CoreStageProgress.model_validate(stage_data)
            if stage_data
            else CoreStageProgress.model_construct()
        )

        # Reconstruct enums
        mood = Mood(data["mood"]) if data.get("mood") else Mood.NEUTRAL
        regard_level = (
            RegardLevel(data["regard_level"])
            if data.get("regard_level")
            else persona.initial_regard
        )

        state: CustomerAgentState = {
            "messages": messages,
            "turn_count": data.get("turn_count", 0),
            "persona": persona,
            "mood": mood,
            "regard_level": regard_level,
            "objections_available": data.get("objections_available", []),
            "objections_raised": data.get("objections_raised", []),
            "objections_resolved": data.get("objections_resolved", []),
            "stage_progress": stage_progress,
            "session_id": data.get("session_id", ""),
            "user_id": data.get("user_id", ""),
        }

        return state

    def resume_session(
        self,
        session: Session,
        transcript: Transcript | None = None,
    ) -> CustomerAgentState:
        """Resume a session from persisted state.

        Reconstructs the full CustomerAgentState from a saved session
        and optional transcript.

        Args:
            session: Session object with agent_state_snapshot and selected_persona.
            transcript: Optional transcript with message history.

        Returns:
            Restored CustomerAgentState ready for continued interaction.

        Raises:
            ValueError: If persona not found or snapshot missing.
        """
        if not session.selected_persona:
            raise ValueError("Session has no selected_persona")

        persona = get_persona(session.selected_persona)
        if not persona:
            raise ValueError(f"Persona '{session.selected_persona}' not found")

        # Reconstruct messages from transcript
        messages: list[BaseMessage] = []
        if transcript:
            for msg in transcript.messages:
                if msg.role == MessageRole.USER:
                    messages.append(HumanMessage(content=msg.text))
                elif msg.role == MessageRole.ASSISTANT:
                    messages.append(AIMessage(content=msg.text))

        # If no snapshot, create fresh state with restored messages
        if not session.agent_state_snapshot:
            initial_mood = self._initial_mood_from_regard(persona.initial_regard.value)
            return {
                "messages": messages,
                "turn_count": len([m for m in messages if isinstance(m, HumanMessage)]),
                "persona": persona,
                "mood": initial_mood,
                "regard_level": persona.initial_regard,
                "objections_available": list(persona.objections),
                "objections_raised": [],
                "objections_resolved": [],
                "stage_progress": CoreStageProgress.model_construct(),
                "session_id": session.session_id,
                "user_id": session.user_id,
            }

        # Deserialize from snapshot
        return self.deserialize_state(
            snapshot_json=session.agent_state_snapshot,
            persona=persona,
            messages=messages,
        )
