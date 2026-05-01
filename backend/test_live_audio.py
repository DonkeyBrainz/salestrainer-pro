#!/usr/bin/env python3
"""Test Gemini Live WebSocket with text input and audio output."""

import asyncio
import json
import sys
import wave

import websockets


async def test_live_audio(token: str, save_audio: bool = True):
    """Test Gemini Live API by sending text and receiving audio.

    Args:
        token: JWT access token
        save_audio: If True, save received audio to file
    """
    uri = f"ws://localhost:8000/ws/gemini/live?token={token}"
    print(f"Connecting to {uri}...\n")

    audio_chunks = []

    async with websockets.connect(uri) as websocket:
        # Wait for ready message
        ready_msg = await websocket.recv()
        print(f"✓ Connected: {ready_msg}\n")

        # Send a text message
        test_message = {
            "type": "text",
            "content": "Hello! Please introduce yourself in one sentence.",
        }
        print(f"Sending: {test_message['content']}")
        await websocket.send(json.dumps(test_message))

        # Receive responses
        print("\nReceiving responses from Gemini...\n")
        turn_complete = False

        try:
            while not turn_complete:
                message = await asyncio.wait_for(websocket.recv(), timeout=30.0)

                if isinstance(message, bytes):
                    # Audio data received
                    print(f"  ♪ Audio chunk: {len(message)} bytes")
                    audio_chunks.append(message)
                else:
                    # JSON message received
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "text":
                        print(f"  💬 Text: {data.get('text', '')}")
                    elif msg_type == "turn_complete":
                        print("  ✓ Turn complete")
                        turn_complete = True
                    else:
                        print(f"  📨 Message: {data}")

        except TimeoutError:
            print("\n⏱ Timeout waiting for response")
        except Exception as e:
            print(f"\n❌ Error: {e}")

    # Save audio to file
    if save_audio and audio_chunks:
        output_file = "gemini_response.wav"
        print(f"\n💾 Saving {len(audio_chunks)} audio chunks to {output_file}...")

        # Combine all audio chunks
        audio_data = b"".join(audio_chunks)

        # Save as WAV file (24kHz, 16-bit PCM, mono)
        with wave.open(output_file, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(24000)  # 24kHz output
            wav_file.writeframes(audio_data)

        print(f"✓ Saved audio to {output_file}")
        print("  Format: 24kHz, 16-bit PCM, mono")
        print(f"  Duration: ~{len(audio_data) / (24000 * 2):.2f} seconds")
        print(f"\nPlay with: afplay {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_live_audio.py <access_token> [--no-save]")
        print("\nGet your access token from the /auth/callback response")
        print("Example: python test_live_audio.py eyJhbGc...")
        sys.exit(1)

    token = sys.argv[1]
    save_audio = "--no-save" not in sys.argv

    asyncio.run(test_live_audio(token, save_audio))
