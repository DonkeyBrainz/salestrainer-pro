#!/usr/bin/env python3
"""Test script to measure Gemini Live API idle timeout.

This script connects to Gemini Live API and does nothing (no audio, no text)
to determine how long the connection stays alive before being disconnected.

Usage:
    cd backend
    uv run python scripts/test_gemini_idle_timeout.py
"""

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.types import SessionResumptionConfig

# Load environment variables
load_dotenv()


def log(message: str) -> None:
    """Log message with timestamp."""
    timestamp = datetime.now(UTC).isoformat()
    print(f"[{timestamp}] {message}")


async def test_idle_timeout() -> None:
    """Connect to Gemini Live API and wait for disconnect."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log("ERROR: GEMINI_API_KEY not set in environment")
        return

    model = os.getenv("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")

    log("Initializing Gemini client...")
    log(f"Model: {model}")

    client = genai.Client(api_key=api_key)

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        session_resumption=SessionResumptionConfig(),  # Enable to receive resumption tokens
    )

    log("Connecting to Gemini Live API (session resumption ENABLED)...")
    start_time = datetime.now(UTC)

    try:
        async with client.aio.live.connect(
            model=model,
            config=config,  # type: ignore
        ) as session:
            log("Connected! Waiting for disconnect (doing nothing)...")
            log("Press Ctrl+C to cancel")

            # Track messages received
            message_count = 0

            # Just receive messages until disconnect
            async for response in session.receive():
                message_count += 1
                elapsed = (datetime.now(UTC) - start_time).total_seconds()

                server_content = response.server_content
                if server_content:
                    if server_content.turn_complete:
                        log(f"[{elapsed:.1f}s] Turn complete (msg #{message_count})")
                    elif server_content.model_turn:
                        log(f"[{elapsed:.1f}s] Model turn received (msg #{message_count})")

                # Check for GoAway message
                if hasattr(response, "go_away") and response.go_away:
                    time_left = response.go_away.time_left
                    log(f"[{elapsed:.1f}s] GoAway received! Time left: {time_left}")

                # Check for session resumption update
                if (
                    hasattr(response, "session_resumption_update")
                    and response.session_resumption_update
                ):
                    update = response.session_resumption_update
                    handle = getattr(update, "new_handle", None)
                    resumable = getattr(update, "resumable", None)
                    log(
                        f"[{elapsed:.1f}s] Session resumption update: resumable={resumable}, handle={handle[:20] if handle else None}..."
                    )

    except Exception as e:
        elapsed = (datetime.now(UTC) - start_time).total_seconds()
        log(f"[{elapsed:.1f}s] Disconnected with error: {type(e).__name__}: {e}")

    end_time = datetime.now(UTC)
    duration = (end_time - start_time).total_seconds()

    log("")
    log("=== RESULTS ===")
    log(f"Start time: {start_time.isoformat()}")
    log(f"End time: {end_time.isoformat()}")
    log(f"Total duration: {duration:.1f} seconds ({duration / 60:.1f} minutes)")


def generate_quiet_noise(duration_sec: float = 1.0, amplitude: int = 100) -> bytes:
    """Generate low-amplitude random noise (16kHz, 16-bit, mono).

    Args:
        duration_sec: Duration in seconds
        amplitude: Max amplitude (0-32767). 100 = very quiet background noise.

    Returns:
        PCM audio bytes
    """
    import random
    import struct

    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)

    samples = []
    for _ in range(num_samples):
        # Random value between -amplitude and +amplitude
        sample = random.randint(-amplitude, amplitude)
        samples.append(sample)

    # Pack as 16-bit signed integers (little-endian)
    return struct.pack(f"<{len(samples)}h", *samples)


async def test_with_silence() -> None:
    """Connect and stream silence to see if that extends the connection."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log("ERROR: GEMINI_API_KEY not set in environment")
        return

    model = os.getenv("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")

    log("Initializing Gemini client (WITH SILENCE STREAMING)...")
    log(f"Model: {model}")

    client = genai.Client(api_key=api_key)

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        session_resumption=SessionResumptionConfig(),
    )

    log("Connecting to Gemini Live API (session resumption ENABLED)...")
    start_time = datetime.now(UTC)

    # Generate 1 second of silence (16kHz, 16-bit, mono)
    # 16000 samples/sec * 2 bytes/sample = 32000 bytes per second
    silence_1sec = b"\x00" * 32000

    try:
        async with client.aio.live.connect(
            model=model,
            config=config,
        ) as session:
            log("Connected! Streaming silence every 5 seconds...")
            log("Press Ctrl+C to cancel")

            async def send_silence_periodically():
                """Send silence every 5 seconds."""
                silence_count = 0
                while True:
                    await asyncio.sleep(5)
                    silence_count += 1
                    elapsed = (datetime.now(UTC) - start_time).total_seconds()
                    try:
                        await session.send_realtime_input(
                            audio={"data": silence_1sec, "mime_type": "audio/pcm"}
                        )
                        log(f"[{elapsed:.1f}s] Sent silence #{silence_count}")
                    except Exception as e:
                        log(f"[{elapsed:.1f}s] Failed to send silence: {e}")
                        break

            async def receive_messages():
                """Receive messages from Gemini."""
                message_count = 0
                async for response in session.receive():
                    message_count += 1
                    elapsed = (datetime.now(UTC) - start_time).total_seconds()

                    server_content = response.server_content
                    if server_content:
                        if server_content.turn_complete:
                            log(f"[{elapsed:.1f}s] Turn complete (msg #{message_count})")

                    if hasattr(response, "go_away") and response.go_away:
                        time_left = response.go_away.time_left
                        log(f"[{elapsed:.1f}s] GoAway received! Time left: {time_left}")

                    if (
                        hasattr(response, "session_resumption_update")
                        and response.session_resumption_update
                    ):
                        update = response.session_resumption_update
                        handle = getattr(update, "new_handle", None)
                        resumable = getattr(update, "resumable", None)
                        log(
                            f"[{elapsed:.1f}s] Session resumption update: resumable={resumable}, handle={handle[:20] if handle else None}..."
                        )

            # Run both tasks
            await asyncio.gather(
                send_silence_periodically(),
                receive_messages(),
            )

    except Exception as e:
        elapsed = (datetime.now(UTC) - start_time).total_seconds()
        log(f"[{elapsed:.1f}s] Disconnected with error: {type(e).__name__}: {e}")

    end_time = datetime.now(UTC)
    duration = (end_time - start_time).total_seconds()

    log("")
    log("=== RESULTS ===")
    log(f"Start time: {start_time.isoformat()}")
    log(f"End time: {end_time.isoformat()}")
    log(f"Total duration: {duration:.1f} seconds ({duration / 60:.1f} minutes)")


