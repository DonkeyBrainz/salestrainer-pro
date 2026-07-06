"""Analyze how much information customers volunteer unprompted.

This metric should correlate with regard level:
- High regard: Freely volunteers name, needs, personal details
- Low regard: Guarded, only responds when directly asked
"""

import asyncio
import re
from collections import defaultdict
from typing import Any

from google.cloud import firestore

from app.config import get_settings

# Patterns indicating customer volunteered information
VOLUNTEER_PATTERNS = {
    "name": {
        "patterns": [
            r"(?i)I'm (\w+)",  # "I'm Sarah", "I'm Robert"
            r"(?i)my name is (\w+)",
            r"(?i)I am (\w+)",
            r"(?i)call me (\w+)",
        ],
        "description": "Volunteering name",
    },
    "needs": {
        "patterns": [
            r"(?i)I'm looking for",
            r"(?i)I need",
            r"(?i)we're looking for",
            r"(?i)we need",
            r"(?i)shopping for",
            r"(?i)browsing for",
            r"(?i)hoping to find",
            r"(?i)want to find",
        ],
        "description": "Stating needs unprompted",
    },
    "personal_details": {
        "patterns": [
            r"(?i)my (?:husband|wife|partner|kids|children|family)",
            r"(?i)we (?:just|recently) (?:moved|bought|got)",
            r"(?i)our (?:apartment|house|home|place)",
            r"(?i)I (?:have|had) (?:two|three|\d+) (?:kids|children)",
            r"(?i)just moved into",
            r"(?i)recently (?:laid off|separated|divorced)",
        ],
        "description": "Sharing personal/family details",
    },
    "timeline": {
        "patterns": [
            r"(?i)(?:need it|want it|looking to buy) (?:by|within|in) (?:the next|\d+)",
            r"(?i)moving in (?:next week|soon|this month)",
            r"(?i)no rush",
            r"(?i)not in a hurry",
            r"(?i)taking my time",
        ],
        "description": "Stating timeline/urgency",
    },
    "budget": {
        "patterns": [
            r"(?i)(?:budget|looking to spend|price range) (?:is|of|around)",
            r"(?i)between \$?\d+,?\d* (?:and|to) \$?\d+,?\d*",
            r"(?i)under \$?\d+,?\d*",
            r"(?i)around \$?\d+,?\d*",
            r"(?i)can't spend more than",
            r"(?i)tight budget",
            r"(?i)on a budget",
        ],
        "description": "Mentioning budget",
    },
    "preferences": {
        "patterns": [
            r"(?i)I (?:love|like|prefer|want)",
            r"(?i)we (?:love|like|prefer|want)",
            r"(?i)important to (?:me|us)",
            r"(?i)looking for something that",
            r"(?i)care about (?:is|are)",
        ],
        "description": "Sharing preferences",
    },
    "enthusiasm": {
        "patterns": [
            r"(?i)(?:so|really|very) excited",
            r"(?i)can't wait",
            r"(?i)love (?:to|the|your)",
            r"(?i)that sounds (?:great|perfect|lovely|amazing)",
            r"!$",  # Exclamation marks
        ],
        "description": "Showing enthusiasm",
    },
}


# Patterns indicating user ASKED for information (reduces volunteer score)
PROMPTING_PATTERNS = {
    "asking_name": [
        r"(?i)what'?s your name",
        r"(?i)can I (?:get|have) your name",
        r"(?i)may I (?:get|have) your name",
        r"(?i)who are you",
        r"(?i)you are\?",
    ],
    "asking_needs": [
        r"(?i)what (?:are you|you're) looking for",
        r"(?i)what (?:do you|can I) (?:need|help you with)",
        r"(?i)how can I help",
        r"(?i)what brings you",
    ],
    "asking_details": [
        r"(?i)tell me (?:about|a little)",
        r"(?i)can you tell me",
        r"(?i)what (?:do you|does)",
        r"(?i)how (?:many|much|often)",
    ],
}


