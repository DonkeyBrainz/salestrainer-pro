"""WebSocket endpoints for real-time communication."""

from fastapi import APIRouter, Depends, Query, WebSocket

from app.api.ws import GeminiWebSocketRelay
from app.core.dependencies import (
    get_auth_service,
    get_coach_agent_service,
    get_customer_agent_service,
    get_gemini_service,
    get_session_service,
)
from app.models.session import SessionType
from app.services.auth_service import AuthService
from app.services.coach_agent_service import CoachAgentService
from app.services.customer_agent_service import CustomerAgentService
from app.services.gemini_service import GeminiService
from app.services.session_service import SessionService

router = APIRouter()


@router.websocket("/ws/gemini/live")
async def websocket_gemini_relay(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    persona_id: str = Query("optimistic_renovator", description="Customer persona ID"),
    mode: str = Query("training", description="Session mode: training or evaluation"),
    product_category: str | None = Query(
        None, description="Product category ID (e.g., 'living_room', 'bedroom')"
    ),
    product_type: str | None = Query(
        None, description="Product type ID within category (e.g., 'sectional_1')"
    ),
    resume: bool = Query(
        True, description="Enable session resumption (set to false for fresh start)"
    ),
    gemini_service: GeminiService = Depends(get_gemini_service),
    auth_service: AuthService = Depends(get_auth_service),
    session_service: SessionService = Depends(get_session_service),
    customer_agent_service: CustomerAgentService = Depends(get_customer_agent_service),
    coach_agent_service: CoachAgentService = Depends(get_coach_agent_service),
) -> None:
    """WebSocket relay for Gemini Live API.

    Establishes a bidirectional WebSocket connection between the client and Gemini Live API.
    Supports real-time audio streaming for voice-based AI interactions.

    Args:
        websocket: WebSocket connection from client
        token: JWT access token for authentication
        gemini_service: Gemini service instance (injected)
        auth_service: Auth service instance (injected)

    Query Parameters:
        token (str): JWT access token obtained from /auth/callback
        persona_id (str): Customer persona ID (default: optimistic_renovator)
        mode (str): Session mode - "training" (real-time hints) or "evaluation" (silent)
        resume (bool): Enable session resumption (default: true, set to false for fresh start)

    Connection Flow:
        1. Client connects with valid JWT token
        2. Server validates token and accepts connection
        3. Server connects to Gemini Live API
        4. Bidirectional streaming begins (client <-> Gemini)
        5. Connection maintained until client disconnects or timeout (30 min)

    Message Types (Client -> Server):
        - Binary frames: Raw PCM audio data (16kHz mono recommended)
        - JSON text: {"type": "text", "content": "..."}
        - JSON text: {"type": "control", "action": "end_turn"}

    Message Types (Server -> Client):
        - Binary frames: PCM audio responses from Gemini
        - JSON: {"type": "ready", "status": "connected"}
        - JSON: {"type": "transcription", "text": "..."}
        - JSON: {"type": "turn_complete"}
        - JSON: {"type": "coach_hint", "level": "...", "hint": "...", "stage": "...",
                 "items_completed": [...], "items_remaining": [...]} (Training mode only)
        - JSON: {"type": "error", "code": "...", "message": "..."}

    Error Codes:
        - 4001: Authentication failed
        - 4002: Session limit exceeded
        - 4003: Rate limit exceeded
        - 4004: Invalid message format
        - 4005: Gemini connection failed
        - 1000: Timeout (30 minutes)
        - 1011: Internal server error

    Example (JavaScript):
        ```javascript
        const ws = new WebSocket(`ws://localhost:8000/ws/gemini/live?token=${accessToken}`);

        ws.onopen = () => {
            console.log('Connected');
        };

        ws.onmessage = (event) => {
            if (event.data instanceof Blob) {
                // Binary audio data
                playAudio(event.data);
            } else {
                // JSON message
                const msg = JSON.parse(event.data);
                console.log('Message:', msg);
            }
        };

        // Send audio
        ws.send(audioBytes);

        // Send text
        ws.send(JSON.stringify({ type: 'text', content: 'Hello' }));
        ```
    """
    # Parse session mode (default to training)
    session_mode = SessionType.TRAINING
    if mode.lower() == "evaluation":
        session_mode = SessionType.EVALUATION

    relay = GeminiWebSocketRelay(
        gemini_service,
        auth_service,
        session_service,
        customer_agent_service,
        coach_agent_service,
        enable_resumption=resume,
    )
    await relay.handle_connection(
        websocket, token, persona_id, session_mode, product_category, product_type
    )
