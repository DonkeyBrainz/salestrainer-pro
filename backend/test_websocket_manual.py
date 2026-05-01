#!/usr/bin/env python3
"""Manual WebSocket test for Phase 2 verification.

This script connects to the WebSocket, sends test messages, and triggers
session/transcript persistence. After running, check Firestore console to verify.
"""

import asyncio
import json
import sys

import websockets


async def test_websocket(token: str):
    """Test WebSocket connection and send messages."""
    uri = f"ws://localhost:8000/ws/gemini/live?token={token}"

    print("=" * 60)
    print("Phase 2 Manual Verification - WebSocket Persistence Test")
    print("=" * 60)
    print(f"\n🔌 Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!\n")

            # Wait for ready message
            ready_msg = await websocket.recv()
            ready_data = json.loads(ready_msg)
            print(f"← Server: {ready_data}")

            if ready_data.get("type") != "ready":
                print("❌ Expected 'ready' message, got:", ready_data)
                return

            print("\n📝 Starting 3-turn conversation (with proper turn-taking)...\n")

            # Helper function to wait for turn completion
            async def wait_for_turn_complete():
                """Wait for assistant response and turn_complete signal."""
                print("   ⏳ Waiting for assistant response...")
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        if isinstance(response, bytes):
                            # Audio data - just acknowledge
                            pass
                        else:
                            resp_data = json.loads(response)
                            if resp_data.get("type") == "transcription":
                                print(f"   ← Assistant: {resp_data.get('text', '...')[:80]}...")
                            elif resp_data.get("type") == "turn_complete":
                                print("   ✓ Turn complete\n")
                                return  # Turn is done
                            elif resp_data.get("type") == "error":
                                print(f"   ❌ Error: {resp_data}")
                                raise Exception(f"Server error: {resp_data}")
                    except TimeoutError:
                        print("   ⚠️  Timeout waiting for turn completion")
                        return

            # Turn 1
            print("Turn 1:")
            msg1 = {"type": "text", "content": "Hello, I'm practicing sales"}
            print(f"   → User: {msg1['content']}")
            await websocket.send(json.dumps(msg1))
            await wait_for_turn_complete()

            # Turn 2
            print("Turn 2:")
            msg2 = {"type": "text", "content": "Can you roleplay as a customer?"}
            print(f"   → User: {msg2['content']}")
            await websocket.send(json.dumps(msg2))
            await wait_for_turn_complete()

            # Turn 3
            print("Turn 3:")
            msg3 = {"type": "text", "content": "What product are you interested in?"}
            print(f"   → User: {msg3['content']}")
            await websocket.send(json.dumps(msg3))
            await wait_for_turn_complete()

            print("\n🔌 Disconnecting...")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"\n❌ Connection failed: {e}")
        print("Make sure the backend server is running:")
        print("   cd backend && uv run uvicorn app.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("✅ Disconnected!\n")
    print("=" * 60)
    print("Now verify in Firestore:")
    print("=" * 60)
    print()
    print("1. Open: https://console.cloud.google.com/firestore")
    print("2. Select project: sales-coach")
    print("3. Select database: (default)")
    print()
    print("4. Check 'sessions' collection:")
    print("   - Find document for user_id: 93596f8d-fcae-4eca-b697-84f2a1715a9b")
    print("   - Sort by 'created_at' (newest first)")
    print("   - Verify fields:")
    print("     • status: 'completed'")
    print("     • message_count: 6 (3 user + 3 assistant)")
    print("     • duration: (seconds between started_at and ended_at)")
    print("     • ended_at: (timestamp when you disconnected)")
    print()
    print("5. Check 'transcripts' collection:")
    print("   - Find document with matching session_id")
    print("   - Verify fields:")
    print("     • total_messages: 6")
    print("     • messages: array of 6 objects")
    print("       - Message 1: role='user', text='Hello, I'm practicing sales'")
    print("       - Message 2: role='assistant', text='...'")
    print("       - Message 3: role='user', text='Can you roleplay as a customer?'")
    print("       - Message 4: role='assistant', text='...'")
    print("       - Message 5: role='user', text='What product are you interested in?'")
    print("       - Message 6: role='assistant', text='...'")
    print("     • total_words: (should be > 0)")
    print()
    print("=" * 60)
    print("✅ Phase 2 Manual Verification Complete!")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_websocket_manual.py <JWT_TOKEN>")
        print()
        print("Example:")
        print("  python test_websocket_manual.py 'eyJhbGciOiJIUzI1NiIs...'")
        sys.exit(1)

    token = sys.argv[1]
    asyncio.run(test_websocket(token))
