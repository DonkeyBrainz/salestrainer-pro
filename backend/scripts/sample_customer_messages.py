"""Show sample customer messages for quality review."""

import asyncio
import random
from typing import Any

from google.cloud import firestore

from app.config import get_settings


async def sample_customer_messages(user_email: str, sample_size: int = 30) -> list[dict[str, Any]]:
    """Get sample customer messages for manual review.

    Args:
        user_email: User's email address
        sample_size: Number of messages to sample

    Returns:
        List of sampled customer messages with context
    """
    settings = get_settings()
    db = firestore.AsyncClient(
        project=settings.gcp_project_id,
        database=settings.firestore_database,
    )

    # Find user
    users_query = db.collection("users").where("email", "==", user_email).limit(1)
    user_doc = None
    async for doc in users_query.stream():
        user_doc = doc
        break

    if not user_doc:
        return []

    user_id = user_doc.id

    # Get sessions
    sessions_query = (
        db.collection("sessions")
        .where("user_id", "==", user_id)
        .where("is_deleted", "==", False)
    )

    sessions = []
    async for doc in sessions_query.stream():
        session_data = doc.to_dict()
        session_data["session_id"] = doc.id
        sessions.append(session_data)

    # Get transcripts
    transcripts = []
    for session in sessions:
        transcript_query = (
            db.collection("transcripts")
            .where("session_id", "==", session["session_id"])
            .limit(1)
        )
        async for doc in transcript_query.stream():
            transcript_data = doc.to_dict()
            transcript_data["session"] = session
            transcripts.append(transcript_data)

    # Collect all customer messages with context
    all_customer_messages = []
    for transcript in transcripts:
        session = transcript["session"]
        messages = transcript.get("messages", [])

        for idx, msg in enumerate(messages):
            if msg.get("role") in ["assistant", "model"]:
                # Get previous user message for context
                prev_user_msg = None
                for i in range(idx - 1, -1, -1):
                    if messages[i].get("role") == "user":
                        prev_user_msg = messages[i].get("text", "")
                        break

                all_customer_messages.append({
                    "persona": session.get("selected_persona", "unknown"),
                    "difficulty": session.get("difficulty", "unknown"),
                    "customer_message": msg.get("text", ""),
                    "previous_user_message": prev_user_msg,
                    "message_index": idx,
                    "session_id": session["session_id"],
                })

    # Sample randomly
    sample = random.sample(all_customer_messages, min(sample_size, len(all_customer_messages)))

    # Print samples
    print("=" * 100)
    print(f"📝 CUSTOMER MESSAGE SAMPLES (Random {len(sample)} of {len(all_customer_messages)})")
    print("=" * 100)

    for i, msg in enumerate(sample, 1):
        print(f"\n{i}. Persona: {msg['persona']} | Difficulty: {msg['difficulty']}")
        print(f"   Session: {msg['session_id'][:8]}...")
        if msg['previous_user_message']:
            print(f"\n   👤 USER: {msg['previous_user_message']}")
        print(f"   🤖 CUSTOMER: {msg['customer_message']}")
        print()

    print("=" * 100)

    return sample


async def main() -> None:
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/sample_customer_messages.py <email> [sample_size]")
        print("Example: python scripts/sample_customer_messages.py user@example.com 30")
        sys.exit(1)

    user_email = sys.argv[1]
    sample_size = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    await sample_customer_messages(user_email, sample_size)


if __name__ == "__main__":
    asyncio.run(main())
