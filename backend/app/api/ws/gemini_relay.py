"""WebSocket relay for Gemini Live API."""

import asyncio
import hashlib
import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from langfuse import get_client, propagate_attributes

from app.agents.personas import get_persona
from app.agents.prompts import build_live_system_instruction
from app.agents.state import CustomerAgentState, CustomerPersona
from app.api.products import get_product_details
from app.core.exceptions import (
    InternalError,
    InvalidRequestError,
    RateLimitError,
    ServiceUnavailableError,
    TokenExpiredError,
    UnauthorizedError,
)
from app.llm_providers.streaming import LLMStreamProvider
from app.llm_providers.voices import resolve_voice
from app.models.session import Difficulty, SessionCreate, SessionHint, SessionStatus, SessionType
from app.models.transcript import MessageRole, TranscriptMessage
from app.services.auth_service import AuthService
from app.services.coach_agent_service import CoachAgentService
from app.services.customer_agent_service import CustomerAgentService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

# Training sessions never send an explicit "evaluate" control (only assessment
# mode does), so a disconnect is their only natural end signal. A session with
# at least this many messages is real practice, not an abandoned false start.
MIN_MESSAGES_FOR_TRAINING_COMPLETION = 4


class GeminiWebSocketRelay:
    """Relay WebSocket connections to Gemini Live API."""

    def __init__(
        self,
        live_provider: LLMStreamProvider,
        auth_service: AuthService,
        session_service: SessionService,
        customer_agent_service: CustomerAgentService,
        coach_agent_service: CoachAgentService,
        enable_resumption: bool = True,
    ) -> None:
        """Initialize WebSocket relay.

        Args:
            live_provider: Speech-to-speech provider for Live API connections
                (Gemini / OpenAI Realtime / Nova Sonic).
            auth_service: Auth service for token validation
            session_service: Session service for persistence
            customer_agent_service: Customer agent service for persona state
            coach_agent_service: Coach agent service for analysis and hints
            enable_resumption: Enable session resumption (Gemini-only; other
                providers never emit resumption signals and reconnect fresh)
        """
        self.live_provider = live_provider
        self.provider_name = live_provider.name
        self.auth_service = auth_service
        self.session_service = session_service
        self.customer_agent_service = customer_agent_service
        self.coach_agent_service = coach_agent_service
        self._message_buffer: list[TranscriptMessage] = []
        self._session_id: str | None = None
        self._agent_state: CustomerAgentState | None = None
        # Final persona for this session (post product-metadata injection);
        # kept so the system instruction can be rebuilt on reconnect.
        self._persona: CustomerPersona | None = None
        self._session_mode: SessionType = SessionType.TRAINING
        self._pending_reasoning: str | None = None  # Hold reasoning until speech arrives
        # Accumulate transcription chunks for consolidated Firestore storage
        self._pending_user_transcription: str = ""
        self._pending_assistant_transcription: str = ""
        # Session resumption state
        self._enable_resumption: bool = enable_resumption
        self._resumption_handle: str | None = None
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 3
        self._should_reconnect: bool = False
        # Track if conversation ended naturally (user requested evaluation)
        self._conversation_ended_naturally: bool = False
        # Coach hint throttling and quota management
        self._last_hint_time: float = 0.0
        self._min_hint_interval: float = 10.0  # 10 seconds minimum between hints
        self._coach_quota_exhausted: bool = False
        self._analysis_cache: dict[str, tuple[Any, Any, Any]] = {}  # Cache analysis results
        # Log of hints actually sent to the client, for the archive's hints-used
        # timeline. One relay instance lives for exactly one WS connection, so
        # wall-clock-since-init is a fine proxy for "time since session start".
        self._session_started_at: datetime = datetime.now(UTC)
        self._hint_log: list[SessionHint] = []

    async def handle_connection(
        self,
        websocket: WebSocket,
        token: str,
        persona_id: str,
        session_mode: SessionType = SessionType.TRAINING,
        product_category: str | None = None,
        product_type: str | None = None,
    ) -> None:
        """Handle WebSocket connection and relay to Gemini Live API.

        Flow:
        1. Validate JWT token
        2. Validate persona_id
        3. Accept WebSocket connection
        4. Initialize customer agent with persona
        5. Connect to Gemini Live API with system instruction
        6. Relay messages bidirectionally
        7. Analyze salesperson messages with coach agent
        8. Send coaching hints (Training mode only)
        9. Handle errors and disconnects

        Args:
            websocket: FastAPI WebSocket connection
            token: JWT access token from query parameter
            persona_id: Customer persona ID for roleplay
            session_mode: Training (with hints) or Evaluation (silent)

        Raises:
            WebSocket closes with appropriate code on errors
        """
        self._session_mode = session_mode
        # Validate JWT token
        try:
            payload = self.auth_service.decode_token(token)
            user_id = payload.sub
            if not user_id:
                logger.warning("Token missing 'sub' claim")
                await websocket.close(code=4001, reason="Invalid token")
                return
        except (TokenExpiredError, UnauthorizedError) as e:
            logger.warning(f"Token validation failed: {e}")
            await websocket.close(code=4001, reason="Invalid token")
            return
        except Exception as e:
            logger.error(f"Unexpected error validating token: {e}")
            await websocket.close(code=4001, reason="Invalid token")
            return

        # Validate persona_id
        persona = get_persona(persona_id)
        if not persona:
            logger.warning(f"Invalid persona_id: {persona_id}")
            await websocket.close(code=4004, reason="Invalid persona")
            return

        # Inject product metadata into persona if product params provided
        if product_category:
            category, ptype = get_product_details(product_category, product_type)
            if category:
                update: dict[str, str | None] = {
                    "product_category": product_category,
                    "product_type": product_type,
                }
                if ptype:
                    update["looking_for"] = f"{ptype.name} - {ptype.description}"
                else:
                    update["looking_for"] = category.description
                persona = persona.model_copy(update=update)
                logger.info(
                    "Injected product metadata into persona",
                    extra={
                        "persona_id": persona_id,
                        "product_category": product_category,
                        "product_type": product_type,
                    },
                )
            else:
                logger.warning(
                    f"Invalid product_category '{product_category}', using persona defaults"
                )

        # Accept WebSocket connection
        await websocket.accept()

        logger.info(
            "WebSocket connected",
            extra={
                "user_id": user_id,
                "persona_id": persona_id,
                "endpoint": "ws/gemini/live",
            },
        )

        # Create session in Firestore. Fired as a background task rather than
        # awaited here so the write overlaps with the Gemini Live handshake below
        # instead of stacking in front of it - resolved in _run_with_reconnection
        # right after the (slower) Gemini connection completes.
        session_create = SessionCreate(
            user_id=user_id,
            session_type=session_mode,
            difficulty=Difficulty(persona.difficulty),
            selected_persona=persona_id,
            product_category=persona.product_category,
            product_type=persona.product_type,
        )
        session_task = asyncio.create_task(self.session_service.start_session(session_create))

        # Initialize customer agent with persona
        try:
            self._agent_state = await self.customer_agent_service.start_session(
                session_id=self._session_id or "unknown",
                user_id=user_id,
                persona_id=persona_id,
            )
            logger.info(f"Initialized agent with persona {persona_id}")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}", exc_info=True)
            # Continue anyway - agent initialization failure shouldn't block WebSocket

        # Build system instruction from persona and agent state
        self._persona = persona
        system_instruction = self._current_system_instruction()

        # Connect to Gemini Live API with reconnection support
        try:
            await self._run_with_reconnection(
                websocket=websocket,
                user_id=user_id,
                system_instruction=system_instruction,
                voice_name=resolve_voice(persona, self.provider_name),
                session_task=session_task,
            )

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected by client (user_id={user_id})")

        except InvalidRequestError as e:
            logger.error(f"Invalid request to Gemini Live: {e}")
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "INVALID_REQUEST",
                    "message": str(e),
                }
            )
            await websocket.close(code=4004, reason="Invalid request")

        except ServiceUnavailableError as e:
            logger.error(f"Gemini Live API unavailable: {e}")
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Gemini service temporarily unavailable",
                }
            )
            await websocket.close(code=4005, reason="Service unavailable")

        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded (user_id={user_id})")
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "RATE_LIMITED",
                    "message": str(e),
                }
            )
            await websocket.close(code=4003, reason="Rate limit exceeded")

        except Exception as e:
            logger.exception(f"Unexpected WebSocket error: {e}")
            try:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "INTERNAL_ERROR",
                        "message": "Unexpected error occurred",
                    }
                )
                await websocket.close(code=1011, reason="Internal error")
            except Exception:
                # WebSocket might already be closed
                pass

        finally:
            # Resolve the session-create task if a Gemini connection failure (or
            # other error) happened before _run_with_reconnection reached it, so
            # the background write isn't left unawaited.
            if not session_task.done():
                try:
                    session = await session_task
                    self._session_id = self._session_id or session.session_id
                except Exception as e:
                    logger.error(f"Failed to create session: {e}", exc_info=True)

            # Persist conversation
            if self._session_id and self._message_buffer:
                try:
                    await self._persist_conversation(user_id)
                except Exception as e:
                    logger.error(f"Failed to persist conversation: {e}", exc_info=True)

            logger.info(f"WebSocket connection closed (user_id={user_id})")

    async def _run_with_reconnection(
        self,
        websocket: WebSocket,
        user_id: str,
        system_instruction: str | None,
        voice_name: str | None = None,
        session_task: "asyncio.Task[Any] | None" = None,
    ) -> None:
        """Run relay loop with automatic reconnection on Gemini disconnect.

        When Gemini sends a GoAway message or disconnects unexpectedly, this method
        will attempt to reconnect using the stored resumption handle (if available).
        The frontend WebSocket stays connected - only the backend-to-Gemini
        connection reconnects transparently.

        Args:
            websocket: Client WebSocket connection
            user_id: User ID for logging
            system_instruction: System instruction for Gemini session
            voice_name: Optional Gemini voice identifier
            session_task: Pending Firestore session-create task, if any. Resolved
                here (after the Gemini handshake) so the write overlaps with the
                handshake instead of blocking it.

        Raises:
            WebSocketDisconnect: When client disconnects
            InvalidRequestError: If Gemini request is invalid
            ServiceUnavailableError: If Gemini is unavailable after retries
            RateLimitError: If rate limited
        """
        while self._reconnect_attempts < self._max_reconnect_attempts:
            self._should_reconnect = False

            # On reconnect, rebuild the prompt so it reflects the customer's
            # current mood/regard/objection state instead of the connect-time
            # snapshot. With a resumption handle Gemini also restores server-side
            # context; the fresh prompt is the only accurate option when
            # reconnecting without one.
            if self._reconnect_attempts > 0:
                rebuilt = self._current_system_instruction()
                if rebuilt is not None:
                    system_instruction = rebuilt
                    logger.info(
                        "Rebuilt system instruction on reconnect",
                        extra={"session_id": self._session_id},
                    )

            try:
                # Only pass resumption handle if resumption is enabled
                resumption_handle = self._resumption_handle if self._enable_resumption else None
                async with self.live_provider.connect_live(
                    system_instruction=system_instruction,
                    voice=voice_name,
                    resumption_handle=resumption_handle,
                ) as live_session:
                    # Reset attempts on successful connect
                    self._reconnect_attempts = 0

                    # Resolve the Firestore session-create task. By now the Gemini
                    # handshake above has already given the event loop time to run
                    # it, so this normally returns immediately.
                    if session_task is not None and self._session_id is None:
                        try:
                            session = await session_task
                            self._session_id = session.session_id
                            if self._agent_state:
                                self._agent_state["session_id"] = session.session_id
                            logger.info(f"Created session {session.session_id} for user {user_id}")
                        except Exception as e:
                            logger.error(f"Failed to create session: {e}", exc_info=True)
                            # Continue anyway - session creation failure shouldn't block the relay

                    # Notify client of connection status
                    if resumption_handle:
                        logger.info(
                            f"Resumed Gemini session (user_id={user_id})",
                            extra={"session_id": self._session_id},
                        )
                        await websocket.send_json({"type": "session_resumed"})
                    else:
                        logger.info(
                            f"Started fresh Gemini session (user_id={user_id}, resumption={'disabled' if not self._enable_resumption else 'enabled but no handle'})",
                            extra={"session_id": self._session_id},
                        )
                        await websocket.send_json({"type": "ready", "status": "connected"})

                    # Run relay tasks
                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(
                            self._relay_client_to_gemini(websocket, live_session, user_id)
                        )
                        tg.create_task(
                            self._relay_gemini_to_client(websocket, live_session, user_id)
                        )

            except WebSocketDisconnect:
                # Client disconnected - propagate up, no reconnection needed
                raise

            except (InternalError, BaseExceptionGroup) as e:
                # Handle connection errors - may be wrapped InternalError or raw ExceptionGroup
                # Check if any exception is a client disconnect
                if isinstance(e, BaseExceptionGroup):
                    for exc in e.exceptions:
                        if isinstance(exc, WebSocketDisconnect):
                            raise WebSocketDisconnect() from exc

                # Check if we should attempt reconnection (have handle or got GoAway)
                if self._should_reconnect or self._resumption_handle:
                    self._reconnect_attempts += 1
                    if self._reconnect_attempts < self._max_reconnect_attempts:
                        logger.info(
                            f"Reconnecting to Gemini (attempt {self._reconnect_attempts})",
                            extra={
                                "user_id": user_id,
                                "session_id": self._session_id,
                                "has_handle": self._resumption_handle is not None,
                            },
                        )
                        try:
                            await websocket.send_json({"type": "reconnecting"})
                        except Exception:
                            # Client may have disconnected
                            raise WebSocketDisconnect() from e
                        await asyncio.sleep(0.5)  # Brief delay before retry
                        continue

                # Log error and re-raise if not reconnecting
                logger.error(
                    "Gemini connection error (not reconnecting)",
                    extra={
                        "session_id": self._session_id,
                        "user_id": user_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "has_handle": self._resumption_handle is not None,
                        "should_reconnect": self._should_reconnect,
                    },
                )
                raise

            # Normal exit (tasks completed without error)
            break

    async def _relay_client_to_gemini(
        self,
        websocket: WebSocket,
        live_session: Any,
        user_id: str,
    ) -> None:
        """Relay messages from client to Gemini.

        Args:
            websocket: Client WebSocket connection
            live_session: Gemini Live API session
            user_id: User ID for logging

        Raises:
            WebSocketDisconnect: When client disconnects
            InternalError: On relay errors
        """
        try:
            while True:
                # Receive message from client with timeout (30 minutes)
                try:
                    message = await asyncio.wait_for(
                        websocket.receive(),
                        timeout=1800.0,  # 30 minutes
                    )
                except TimeoutError:
                    logger.warning(f"WebSocket timeout for user {user_id}")
                    await websocket.close(code=1000, reason="Timeout")
                    return

                # Check for disconnect
                if message.get("type") == "websocket.disconnect":
                    logger.debug(f"Client sent disconnect message (user_id={user_id})")
                    raise WebSocketDisconnect()

                # Handle different message types
                if "bytes" in message:
                    # Binary audio data
                    audio_data = message["bytes"]
                    await live_session.send_audio(audio_data)
                    logger.debug(f"Relayed {len(audio_data)} bytes to Gemini (user_id={user_id})")

                elif "text" in message:
                    # JSON text message
                    import json

                    try:
                        data = json.loads(message["text"])
                        msg_type = data.get("type")

                        if msg_type == "text":
                            # Text input
                            content = data.get("content", "")
                            await live_session.send_text(content)
                            # Buffer user message
                            self._buffer_message(
                                role=MessageRole.USER,
                                text=content,
                                timestamp=datetime.now(UTC),
                            )
                            # Update agent state + coach analysis (non-blocking)
                            await self._process_agents(
                                salesperson_message=content,
                                websocket=websocket,
                                user_id=user_id,
                            )

                        elif msg_type == "control":
                            # Control messages (e.g., end_turn, evaluate)
                            action = data.get("action")
                            logger.debug(f"Control action: {action} (user_id={user_id})")

                            if action == "evaluate":
                                # Flush pending transcriptions
                                if self._pending_user_transcription:
                                    self._buffer_message(
                                        role=MessageRole.USER,
                                        text=self._pending_user_transcription.strip(),
                                        timestamp=datetime.now(UTC),
                                    )
                                    self._pending_user_transcription = ""
                                if self._pending_assistant_transcription:
                                    self._buffer_message_with_reasoning(
                                        role=MessageRole.ASSISTANT,
                                        text=self._pending_assistant_transcription.strip(),
                                        internal_reasoning=self._pending_reasoning,
                                        timestamp=datetime.now(UTC),
                                    )
                                    self._pending_assistant_transcription = ""
                                    self._pending_reasoning = None

                                # Mark as naturally ended before persisting
                                self._conversation_ended_naturally = True

                                # Persist conversation before evaluation
                                if self._session_id and self._message_buffer:
                                    await self._persist_conversation(user_id)

                                # Generate and send evaluation
                                await self._generate_and_send_evaluation(
                                    user_id=user_id,
                                    websocket=websocket,
                                )

                                # Clear buffer to prevent double-persist in finally
                                self._message_buffer.clear()

                                # Close and disconnect
                                await websocket.close(code=1000, reason="Evaluation complete")
                                raise WebSocketDisconnect()

                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON from client (user_id={user_id}): {e}")
                        await websocket.send_json(
                            {
                                "type": "error",
                                "code": "INVALID_MESSAGE",
                                "message": "Invalid message format",
                            }
                        )

        except WebSocketDisconnect:
            logger.debug(f"Client disconnected while relaying to Gemini (user_id={user_id})")
            raise

        except Exception as e:
            logger.exception(f"Error relaying client to Gemini: {e}")
            raise InternalError(f"Relay error: {str(e)}") from e

    async def _relay_gemini_to_client(
        self,
        websocket: WebSocket,
        live_session: Any,
        user_id: str,
    ) -> None:
        """Relay messages from Gemini to client.

        Handles the following message types from Gemini:
        - audio: Binary audio response, relayed to client
        - internal_reasoning: Model's internal text (stored, not sent to client)
        - input_transcription: User's speech transcription (analyzed + buffered)
        - output_transcription: Model's speech transcription (buffered with reasoning)
        - end: Turn complete signal

        Args:
            websocket: Client WebSocket connection
            live_session: Gemini Live API session
            user_id: User ID for logging

        Raises:
            InternalError: On relay errors
        """
        try:
            async for response in live_session.receive():
                resp_type = response["type"]

                # Session resumption update - store handle for reconnection (if enabled)
                if resp_type == "session_resumption_update":
                    new_handle = response.get("new_handle")
                    if new_handle and self._enable_resumption:
                        self._resumption_handle = new_handle
                        logger.debug(
                            "Stored resumption handle",
                            extra={"user_id": user_id, "resumable": response.get("resumable")},
                        )
                    elif new_handle and not self._enable_resumption:
                        logger.debug(
                            "Ignoring resumption handle (resumption disabled)",
                            extra={"user_id": user_id},
                        )
                    continue

                # GoAway - server is requesting disconnect, prepare for reconnection
                if resp_type == "go_away":
                    time_left = response.get("time_left")
                    logger.info(
                        f"GoAway received, time_left={time_left}",
                        extra={"user_id": user_id, "session_id": self._session_id},
                    )
                    self._should_reconnect = True
                    continue

                # Audio - relay to client
                if resp_type == "audio" and response["audio_data"]:
                    await websocket.send_bytes(response["audio_data"])
                    logger.debug(
                        f"Relayed {len(response['audio_data'])} bytes to client (user_id={user_id})"
                    )

                # Internal reasoning (from model_turn.parts[].text)
                elif resp_type == "internal_reasoning" and response["text"]:
                    # Store reasoning, don't buffer yet - wait for output_transcription
                    self._pending_reasoning = response["text"]
                    logger.debug(f"Received internal reasoning (user_id={user_id})")

                # Input transcription (salesperson's speech)
                elif resp_type == "input_transcription" and response["text"]:
                    chunk = response["text"]

                    # Accumulate for consolidated Firestore storage
                    self._pending_user_transcription += chunk

                    # Stream to client for real-time display
                    await websocket.send_json(
                        {
                            "type": "user_transcription",
                            "text": chunk,
                        }
                    )

                # Output transcription (customer agent's speech)
                elif resp_type == "output_transcription" and response["text"]:
                    chunk = response["text"]

                    # Accumulate for consolidated Firestore storage
                    self._pending_assistant_transcription += chunk

                    # Stream to client for real-time display
                    await websocket.send_json(
                        {
                            "type": "transcription",
                            "text": chunk,
                        }
                    )

                # Turn complete - flush accumulated transcriptions
                elif resp_type == "end":
                    # Flush user transcription
                    if self._pending_user_transcription:
                        user_text = self._pending_user_transcription.strip()
                        self._buffer_message(
                            role=MessageRole.USER,
                            text=user_text,
                            timestamp=datetime.now(UTC),
                        )

                        # Run agent state update + coach analysis on complete message
                        await self._process_agents(
                            salesperson_message=user_text,
                            websocket=websocket,
                            user_id=user_id,
                        )

                        self._pending_user_transcription = ""

                    # Flush assistant transcription
                    if self._pending_assistant_transcription:
                        self._buffer_message_with_reasoning(
                            role=MessageRole.ASSISTANT,
                            text=self._pending_assistant_transcription.strip(),
                            internal_reasoning=self._pending_reasoning,
                            timestamp=datetime.now(UTC),
                        )
                        self._pending_assistant_transcription = ""
                        self._pending_reasoning = None

                    await websocket.send_json({"type": "turn_complete"})

        except WebSocketDisconnect:
            logger.debug(f"Client disconnected while relaying from Gemini (user_id={user_id})")
            raise

        except Exception as e:
            logger.exception(f"Error relaying Gemini to client: {e}")
            raise InternalError(f"Relay error: {str(e)}") from e

    def _buffer_message(self, role: MessageRole, text: str, timestamp: datetime) -> None:
        """Buffer message for later persistence."""
        message = TranscriptMessage(
            message_id=str(uuid4()),
            role=role,
            text=text,
            timestamp=timestamp,
        )
        self._message_buffer.append(message)

    def _buffer_message_with_reasoning(
        self,
        role: MessageRole,
        text: str,
        timestamp: datetime,
        internal_reasoning: str | None = None,
    ) -> None:
        """Buffer message with optional internal reasoning."""
        message = TranscriptMessage(
            message_id=str(uuid4()),
            role=role,
            text=text,
            timestamp=timestamp,
            internal_reasoning=internal_reasoning,
        )
        self._message_buffer.append(message)

    def _current_system_instruction(self) -> str | None:
        """Build the persona system instruction from the current agent state.

        Used at connect time and again on each reconnect so the prompt reflects
        live mood/regard/objection state rather than the connect-time snapshot.
        """
        if not (self._persona and self._agent_state):
            return None
        return build_live_system_instruction(
            persona=self._persona, state=self._agent_state, provider_name=self.provider_name
        )

    async def _process_agents(
        self,
        salesperson_message: str,
        websocket: WebSocket,
        user_id: str,
    ) -> None:
        """Run customer-agent state update and coach analysis for a completed turn.

        Each agent gets its own exception scope: a customer-agent failure must not
        prevent coach analysis (and vice versa). Both degrade non-fatally while the
        voice session continues.

        Wraps both agents in a Langfuse span so every Gemini generation this turn
        produces (persona response, coach analysis) is grouped under one session
        in the Langfuse UI.

        Args:
            salesperson_message: The salesperson's completed message
            websocket: WebSocket connection for sending coach events
            user_id: Salesperson's user ID, for Langfuse session grouping
        """
        if not (self._agent_state and self._session_id):
            return

        langfuse = get_client()
        with (
            langfuse.start_as_current_observation(as_type="span", name="sales-training-turn"),
            propagate_attributes(
                session_id=self._session_id,
                user_id=user_id,
                tags=[self.provider_name, self._session_mode.value],
            ),
        ):
            await self._run_agents(salesperson_message, websocket)

    async def _run_agents(
        self,
        salesperson_message: str,
        websocket: WebSocket,
    ) -> None:
        """Body of ``_process_agents``, run inside its Langfuse span."""
        assert self._agent_state and self._session_id
        try:
            # Preserve coach-maintained stage_progress across
            # LangGraph invocation (graph doesn't manage this field)
            preserved_progress = self._agent_state["stage_progress"]
            (
                _,
                self._agent_state,
            ) = await self.customer_agent_service.process_message(
                session_id=self._session_id,
                user_message=salesperson_message,
                current_state=self._agent_state,
                generate_response=False,
            )
            self._agent_state["stage_progress"] = preserved_progress
            logger.debug(
                f"Agent state updated: mood={self._agent_state.get('mood')}, "
                f"regard={self._agent_state.get('regard_level')}"
            )
            await self._send_mood_update(websocket)
        except Exception as e:
            logger.warning(f"Customer agent processing failed: {e}", exc_info=True)

        try:
            await self._analyze_and_send_hint(
                salesperson_message=salesperson_message,
                websocket=websocket,
            )
        except Exception as e:
            logger.warning(f"Coach analysis failed: {e}", exc_info=True)

    async def _send_mood_update(self, websocket: WebSocket) -> None:
        """Push the customer's current mood/regard to the client.

        Sent on every turn (unlike hints, which are throttled) so the mood HUD
        tracks the same state the persona prompt is rebuilt from.
        """
        if not self._agent_state:
            return

        mood = self._agent_state.get("mood")
        regard = self._agent_state.get("regard_level")
        if mood is None or regard is None:
            return

        await websocket.send_json(
            {
                "type": "mood_update",
                "mood": mood.value,
                "regard_level": regard.value,
            }
        )
        logger.debug(
            "Sent mood update",
            extra={
                "session_id": self._session_id,
                "mood": mood.value,
                "regard_level": regard.value,
            },
        )

    async def _analyze_and_send_hint(
        self,
        salesperson_message: str,
        websocket: WebSocket,
    ) -> None:
        """Analyze salesperson message with coach agent and send hint if needed.

        Only sends hints in Training mode and when intervention is non-NONE.
        Implements throttling (10s minimum), caching, and graceful quota handling.

        Args:
            salesperson_message: The salesperson's message to analyze
            websocket: WebSocket connection for sending hints
        """
        if not self._agent_state:
            return

        # Check if quota is exhausted - skip analysis but keep session alive
        if self._coach_quota_exhausted:
            logger.debug(
                "Skipping coach analysis - quota exhausted",
                extra={"session_id": self._session_id},
            )
            return

        # Throttling: Enforce 10-second minimum between hints
        current_time = time.time()
        time_since_last_hint = current_time - self._last_hint_time
        if time_since_last_hint < self._min_hint_interval:
            logger.debug(
                "Skipping coach analysis - throttled",
                extra={
                    "session_id": self._session_id,
                    "time_since_last_hint": f"{time_since_last_hint:.1f}s",
                    "min_interval": f"{self._min_hint_interval}s",
                },
            )
            return

        # Check cache using stage-scoped message hash. Keying on stage prevents
        # replaying a stale analysis/progress from an earlier C.O.R.E. stage
        # (turn_count is deliberately excluded — it would defeat the cache).
        current_stage = self._agent_state["stage_progress"].current_stage.value
        message_hash = hashlib.sha256(
            f"{current_stage}|{salesperson_message}".encode()
        ).hexdigest()[:16]
        if message_hash in self._analysis_cache:
            logger.debug(
                "Using cached analysis",
                extra={"session_id": self._session_id, "cache_key": message_hash},
            )
            analysis, updated_progress, hint = self._analysis_cache[message_hash]
        else:
            # Show "analyzing" message to user
            try:
                await websocket.send_json(
                    {
                        "type": "coach_status",
                        "status": "analyzing",
                        "message": "Coach analyzing, please wait...",
                    }
                )
            except Exception:
                # Client may have disconnected, but continue analysis
                pass

            try:
                logger.debug(
                    "Starting coach analysis",
                    extra={
                        "session_id": self._session_id,
                        "message_length": len(salesperson_message),
                        "session_mode": self._session_mode.value,
                    },
                )

                # Run coach analysis
                analysis, updated_progress, hint = await self.coach_agent_service.analyze_turn(
                    salesperson_message=salesperson_message,
                    state=self._agent_state,
                    session_mode=self._session_mode,
                )

                # Cache successful analysis
                self._analysis_cache[message_hash] = (analysis, updated_progress, hint)

                # Limit cache size to prevent memory issues
                if len(self._analysis_cache) > 50:
                    # Remove oldest entry (first key)
                    first_key = next(iter(self._analysis_cache))
                    del self._analysis_cache[first_key]

                logger.info(
                    "Coach analysis complete",
                    extra={
                        "session_id": self._session_id,
                        "intervention_level": analysis.intervention_level.value,
                        "techniques_detected": analysis.techniques_detected,
                        "stage_items_completed": [
                            {"stage": s.stage, "item": s.item}
                            for s in analysis.stage_items_completed
                        ],
                        "has_hint": hint is not None,
                        "updated_connect": updated_progress.connect,
                        "updated_observe": updated_progress.observe,
                        "updated_recommend": updated_progress.recommend,
                        "updated_execute": updated_progress.execute,
                    },
                )

            except RateLimitError as e:
                # Graceful 429 handling - disable coach hints but keep Gemini Live alive
                logger.warning(
                    "Coach quota exhausted - disabling hints for this session",
                    extra={
                        "session_id": self._session_id,
                        "error": str(e),
                    },
                )
                self._coach_quota_exhausted = True

                # Notify user that coach hints are temporarily unavailable
                try:
                    await websocket.send_json(
                        {
                            "type": "coach_status",
                            "status": "quota_exhausted",
                            "message": "Coach hints temporarily unavailable due to high demand. Your session will continue.",
                        }
                    )
                except Exception:
                    pass
                return

            except Exception as e:
                # Other analysis failures should not crash WebSocket
                logger.warning(
                    "Coach analysis failed",
                    extra={
                        "session_id": self._session_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                return

        # Update last hint time
        self._last_hint_time = current_time

        # Update agent state with new stage progress
        self._agent_state["stage_progress"] = updated_progress

        # Always send authoritative stage progress to the frontend
        all_completed: list[str] = []
        for stage_dict in [
            updated_progress.connect,
            updated_progress.observe,
            updated_progress.recommend,
            updated_progress.execute,
        ]:
            all_completed.extend(item for item, done in stage_dict.items() if done)

        await websocket.send_json(
            {
                "type": "stage_progress",
                "current_stage": updated_progress.current_stage.value,
                "all_completed_items": all_completed,
            }
        )

        # Send hint to client (Training mode only, handled by analyze_turn)
        if hint:
            await websocket.send_json(
                {
                    "type": "coach_hint",
                    "level": hint.level.value,
                    "hint": hint.hint,
                    "stage": hint.stage,
                    "example_phrase": hint.example_phrase,
                    "ready_for_next_stage": hint.ready_for_next_stage,
                }
            )
            elapsed = int((datetime.now(UTC) - self._session_started_at).total_seconds())
            self._hint_log.append(
                SessionHint(t=f"{elapsed // 60:02d}:{elapsed % 60:02d}", hint=hint.hint)
            )
            logger.info(
                "Sent coach hint",
                extra={
                    "session_id": self._session_id,
                    "level": hint.level.value,
                    "stage": hint.stage,
                },
            )

    async def _generate_and_send_evaluation(
        self,
        user_id: str,
        websocket: WebSocket,
    ) -> None:
        """Generate evaluation and send result to client via WebSocket.

        Args:
            user_id: User ID for evaluation
            websocket: WebSocket connection for sending result
        """
        if not self._agent_state or not self._session_id:
            await websocket.send_json(
                {
                    "type": "evaluation_error",
                    "message": "Session state unavailable for evaluation",
                }
            )
            return

        try:
            # Log stage_progress before evaluation for debugging
            sp = self._agent_state.get("stage_progress")
            if sp:
                logger.info(
                    "Stage progress at evaluation time",
                    extra={
                        "session_id": self._session_id,
                        "current_stage": sp.current_stage.value,
                        "connect": sp.connect,
                        "observe": sp.observe,
                        "recommend": sp.recommend,
                        "execute": sp.execute,
                    },
                )

            evaluation = await self.coach_agent_service.generate_evaluation(
                session_id=self._session_id,
                user_id=user_id,
                state=self._agent_state,
                session_mode=self._session_mode,
            )

            # Serialize scorecard stage_scores for JSON
            stage_scores_dict: dict[str, dict[str, object]] = {}
            for key, stage_score in evaluation.scorecard.stage_scores.items():
                stage_scores_dict[key] = {
                    "stage": stage_score.stage,
                    "items_completed": stage_score.items_completed,
                    "items_total": stage_score.items_total,
                    "score": stage_score.score,
                    "weight": stage_score.weight,
                    "feedback": stage_score.feedback,
                }

            await websocket.send_json(
                {
                    "type": "evaluation_result",
                    "evaluation": {
                        "evaluation_id": evaluation.evaluation_id,
                        "session_id": evaluation.session_id,
                        "scorecard": {
                            "stage_scores": stage_scores_dict,
                            "pbm_match_rate": evaluation.scorecard.pbm_match_rate,
                            "pbm_bonus": evaluation.scorecard.pbm_bonus,
                            "objection_resolution_rate": evaluation.scorecard.objection_resolution_rate,
                            "objection_penalty": evaluation.scorecard.objection_penalty,
                            "deviations": evaluation.scorecard.deviations,
                            "deviation_penalty": evaluation.scorecard.deviation_penalty,
                            "raw_score": evaluation.scorecard.raw_score,
                            "final_score": evaluation.scorecard.final_score,
                            "grade": evaluation.scorecard.grade.value,
                        },
                        "final_score": evaluation.final_score,
                        "grade": evaluation.grade.value,
                        "summary": evaluation.summary,
                        "strengths": evaluation.strengths,
                        "improvements": evaluation.improvements,
                        "techniques_detected": evaluation.techniques_detected,
                    },
                    # Subject identity is withheld during evaluation mode (see
                    # persona.py EvaluationPersonaResponse); grading is the
                    # "declassification" moment, so the real name ships here.
                    "persona_name": self._persona.name if self._persona else None,
                }
            )

            logger.info(
                f"Sent evaluation result for session {self._session_id}: "
                f"score={evaluation.final_score:.1f}, grade={evaluation.grade.value}"
            )

        except Exception as e:
            logger.error(
                f"Failed to generate evaluation: {e}",
                exc_info=True,
            )
            await websocket.send_json(
                {
                    "type": "evaluation_error",
                    "message": "Failed to generate evaluation",
                }
            )

    async def _persist_conversation(self, user_id: str) -> None:
        """Save session and transcript to Firestore."""
        if not self._session_id or not self._message_buffer:
            return

        # Serialize agent state if available
        agent_state_snapshot: str | None = None
        if self._agent_state:
            agent_state_snapshot = self.customer_agent_service.serialize_state(self._agent_state)

        # Determine session status based on how conversation ended.
        # Evaluation mode only ends "naturally" via the explicit evaluate
        # control; training mode has no such signal, so a disconnect with
        # enough real exchange still counts as a completed practice run.
        if self._conversation_ended_naturally:
            status = SessionStatus.COMPLETED
        elif (
            self._session_mode == SessionType.TRAINING
            and len(self._message_buffer) >= MIN_MESSAGES_FOR_TRAINING_COMPLETION
        ):
            status = SessionStatus.COMPLETED
        else:
            status = SessionStatus.ABANDONED

        # Delegate to SessionService
        await self.session_service.end_session(
            session_id=self._session_id,
            messages=self._message_buffer,
            status=status,
            agent_state_snapshot=agent_state_snapshot,
            hints_used=self._hint_log,
        )

        logger.info(
            f"Persisted session {self._session_id}: {len(self._message_buffer)} messages, "
            f"status={status.value}"
        )

        # Generate post-session evaluation if we have agent state
        if self._agent_state:
            try:
                evaluation = await self.coach_agent_service.generate_evaluation(
                    session_id=self._session_id,
                    user_id=user_id,
                    state=self._agent_state,
                    session_mode=self._session_mode,
                )
                await self.session_service.record_evaluation_result(
                    session_id=self._session_id,
                    grade=evaluation.scorecard.grade.value,
                    score=evaluation.scorecard.final_score,
                )
                logger.info(
                    f"Generated evaluation for session {self._session_id}: "
                    f"score={evaluation.scorecard.final_score:.1f}, grade={evaluation.scorecard.grade.value}"
                )
            except Exception as e:
                logger.warning(f"Failed to generate evaluation: {e}")
