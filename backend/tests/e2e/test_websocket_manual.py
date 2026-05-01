#!/usr/bin/env python3
"""Manual WebSocket test script for E2E voice session testing.

This script tests the full voice roleplay pipeline with actual Gemini Live API.
Requires valid JWT token and running backend server.

Usage:
    # Basic text session test
    python tests/e2e/test_websocket_manual.py --token <JWT_TOKEN>

    # With specific persona
    python tests/e2e/test_websocket_manual.py --token <JWT_TOKEN> --persona demanding_professional

    # Interactive mode (read from stdin)
    python tests/e2e/test_websocket_manual.py --token <JWT_TOKEN> --interactive

    # Save audio responses to WAV file
    python tests/e2e/test_websocket_manual.py --token <JWT_TOKEN> --save-audio

    # Custom server URL
    python tests/e2e/test_websocket_manual.py --token <JWT_TOKEN> --url ws://localhost:8000

Environment:
    E2E_JWT_TOKEN: JWT token (alternative to --token flag)
    E2E_SERVER_URL: WebSocket server URL (default: ws://localhost:8000)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Try to import websockets, provide helpful error if not available
try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("Error: websockets package not found.")
    print("Install with: uv add websockets --dev")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# Available personas for reference
PERSONAS = [
    "eager_newlywed",  # Easy - friendly, open
    "busy_parent",  # Medium - pressed for time, guarded
    "skeptical_shopper",  # Medium - price-conscious, distrustful
    "demanding_professional",  # Hard - high standards, impatient
    "price_resistant",  # Hard - tight budget, defensive
]


class WebSocketTester:
    """Test client for WebSocket voice session testing."""

    # Gemini Live audio format: PCM 24kHz mono 16-bit
    AUDIO_SAMPLE_RATE = 24000
    AUDIO_CHANNELS = 1
    AUDIO_SAMPLE_WIDTH = 2  # 16-bit = 2 bytes

    def __init__(
        self,
        token: str,
        persona_id: str = "eager_newlywed",
        base_url: str = "ws://localhost:8000",
        save_audio: bool = False,
        audio_output_dir: str = ".",
        mode: str = "training",
    ) -> None:
        """Initialize WebSocket tester.

        Args:
            token: JWT access token
            persona_id: Customer persona ID
            base_url: WebSocket server base URL
            save_audio: Whether to save audio responses to WAV files
            audio_output_dir: Directory to save audio files
            mode: Session mode ('training' or 'evaluation')
        """
        self.token = token
        self.persona_id = persona_id
        self.base_url = base_url
        self.save_audio = save_audio
        self.audio_output_dir = Path(audio_output_dir)
        self.mode = mode
        self.ws: Any = None
        self.connected = False
        self.turn_count = 0
        self.messages: list[dict[str, Any]] = []
        self.coach_hints: list[dict[str, Any]] = []  # Store coach hints
        self.audio_buffer: bytearray = bytearray()  # Collect all audio bytes

    @property
    def url(self) -> str:
        """Build full WebSocket URL with query parameters."""
        return f"{self.base_url}/ws/gemini/live?token={self.token}&persona_id={self.persona_id}&mode={self.mode}"

    async def connect(self) -> bool:
        """Establish WebSocket connection.

        Returns:
            True if connection successful and ready message received.
        """
        logger.info(f"Connecting to {self.base_url}/ws/gemini/live...")
        logger.info(f"Persona: {self.persona_id}")

        try:
            self.ws = await websockets.connect(self.url)
            logger.info("WebSocket connection established")

            # Wait for ready message
            msg = await asyncio.wait_for(self.ws.recv(), timeout=10)
            data = json.loads(msg)

            if data.get("type") == "ready":
                logger.info(f"Ready message received: {data}")
                self.connected = True
                return True
            else:
                logger.error(f"Unexpected initial message: {data}")
                return False

        except TimeoutError:
            logger.error("Timeout waiting for ready message")
            return False
        except ConnectionClosed as e:
            logger.error(f"Connection closed: code={e.code}, reason={e.reason}")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def send_text(self, content: str) -> None:
        """Send text message to server.

        Args:
            content: Text content to send
        """
        if not self.ws:
            logger.error("Not connected")
            return

        message = {"type": "text", "content": content}
        await self.ws.send(json.dumps(message))
        logger.info(f">>> Sent: {content}")
        self.messages.append(
            {
                "role": "user",
                "content": content,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    async def receive_responses(self, timeout: float = 15.0) -> list[dict[str, Any]]:
        """Receive all responses until turn complete or timeout.

        Args:
            timeout: Maximum time to wait for responses

        Returns:
            List of received messages
        """
        if not self.ws:
            logger.error("Not connected")
            return []

        responses: list[dict[str, Any]] = []
        turn_complete = False

        try:
            while not turn_complete:
                msg = await asyncio.wait_for(self.ws.recv(), timeout=timeout)

                if isinstance(msg, bytes):
                    # Audio data - collect for WAV saving
                    logger.info(f"<<< Audio: {len(msg)} bytes")
                    responses.append({"type": "audio", "bytes": len(msg)})
                    if self.save_audio:
                        self.audio_buffer.extend(msg)
                else:
                    # JSON message
                    data = json.loads(msg)
                    msg_type = data.get("type")

                    if msg_type == "transcription":
                        text = data.get("text", "")
                        logger.info(f"<<< Response: {text}")
                        responses.append({"type": "text", "content": text})
                        self.messages.append(
                            {
                                "role": "assistant",
                                "content": text,
                                "timestamp": datetime.now(UTC).isoformat(),
                            }
                        )

                    elif msg_type == "turn_complete":
                        logger.info("<<< Turn complete")
                        turn_complete = True
                        self.turn_count += 1

                    elif msg_type == "coach_hint":
                        # Coach hint message (Training mode only)
                        level = data.get("level", "unknown")
                        hint = data.get("hint", "")
                        stage = data.get("stage", "")
                        logger.info(f"<<< Coach [{level.upper()}] ({stage}): {hint}")
                        responses.append(data)
                        self.coach_hints.append(data)

                    elif msg_type == "error":
                        logger.error(f"<<< Error: {data}")
                        responses.append(data)
                        break

                    else:
                        logger.debug(f"<<< Other: {data}")
                        responses.append(data)

        except TimeoutError:
            logger.warning(f"Response timeout after {timeout}s")
        except ConnectionClosed as e:
            logger.error(f"Connection closed during receive: code={e.code}")

        return responses

    async def send_and_receive(self, content: str, timeout: float = 15.0) -> list[dict[str, Any]]:
        """Send text and receive responses.

        Args:
            content: Text to send
            timeout: Response timeout

        Returns:
            List of responses
        """
        await self.send_text(content)
        return await self.receive_responses(timeout)

    async def close(self) -> None:
        """Close WebSocket connection gracefully."""
        if self.ws:
            await self.ws.close()
            logger.info("Connection closed")
            self.connected = False

        # Save audio if enabled and we have data
        if self.save_audio and self.audio_buffer:
            self.save_audio_to_wav()

    def save_audio_to_wav(self, filename: str | None = None) -> Path | None:
        """Save collected audio buffer to WAV file.

        Args:
            filename: Optional filename (default: auto-generated with timestamp)

        Returns:
            Path to saved WAV file, or None if no audio data
        """
        if not self.audio_buffer:
            logger.warning("No audio data to save")
            return None

        # Generate filename with timestamp
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gemini_response_{self.persona_id}_{timestamp}.wav"

        # Ensure output directory exists
        self.audio_output_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.audio_output_dir / filename

        # Write WAV file with proper headers
        with wave.open(str(filepath), "wb") as wav_file:
            wav_file.setnchannels(self.AUDIO_CHANNELS)
            wav_file.setsampwidth(self.AUDIO_SAMPLE_WIDTH)
            wav_file.setframerate(self.AUDIO_SAMPLE_RATE)
            wav_file.writeframes(bytes(self.audio_buffer))

        duration_sec = len(self.audio_buffer) / (
            self.AUDIO_SAMPLE_RATE * self.AUDIO_CHANNELS * self.AUDIO_SAMPLE_WIDTH
        )
        logger.info(
            f"Saved audio: {filepath} ({duration_sec:.2f}s, {len(self.audio_buffer)} bytes)"
        )

        return filepath

    def print_summary(self) -> None:
        """Print session summary."""
        print("\n" + "=" * 60)
        print("SESSION SUMMARY")
        print("=" * 60)
        print(f"Persona: {self.persona_id}")
        print(f"Mode: {self.mode}")
        print(f"Turns: {self.turn_count}")
        print(f"Total messages: {len(self.messages)}")
        print(f"Coach hints received: {len(self.coach_hints)}")
        if self.audio_buffer:
            duration_sec = len(self.audio_buffer) / (
                self.AUDIO_SAMPLE_RATE * self.AUDIO_CHANNELS * self.AUDIO_SAMPLE_WIDTH
            )
            print(f"Audio collected: {len(self.audio_buffer)} bytes ({duration_sec:.2f}s)")

        if self.coach_hints:
            print("\nCoach Hints:")
            print("-" * 40)
            for hint in self.coach_hints:
                level = hint.get("level", "").upper()
                stage = hint.get("stage", "")
                text = hint.get("hint", "")
                completed = hint.get("items_completed", [])
                remaining = hint.get("items_remaining", [])
                print(f"  [{level}] {stage}: {text}")
                if completed:
                    print(f"    Completed: {', '.join(completed)}")
                if remaining:
                    print(f"    Remaining: {', '.join(remaining)}")

        print("\nConversation:")
        print("-" * 40)
        for msg in self.messages:
            role = msg["role"].upper()
            content = msg["content"]
            print(f"[{role}] {content}")
        print("=" * 60)


async def run_basic_test(tester: WebSocketTester) -> bool:
    """Run basic connectivity test with single exchange.

    Args:
        tester: WebSocket tester instance

    Returns:
        True if test passed
    """
    logger.info("=== Basic Connectivity Test ===")

    if not await tester.connect():
        logger.error("FAILED: Could not connect")
        return False

    try:
        responses = await tester.send_and_receive("Hi!, my name is Michael. Welcome in...")

        if not responses:
            logger.error("FAILED: No responses received")
            return False

        # Check if we got text response
        text_responses = [r for r in responses if r.get("type") == "text"]
        if not text_responses:
            logger.warning("No text response (may be audio-only)")

        logger.info("PASSED: Basic test completed")
        return True

    finally:
        await tester.close()


async def run_multi_turn_test(tester: WebSocketTester) -> bool:
    """Run multi-turn conversation test.

    Args:
        tester: WebSocket tester instance

    Returns:
        True if test passed
    """
    logger.info("=== Multi-Turn Conversation Test ===")

    if not await tester.connect():
        logger.error("FAILED: Could not connect")
        return False

    try:
        # Turn 1: Initial greeting
        await tester.send_and_receive("Hello! I'm looking for a sofa.")

        # Turn 2: Follow-up
        await tester.send_and_receive("What do you have in leather?")

        # Turn 3: Price inquiry
        await tester.send_and_receive("What's your budget range for quality leather sofas?")

        if tester.turn_count >= 3:
            logger.info("PASSED: Multi-turn test completed")
            return True
        else:
            logger.error(f"FAILED: Only {tester.turn_count} turns completed")
            return False

    finally:
        tester.print_summary()
        await tester.close()


async def run_persona_difficulty_test(
    token: str,
    persona_id: str,
    base_url: str,
    save_audio: bool = False,
    audio_dir: str = "./audio_output",
    mode: str = "training",
) -> bool:
    """Test persona-specific difficulty behaviors.

    Args:
        token: JWT token
        persona_id: Persona to test
        base_url: Server URL
        save_audio: Whether to save audio responses
        audio_dir: Directory to save audio files
        mode: Session mode ('training' or 'evaluation')

    Returns:
        True if test passed
    """
    logger.info(f"=== Persona Difficulty Test: {persona_id} (mode={mode}) ===")

    tester = WebSocketTester(token, persona_id, base_url, save_audio, audio_dir, mode)

    if not await tester.connect():
        logger.error("FAILED: Could not connect")
        return False

    try:
        # Test conversation that might trigger objections
        test_messages = [
            "Hi there! I'm here to help you find exactly what you need.",
            "I notice you're looking at our premium collection. Great choice!",
            "We have a special promotion today - 15% off if you decide now.",
        ]

        for msg in test_messages:
            responses = await tester.send_and_receive(msg, timeout=20.0)

            # Log response content for manual verification
            for resp in responses:
                if resp.get("type") == "text":
                    content = resp.get("content", "")
                    # Check for objection keywords
                    objection_keywords = [
                        "browsing",
                        "think about",
                        "not sure",
                        "husband",
                        "wife",
                        "partner",
                        "budget",
                        "expensive",
                        "cheaper",
                        "manager",
                        "discount",
                        "online",
                    ]
                    found = [kw for kw in objection_keywords if kw.lower() in content.lower()]
                    if found:
                        logger.info(f"Potential objection detected: {found}")

        logger.info("PASSED: Persona test completed (verify responses manually)")
        return True

    finally:
        tester.print_summary()
        await tester.close()


async def run_interactive_session(tester: WebSocketTester) -> None:
    """Run interactive session reading from stdin.

    Args:
        tester: WebSocket tester instance
    """
    logger.info("=== Interactive Session ===")
    logger.info("Type messages and press Enter. Type 'quit' to exit.")

    if not await tester.connect():
        logger.error("Could not connect")
        return

    try:
        while True:
            try:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ("quit", "exit", "q"):
                    break
                if not user_input:
                    continue

                await tester.send_and_receive(user_input, timeout=30.0)

            except EOFError:
                break
            except KeyboardInterrupt:
                print("\nInterrupted")
                break

    finally:
        tester.print_summary()
        await tester.close()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="E2E WebSocket test script for voice session testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available personas:
  {", ".join(PERSONAS)}

Examples:
  # Basic test with token
  python %(prog)s --token eyJ...

  # Test specific persona
  python %(prog)s --token eyJ... --persona demanding_professional

  # Interactive mode
  python %(prog)s --token eyJ... --interactive

  # Multi-turn test
  python %(prog)s --token eyJ... --test multi-turn
""",
    )

    parser.add_argument(
        "--token",
        "-t",
        default=os.environ.get("E2E_JWT_TOKEN"),
        help="JWT access token (or set E2E_JWT_TOKEN env var)",
    )
    parser.add_argument(
        "--persona",
        "-p",
        default="eager_newlywed",
        choices=PERSONAS,
        help="Customer persona ID (default: eager_newlywed)",
    )
    parser.add_argument(
        "--url",
        "-u",
        default=os.environ.get("E2E_SERVER_URL", "ws://localhost:8000"),
        help="WebSocket server URL (default: ws://localhost:8000)",
    )
    parser.add_argument(
        "--test",
        choices=["basic", "multi-turn", "persona", "all"],
        default="basic",
        help="Test type to run (default: basic)",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--save-audio",
        "-a",
        action="store_true",
        help="Save audio responses to WAV file",
    )
    parser.add_argument(
        "--audio-dir",
        default="./audio_output",
        help="Directory to save audio files (default: ./audio_output)",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["training", "evaluation"],
        default="training",
        help="Session mode: training (with hints) or evaluation (silent)",
    )

    return parser.parse_args()


