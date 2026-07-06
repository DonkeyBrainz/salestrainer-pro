"""Analyze user transcripts to understand testing strategy and improve scrimmages."""

import asyncio
import collections
from datetime import datetime
from typing import Any

from google.cloud import firestore

from app.config import get_settings


async def analyze_user_transcripts(user_email: str) -> dict[str, Any]:
    """Analyze transcripts for a specific user.

    Args:
        user_email: User's email address

    Returns:
        Analysis summary including testing patterns, common phrases, session stats
    """
    settings = get_settings()
    db = firestore.AsyncClient(
        project=settings.gcp_project_id,
        database=settings.firestore_database,
    )

    # 1. Find user by email
    print(f"🔍 Looking up user: {user_email}")
    users_query = db.collection("users").where("email", "==", user_email).limit(1)
    user_doc = None
    async for doc in users_query.stream():
        user_doc = doc
        break

    if not user_doc:
        print(f"❌ User not found: {user_email}")
        return {}

    user_data = user_doc.to_dict()
    user_id = user_doc.id
    print(f"✅ Found user: {user_data.get('name')} (ID: {user_id})")

    # 2. Get all sessions for this user
    print("\n📊 Fetching sessions...")
    sessions_query = (
        db.collection("sessions").where("user_id", "==", user_id).where("is_deleted", "==", False)
    )

    sessions = []
    async for doc in sessions_query.stream():
        session_data = doc.to_dict()
        session_data["session_id"] = doc.id
        sessions.append(session_data)

    print(f"✅ Found {len(sessions)} sessions")

    # 3. Get transcripts for all sessions
    print("\n📝 Fetching transcripts...")
    transcripts = []
    for session in sessions:
        transcript_query = (
            db.collection("transcripts").where("session_id", "==", session["session_id"]).limit(1)
        )
        async for doc in transcript_query.stream():
            transcript_data = doc.to_dict()
            transcript_data["transcript_id"] = doc.id
            transcript_data["session"] = session  # Attach session info
            transcripts.append(transcript_data)

    print(f"✅ Found {len(transcripts)} transcripts")

    if not transcripts:
        print("\n⚠️  No transcripts found for this user")
        return {
            "user_email": user_email,
            "user_id": user_id,
            "user_name": user_data.get("name"),
            "total_sessions": len(sessions),
            "total_transcripts": 0,
        }

    # 4. Analyze transcripts
    print("\n🔬 Analyzing transcripts...\n")

    analysis = {
        "user_email": user_email,
        "user_id": user_id,
        "user_name": user_data.get("name"),
        "total_sessions": len(sessions),
        "total_transcripts": len(transcripts),
        "session_breakdown": collections.defaultdict(int),
        "persona_usage": collections.Counter(),
        "difficulty_usage": collections.Counter(),
        "status_breakdown": collections.Counter(),
        "total_messages": 0,
        "total_user_messages": 0,
        "total_customer_messages": 0,
        "avg_messages_per_session": 0,
        "avg_session_duration_minutes": 0,
        "common_user_phrases": [],
        "common_customer_phrases": [],
        "sessions_by_date": collections.defaultdict(int),
        "detailed_sessions": [],
    }

    all_user_messages = []
    all_customer_messages = []
    total_duration_seconds = 0
    session_count_with_duration = 0

    for transcript in transcripts:
        session = transcript["session"]
        messages = transcript.get("messages", [])

        # Session metadata
        session_type = session.get("session_type", "unknown")
        persona = session.get("selected_persona", "unknown")
        difficulty = session.get("difficulty", "unknown")
        status = session.get("status", "unknown")

        analysis["session_breakdown"][session_type] += 1
        analysis["persona_usage"][persona] += 1
        analysis["difficulty_usage"][difficulty] += 1
        analysis["status_breakdown"][status] += 1

        # Session timing
        started_at = session.get("started_at")
        ended_at = session.get("ended_at")
        if started_at and ended_at:
            if isinstance(started_at, datetime):
                date_key = started_at.strftime("%Y-%m-%d")
            else:
                date_key = started_at.date().isoformat()
            analysis["sessions_by_date"][date_key] += 1

            # Duration
            duration = session.get("duration")
            if duration:
                total_duration_seconds += duration
                session_count_with_duration += 1

        # Message analysis
        user_messages = []
        customer_messages = []

        for msg in messages:
            role = msg.get("role")
            text = msg.get("text", "")

            if role == "user":
                user_messages.append(text)
                all_user_messages.append(text)
            elif role == "assistant" or role == "model":
                customer_messages.append(text)
                all_customer_messages.append(text)

        analysis["total_messages"] += len(messages)
        analysis["total_user_messages"] += len(user_messages)
        analysis["total_customer_messages"] += len(customer_messages)

        # Detailed session info
        session_detail = {
            "session_id": session["session_id"],
            "type": session_type,
            "persona": persona,
            "difficulty": difficulty,
            "status": status,
            "started_at": started_at.isoformat()
            if isinstance(started_at, datetime)
            else str(started_at),
            "ended_at": ended_at.isoformat()
            if isinstance(ended_at, datetime)
            else str(ended_at)
            if ended_at
            else None,
            "message_count": len(messages),
            "user_message_count": len(user_messages),
            "customer_message_count": len(customer_messages),
            "user_messages": user_messages[:5],  # First 5 messages
            "customer_messages": customer_messages[:5],
        }
        analysis["detailed_sessions"].append(session_detail)

    # Calculate averages
    if transcripts:
        analysis["avg_messages_per_session"] = analysis["total_messages"] / len(transcripts)

    if session_count_with_duration > 0:
        avg_duration_seconds = total_duration_seconds / session_count_with_duration
        analysis["avg_session_duration_minutes"] = round(avg_duration_seconds / 60, 2)

    # Find common phrases (simple word frequency)
    # User phrases (3+ words)
    user_text = " ".join(all_user_messages).lower()
    user_words = user_text.split()
    user_trigrams = [" ".join(user_words[i : i + 3]) for i in range(len(user_words) - 2)]
    analysis["common_user_phrases"] = collections.Counter(user_trigrams).most_common(20)

    # Customer phrases (3+ words)
    customer_text = " ".join(all_customer_messages).lower()
    customer_words = customer_text.split()
    customer_trigrams = [
        " ".join(customer_words[i : i + 3]) for i in range(len(customer_words) - 2)
    ]
    analysis["common_customer_phrases"] = collections.Counter(customer_trigrams).most_common(20)

    # Print summary
    print("=" * 80)
    print(f"📊 ANALYSIS SUMMARY FOR {user_data.get('name')} ({user_email})")
    print("=" * 80)

    print("\n📈 OVERALL STATS")
    print(f"  Total Sessions: {analysis['total_sessions']}")
    print(f"  Total Transcripts: {analysis['total_transcripts']}")
    print(f"  Total Messages: {analysis['total_messages']}")
    print(f"  - User Messages: {analysis['total_user_messages']}")
    print(f"  - Customer Messages: {analysis['total_customer_messages']}")
    print(f"  Avg Messages/Session: {analysis['avg_messages_per_session']:.1f}")
    print(f"  Avg Session Duration: {analysis['avg_session_duration_minutes']:.1f} minutes")

    print("\n🎭 SESSION BREAKDOWN")
    for session_type, count in analysis["session_breakdown"].items():
        print(f"  {session_type}: {count}")

    print("\n👥 PERSONA USAGE")
    for persona, count in analysis["persona_usage"].most_common():
        print(f"  {persona}: {count}")

    print("\n⚡ DIFFICULTY BREAKDOWN")
    for difficulty, count in analysis["difficulty_usage"].most_common():
        print(f"  {difficulty}: {count}")

    print("\n✅ STATUS BREAKDOWN")
    for status, count in analysis["status_breakdown"].items():
        print(f"  {status}: {count}")

    print("\n📅 SESSIONS BY DATE")
    for date in sorted(analysis["sessions_by_date"].keys()):
        count = analysis["sessions_by_date"][date]
        print(f"  {date}: {count}")

    print("\n💬 TOP 10 USER PHRASES (3-grams)")
    for phrase, count in analysis["common_user_phrases"][:10]:
        if count > 1:  # Only show phrases used more than once
            print(f"  '{phrase}': {count}x")

    print("\n🗣️  TOP 10 CUSTOMER PHRASES (3-grams)")
    for phrase, count in analysis["common_customer_phrases"][:10]:
        if count > 1:
            print(f"  '{phrase}': {count}x")

    print("\n📋 RECENT SESSIONS (last 5)")
    for session in sorted(
        analysis["detailed_sessions"],
        key=lambda x: x["started_at"],
        reverse=True,
    )[:5]:
        print(f"\n  Session: {session['session_id'][:8]}...")
        print(
            f"  Type: {session['type']} | Persona: {session['persona']} | Difficulty: {session['difficulty']}"
        )
        print(f"  Status: {session['status']} | Messages: {session['message_count']}")
        print(f"  Started: {session['started_at']}")
        if session["user_messages"]:
            print("  First user messages:")
            for msg in session["user_messages"][:3]:
                print(f"    - {msg[:100]}...")

    print("\n" + "=" * 80)

    return analysis


async def main() -> None:
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_user_transcripts.py <email>")
        print("Example: python scripts/analyze_user_transcripts.py user@example.com")
        sys.exit(1)

    user_email = sys.argv[1]
    analysis = await analyze_user_transcripts(user_email)

    # Optionally save to JSON
    if len(sys.argv) > 2 and sys.argv[2] == "--save":
        import json
        from datetime import datetime

        output_file = f"user_analysis_{user_email.replace('@', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Convert Counter to dict for JSON serialization
        analysis_json = {
            **analysis,
            "session_breakdown": dict(analysis["session_breakdown"]),
            "persona_usage": dict(analysis["persona_usage"]),
            "difficulty_usage": dict(analysis["difficulty_usage"]),
            "status_breakdown": dict(analysis["status_breakdown"]),
            "sessions_by_date": dict(analysis["sessions_by_date"]),
        }

        with open(output_file, "w") as f:
            json.dump(analysis_json, f, indent=2, default=str)

        print(f"\n💾 Analysis saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
