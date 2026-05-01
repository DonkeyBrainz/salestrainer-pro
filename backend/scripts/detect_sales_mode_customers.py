"""Detect when AI customers inappropriately act like salespeople."""

import asyncio
import re
from typing import Any

from google.cloud import firestore

from app.config import get_settings


# Patterns that indicate customer is acting like a salesperson
SALES_MODE_PATTERNS = [
    # Direct sales questions
    r"(?i)is there something (?:you're|you are|you're) looking for",
    r"(?i)what (?:are you|you're) looking for",
    r"(?i)can I help you (?:with|find)",
    r"(?i)how can I (?:help|assist) you",
    r"(?i)what brings you (?:in|here) today",
    r"(?i)are you looking for (?:anything|something) (?:in particular|specific)",
    r"(?i)let me (?:show|help) you",
    r"(?i)would you like (?:to see|me to show)",
    r"(?i)I can show you",
    r"(?i)I'd be happy to (?:help|show|assist)",
    r"(?i)we have (?:a great|some nice|several)",
    r"(?i)this would be (?:perfect|great) for",
    r"(?i)have you considered",
    r"(?i)let me tell you about",
    r"(?i)I recommend",
    r"(?i)you should (?:check out|look at|consider)",
    r"(?i)our (?:best seller|most popular)",
    r"(?i)this is one of our",
    # Offering assistance
    r"(?i)need (?:any )?help with",
    r"(?i)(?:feel free to|please) ask (?:me )?if you",
    r"(?i)let me know if (?:you|there's)",
]


async def detect_sales_mode(user_email: str) -> dict[str, Any]:
    """Detect sales mode behaviors in customer transcripts.

    Args:
        user_email: User's email address

    Returns:
        Analysis of sales mode violations
    """
    settings = get_settings()
    db = firestore.AsyncClient(
        project=settings.gcp_project_id,
        database=settings.firestore_database,
    )

    # 1. Find user
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

    # 2. Get sessions
    print(f"\n📊 Fetching sessions...")
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

    print(f"✅ Found {len(sessions)} sessions")

    # 3. Get transcripts
    print(f"\n📝 Fetching transcripts...")
    transcripts = []
    for session in sessions:
        transcript_query = (
            db.collection("transcripts")
            .where("session_id", "==", session["session_id"])
            .limit(1)
        )
        async for doc in transcript_query.stream():
            transcript_data = doc.to_dict()
            transcript_data["transcript_id"] = doc.id
            transcript_data["session"] = session
            transcripts.append(transcript_data)

    print(f"✅ Found {len(transcripts)} transcripts")

    # 4. Analyze for sales mode violations
    print(f"\n🔬 Analyzing for sales mode violations...\n")

    violations = []
    total_customer_messages = 0
    sessions_with_violations = set()

    for transcript in transcripts:
        session = transcript["session"]
        messages = transcript.get("messages", [])

        for idx, msg in enumerate(messages):
            role = msg.get("role")
            text = msg.get("text", "")

            if role in ["assistant", "model"]:
                total_customer_messages += 1

                # Check each pattern
                for pattern in SALES_MODE_PATTERNS:
                    if re.search(pattern, text):
                        violation = {
                            "session_id": session["session_id"],
                            "persona": session.get("selected_persona", "unknown"),
                            "difficulty": session.get("difficulty", "unknown"),
                            "message_index": idx,
                            "customer_message": text,
                            "pattern_matched": pattern,
                            "timestamp": msg.get("timestamp"),
                        }
                        violations.append(violation)
                        sessions_with_violations.add(session["session_id"])
                        break  # Only count once per message

    # 5. Report findings
    print("=" * 80)
    print(f"🚨 SALES MODE VIOLATION REPORT")
    print("=" * 80)

    print(f"\n📊 SUMMARY")
    print(f"  Total Transcripts: {len(transcripts)}")
    print(f"  Total Customer Messages: {total_customer_messages}")
    print(f"  Violations Found: {len(violations)}")
    print(f"  Sessions with Violations: {len(sessions_with_violations)}")
    print(f"  Violation Rate: {len(violations) / total_customer_messages * 100:.1f}% of customer messages")

    if violations:
        print(f"\n🔴 VIOLATIONS DETECTED\n")

        # Group by persona
        by_persona = {}
        for v in violations:
            persona = v["persona"]
            if persona not in by_persona:
                by_persona[persona] = []
            by_persona[persona].append(v)

        print(f"📋 Violations by Persona:")
        for persona, persona_violations in sorted(by_persona.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  {persona}: {len(persona_violations)} violations")

        print(f"\n💬 Sample Violations (first 20):\n")
        for i, v in enumerate(violations[:20], 1):
            print(f"{i}. Session: {v['session_id'][:8]}... | Persona: {v['persona']}")
            print(f"   Message: \"{v['customer_message'][:150]}...\"")
            print(f"   Pattern: {v['pattern_matched']}")
            print()

        print(f"\n📈 Most Common Patterns:")
        pattern_counts = {}
        for v in violations:
            pattern = v["pattern_matched"]
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {count}x - {pattern}")

    else:
        print(f"\n✅ NO VIOLATIONS DETECTED")
        print(f"   All customer personas stayed in character!")

    print("\n" + "=" * 80)

    return {
        "total_transcripts": len(transcripts),
        "total_customer_messages": total_customer_messages,
        "violations_found": len(violations),
        "sessions_with_violations": len(sessions_with_violations),
        "violation_rate": len(violations) / total_customer_messages if total_customer_messages > 0 else 0,
        "violations": violations,
        "by_persona": {
            persona: len(persona_violations)
            for persona, persona_violations in by_persona.items()
        } if violations else {},
    }


async def main() -> None:
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/detect_sales_mode_customers.py <email>")
        print("Example: python scripts/detect_sales_mode_customers.py user@example.com")
        sys.exit(1)

    user_email = sys.argv[1]
    results = await detect_sales_mode(user_email)

    # Save report
    if len(sys.argv) > 2 and sys.argv[2] == "--save":
        import json
        from datetime import datetime

        output_file = f"sales_mode_violations_{user_email.replace('@', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n💾 Report saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