async def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.token:
        print("Error: JWT token required")
        print("Provide via --token flag or E2E_JWT_TOKEN environment variable")
        print("\nTo get a token:")
        print("  1. Start backend: uv run uvicorn app.main:app --reload")
        print("  2. Navigate to http://localhost:8000/auth/login")
        print("  3. Complete OAuth flow")
        print("  4. Extract JWT from response")
        return 1

    logger.info(f"Server URL: {args.url}")
    logger.info(f"Persona: {args.persona}")
    logger.info(f"Mode: {args.mode}")

    if args.interactive:
        tester = WebSocketTester(
            args.token, args.persona, args.url, args.save_audio, args.audio_dir, args.mode
        )
        await run_interactive_session(tester)
        return 0

    success = True

    if args.test in ("basic", "all"):
        tester = WebSocketTester(
            args.token, args.persona, args.url, args.save_audio, args.audio_dir, args.mode
        )
        if not await run_basic_test(tester):
            success = False

    if args.test in ("multi-turn", "all"):
        tester = WebSocketTester(
            args.token, args.persona, args.url, args.save_audio, args.audio_dir, args.mode
        )
        if not await run_multi_turn_test(tester):
            success = False

    if args.test in ("persona", "all"):
        for persona_id in PERSONAS:
            if not await run_persona_difficulty_test(
                args.token, persona_id, args.url, args.save_audio, args.audio_dir, args.mode
            ):
                success = False

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