async def test_with_noise_keepalive() -> None:
    """Connect and stream low-amplitude noise to keep connection alive."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log("ERROR: GEMINI_API_KEY not set in environment")
        return

    model = os.getenv("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")

    log("Initializing Gemini client (WITH NOISE KEEPALIVE)...")
    log(f"Model: {model}")

    client = genai.Client(api_key=api_key)

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        session_resumption=SessionResumptionConfig(),
    )

    log("Connecting to Gemini Live API (session resumption ENABLED)...")
    start_time = datetime.now(UTC)

    # Generate 0.5 second of quiet noise (amplitude 50 = barely audible)
    noise_chunk = generate_quiet_noise(duration_sec=0.5, amplitude=50)
    log(f"Generated noise chunk: {len(noise_chunk)} bytes")

    try:
        async with client.aio.live.connect(
            model=model,
            config=config,
        ) as session:
            log("Connected! Streaming quiet noise every 10 seconds...")
            log("Press Ctrl+C to cancel")

            async def send_noise_periodically():
                """Send noise every 10 seconds."""
                noise_count = 0
                while True:
                    await asyncio.sleep(10)
                    noise_count += 1
                    elapsed = (datetime.now(UTC) - start_time).total_seconds()
                    try:
                        await session.send_realtime_input(
                            audio={"data": noise_chunk, "mime_type": "audio/pcm"}
                        )
                        log(f"[{elapsed:.1f}s] Sent noise keepalive #{noise_count}")
                    except Exception as e:
                        log(f"[{elapsed:.1f}s] Failed to send noise: {e}")
                        break

            async def receive_messages():
                """Receive messages from Gemini."""
                message_count = 0
                async for response in session.receive():
                    message_count += 1
                    elapsed = (datetime.now(UTC) - start_time).total_seconds()

                    server_content = response.server_content
                    if server_content:
                        if server_content.turn_complete:
                            log(f"[{elapsed:.1f}s] Turn complete (msg #{message_count})")

                    if hasattr(response, "go_away") and response.go_away:
                        time_left = response.go_away.time_left
                        log(f"[{elapsed:.1f}s] GoAway received! Time left: {time_left}")

                    if (
                        hasattr(response, "session_resumption_update")
                        and response.session_resumption_update
                    ):
                        update = response.session_resumption_update
                        handle = getattr(update, "new_handle", None)
                        resumable = getattr(update, "resumable", None)
                        log(
                            f"[{elapsed:.1f}s] Session resumption update: resumable={resumable}, handle={handle[:20] if handle else None}..."
                        )

            # Run both tasks
            await asyncio.gather(
                send_noise_periodically(),
                receive_messages(),
            )

    except Exception as e:
        elapsed = (datetime.now(UTC) - start_time).total_seconds()
        log(f"[{elapsed:.1f}s] Disconnected with error: {type(e).__name__}: {e}")

    end_time = datetime.now(UTC)
    duration = (end_time - start_time).total_seconds()

    log("")
    log("=== RESULTS ===")
    log(f"Start time: {start_time.isoformat()}")
    log(f"End time: {end_time.isoformat()}")
    log(f"Total duration: {duration:.1f} seconds ({duration / 60:.1f} minutes)")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Gemini Live API idle timeout")
    parser.add_argument(
        "--with-silence", action="store_true", help="Stream silence (zeros) every 5 seconds"
    )
    parser.add_argument(
        "--with-noise", action="store_true", help="Stream quiet noise every 10 seconds (keepalive)"
    )
    args = parser.parse_args()

    log("=" * 60)
    log("Gemini Live API Idle Timeout Test")
    log("=" * 60)

    if args.with_noise:
        asyncio.run(test_with_noise_keepalive())
    elif args.with_silence:
        asyncio.run(test_with_silence())
    else:
        asyncio.run(test_idle_timeout())


if __name__ == "__main__":
    main()