async def analyze_volunteer_behavior(user_email: str) -> dict[str, Any]:
    """Analyze information volunteering by persona/difficulty.

    Args:
        user_email: User's email address

    Returns:
        Analysis of volunteer behavior metrics by persona
    """
    settings = get_settings()
    db = firestore.AsyncClient(
        project=settings.gcp_project_id,
        database=settings.firestore_database,
    )

    # Find user
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

    # Get sessions
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

    # Get transcripts
    print("\n📝 Fetching transcripts...")
    transcripts = []
    for session in sessions:
        transcript_query = (
            db.collection("transcripts").where("session_id", "==", session["session_id"]).limit(1)
        )
        async for doc in transcript_query.stream():
            transcript_data = doc.to_dict()
            transcript_data["session"] = session
            transcripts.append(transcript_data)

    print(f"✅ Found {len(transcripts)} transcripts")

    # Analyze volunteering behavior
    print("\n🔬 Analyzing volunteer behavior...\n")

    # Track by persona and difficulty
    by_persona = defaultdict(
        lambda: {
            "message_count": 0,
            "first_message_volunteers": 0,
            "volunteer_events": defaultdict(int),
            "total_volunteer_score": 0,
            "sessions": 0,
            "examples": [],
        }
    )

    by_difficulty = defaultdict(
        lambda: {
            "message_count": 0,
            "first_message_volunteers": 0,
            "volunteer_events": defaultdict(int),
            "total_volunteer_score": 0,
            "sessions": 0,
        }
    )

    for transcript in transcripts:
        session = transcript["session"]
        messages = transcript.get("messages", [])
        persona = session.get("selected_persona", "unknown")
        difficulty = session.get("difficulty", "unknown")

        by_persona[persona]["sessions"] += 1
        by_difficulty[difficulty]["sessions"] += 1

        # Check first customer message (most important for volunteering)
        first_customer_msg = None
        for msg in messages:
            if msg.get("role") in ["assistant", "model"]:
                first_customer_msg = msg.get("text", "")
                break

        if first_customer_msg:
            # Check if first message volunteers information
            first_msg_score = 0
            volunteered_items = []

            for category, info in VOLUNTEER_PATTERNS.items():
                for pattern in info["patterns"]:
                    if re.search(pattern, first_customer_msg):
                        first_msg_score += 1
                        volunteered_items.append(category)
                        by_persona[persona]["volunteer_events"][category] += 1
                        by_difficulty[difficulty]["volunteer_events"][category] += 1
                        break  # Only count once per category

            if first_msg_score > 0:
                by_persona[persona]["first_message_volunteers"] += 1
                by_difficulty[difficulty]["first_message_volunteers"] += 1

                # Save example
                if len(by_persona[persona]["examples"]) < 3:
                    by_persona[persona]["examples"].append(
                        {
                            "session_id": session["session_id"],
                            "message": first_customer_msg,
                            "volunteered": volunteered_items,
                            "score": first_msg_score,
                        }
                    )

        # Analyze all customer messages
        for idx, msg in enumerate(messages):
            if msg.get("role") in ["assistant", "model"]:
                customer_text = msg.get("text", "")
                by_persona[persona]["message_count"] += 1
                by_difficulty[difficulty]["message_count"] += 1

                # Check if previous user message was a prompt
                was_prompted = False
                if idx > 0:
                    prev_user_msg = None
                    for i in range(idx - 1, -1, -1):
                        if messages[i].get("role") == "user":
                            prev_user_msg = messages[i].get("text", "")
                            break

                    if prev_user_msg:
                        for prompt_category, patterns in PROMPTING_PATTERNS.items():
                            for pattern in patterns:
                                if re.search(pattern, prev_user_msg):
                                    was_prompted = True
                                    break
                            if was_prompted:
                                break

                # Score volunteer behavior (only if not prompted)
                if not was_prompted:
                    msg_score = 0
                    for category, info in VOLUNTEER_PATTERNS.items():
                        for pattern in info["patterns"]:
                            if re.search(pattern, customer_text):
                                msg_score += 1
                                break

                    by_persona[persona]["total_volunteer_score"] += msg_score
                    by_difficulty[difficulty]["total_volunteer_score"] += msg_score

    # Calculate metrics
    print("=" * 100)
    print("📊 VOLUNTEER BEHAVIOR ANALYSIS")
    print("=" * 100)

    print("\n📋 BY PERSONA\n")

    # Sort by volunteer score (high to low)
    sorted_personas = sorted(
        by_persona.items(),
        key=lambda x: x[1]["total_volunteer_score"] / max(x[1]["message_count"], 1),
        reverse=True,
    )

    for persona, stats in sorted_personas:
        avg_score = stats["total_volunteer_score"] / max(stats["message_count"], 1)
        first_msg_rate = stats["first_message_volunteers"] / max(stats["sessions"], 1) * 100

        print(f"🎭 {persona.upper()}")
        print(f"   Sessions: {stats['sessions']}")
        print(f"   Total Messages: {stats['message_count']}")
        print(f"   Volunteer Score: {avg_score:.2f} (avg per message)")
        print(f"   First Message Volunteer Rate: {first_msg_rate:.0f}%")

        # Category breakdown
        if stats["volunteer_events"]:
            print("   Volunteers:")
            for category, count in sorted(
                stats["volunteer_events"].items(), key=lambda x: x[1], reverse=True
            ):
                print(f"     - {VOLUNTEER_PATTERNS[category]['description']}: {count}x")

        # Examples
        if stats["examples"]:
            print("   First Message Examples:")
            for ex in stats["examples"][:2]:
                print(f'     • "{ex["message"][:100]}..." (score: {ex["score"]})')

        print()

    print("\n📊 BY DIFFICULTY/REGARD LEVEL\n")

    # Sort by volunteer score
    sorted_difficulty = sorted(
        by_difficulty.items(),
        key=lambda x: x[1]["total_volunteer_score"] / max(x[1]["message_count"], 1),
        reverse=True,
    )

    for difficulty, stats in sorted_difficulty:
        avg_score = stats["total_volunteer_score"] / max(stats["message_count"], 1)
        first_msg_rate = stats["first_message_volunteers"] / max(stats["sessions"], 1) * 100

        print(f"⚡ {difficulty.upper()}")
        print(f"   Sessions: {stats['sessions']}")
        print(f"   Total Messages: {stats['message_count']}")
        print(f"   Volunteer Score: {avg_score:.2f} (avg per message)")
        print(f"   First Message Volunteer Rate: {first_msg_rate:.0f}%")

        # Category breakdown
        if stats["volunteer_events"]:
            print("   Top Volunteers:")
            for category, count in sorted(
                stats["volunteer_events"].items(), key=lambda x: x[1], reverse=True
            )[:5]:
                print(f"     - {VOLUNTEER_PATTERNS[category]['description']}: {count}x")

        print()

    print("=" * 100)

    return {
        "by_persona": dict(by_persona),
        "by_difficulty": dict(by_difficulty),
    }


async def main() -> None:
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_volunteer_behavior.py <email>")
        print("Example: python scripts/analyze_volunteer_behavior.py user@example.com")
        sys.exit(1)

    user_email = sys.argv[1]
    await analyze_volunteer_behavior(user_email)


if __name__ == "__main__":
    asyncio.run(main())
