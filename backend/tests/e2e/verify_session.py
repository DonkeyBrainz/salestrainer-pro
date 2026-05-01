#!/usr/bin/env python3
"""Verification script for E2E session persistence.

Checks Firestore to verify session and transcript data after a test session.

Usage:
    python tests/e2e/verify_session.py --session-id <SESSION_ID>

Environment:
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON
    GCP_PROJECT_ID: Google Cloud project ID
    FIRESTORE_DATABASE: Firestore database ID (default: "(default)")
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any


def format_timestamp(ts: Any) -> str:
    """Format Firestore timestamp for display."""
    if ts is None:
        return "N/A"
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    return str(ts)


def check_session(db: Any, session_id: str) -> dict[str, Any] | None:
    """Check session document in Firestore.

    Args:
        db: Firestore client
        session_id: Session ID to check

    Returns:
        Session data if found, None otherwise
    """
    print(f"\n{'=' * 60}")
    print("CHECKING SESSION")
    print(f"{'=' * 60}")

    doc_ref = db.collection("sessions").document(session_id)
    doc = doc_ref.get()

    if not doc.exists:
        print(f"[FAIL] Session {session_id} not found in Firestore")
        return None

    data = doc.to_dict()
    print(f"[PASS] Session found: {session_id}")
    print(f"\n  Status: {data.get('status')}")
    print(f"  User ID: {data.get('user_id')}")
    print(f"  Persona: {data.get('selected_persona')}")
    print(f"  Difficulty: {data.get('difficulty')}")
    print(f"  Started: {format_timestamp(data.get('started_at'))}")
    print(f"  Ended: {format_timestamp(data.get('ended_at'))}")
    print(f"  Duration: {data.get('duration')}s")
    print(f"  Message Count: {data.get('message_count')}")

    # Check agent state snapshot
    snapshot = data.get("agent_state_snapshot")
    if snapshot:
        print(f"\n  Agent State Snapshot: {len(snapshot)} chars")
        try:
            state = json.loads(snapshot)
            print(f"    - Mood: {state.get('mood')}")
            print(f"    - Regard: {state.get('regard_level')}")
            print(f"    - Turn Count: {state.get('turn_count')}")
            print(f"    - Objections Raised: {state.get('objections_raised')}")
        except json.JSONDecodeError:
            print("    [WARN] Could not parse agent state snapshot")
    else:
        print("\n  [WARN] No agent state snapshot saved")

    return data


def check_transcript(db: Any, session_id: str) -> list[dict[str, Any]]:
    """Check transcript messages in Firestore.

    Args:
        db: Firestore client
        session_id: Session ID to check

    Returns:
        List of transcript messages
    """
    print(f"\n{'=' * 60}")
    print("CHECKING TRANSCRIPT")
    print(f"{'=' * 60}")

    query = db.collection("transcripts").where("session_id", "==", session_id).order_by("timestamp")
    docs = query.stream()
    messages = [doc.to_dict() for doc in docs]

    if not messages:
        print(f"[WARN] No transcript messages found for session {session_id}")
        return []

    print(f"[PASS] Found {len(messages)} transcript messages")
    print("\nConversation:")
    print("-" * 40)

    for msg in messages:
        role = msg.get("role", "unknown").upper()
        text = msg.get("text", "")
        ts = format_timestamp(msg.get("timestamp"))

        # Truncate long messages
        if len(text) > 100:
            text = text[:97] + "..."

        print(f"[{role}] ({ts[:19]}) {text}")

    return messages


def check_user_sessions(db: Any, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """List recent sessions for a user.

    Args:
        db: Firestore client
        user_id: User ID to check
        limit: Maximum sessions to return

    Returns:
        List of session data
    """
    print(f"\n{'=' * 60}")
    print(f"RECENT SESSIONS FOR USER: {user_id}")
    print(f"{'=' * 60}")

    query = (
        db.collection("sessions")
        .where("user_id", "==", user_id)
        .order_by("created_at", direction="DESCENDING")
        .limit(limit)
    )
    docs = query.stream()
    sessions = [{"id": doc.id, **doc.to_dict()} for doc in docs]

    if not sessions:
        print(f"[WARN] No sessions found for user {user_id}")
        return []

    print(f"Found {len(sessions)} session(s):\n")
    for session in sessions:
        status = session.get("status", "unknown")
        persona = session.get("selected_persona", "N/A")
        created = format_timestamp(session.get("created_at"))
        msg_count = session.get("message_count", 0)
        print(f"  {session['id']}")
        print(f"    Status: {status}, Persona: {persona}")
        print(f"    Created: {created}, Messages: {msg_count}")
        print()

    return sessions


def generate_verification_report(
    session_data: dict[str, Any] | None,
    messages: list[dict[str, Any]],
) -> dict[str, bool]:
    """Generate verification checklist.

    Args:
        session_data: Session document data
        messages: Transcript messages

    Returns:
        Dict of check name -> pass/fail
    """
    print(f"\n{'=' * 60}")
    print("VERIFICATION CHECKLIST")
    print(f"{'=' * 60}")

    checks = {
        "Session exists in Firestore": session_data is not None,
        "Session status is completed": (
            session_data.get("status") == "completed" if session_data else False
        ),
        "Session has user_id": bool(session_data.get("user_id")) if session_data else False,
        "Session has persona": bool(session_data.get("selected_persona"))
        if session_data
        else False,
        "Session has difficulty": bool(session_data.get("difficulty")) if session_data else False,
        "Session has timestamps": (
            session_data.get("started_at") is not None and session_data.get("ended_at") is not None
            if session_data
            else False
        ),
        "Session has duration": session_data.get("duration") is not None if session_data else False,
        "Agent state snapshot saved": bool(session_data.get("agent_state_snapshot"))
        if session_data
        else False,
        "Transcript messages exist": len(messages) > 0,
        "Has user messages": any(m.get("role") == "user" for m in messages),
        "Has assistant messages": any(m.get("role") == "assistant" for m in messages),
        "Messages have timestamps": all(m.get("timestamp") for m in messages),
    }

    passed = 0
    failed = 0

    for check, result in checks.items():
        icon = "[X]" if result else "[ ]"
        print(f"  {icon} {check}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n  Total: {passed}/{len(checks)} checks passed")

    return checks


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify E2E session persistence in Firestore")
    parser.add_argument(
        "--session-id",
        "-s",
        help="Session ID to verify",
    )
    parser.add_argument(
        "--user-id",
        "-u",
        help="User ID to list sessions for",
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("GCP_PROJECT_ID"),
        help="GCP project ID",
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("FIRESTORE_DATABASE", "(default)"),
        help="Firestore database ID",
    )

    args = parser.parse_args()

    if not args.session_id and not args.user_id:
        parser.error("Either --session-id or --user-id is required")

    if not args.project_id:
        print("Error: GCP_PROJECT_ID environment variable or --project-id required")
        return 1

    # Import Firestore client
    try:
        from google.cloud import firestore
    except ImportError:
        print("Error: google-cloud-firestore package not found")
        print("Install with: uv add google-cloud-firestore")
        return 1

    # Initialize Firestore
    try:
        db = firestore.Client(project=args.project_id, database=args.database)
        print(f"Connected to Firestore: {args.project_id}/{args.database}")
    except Exception as e:
        print(f"Error connecting to Firestore: {e}")
        print("Ensure GOOGLE_APPLICATION_CREDENTIALS is set")
        return 1

    if args.user_id:
        check_user_sessions(db, args.user_id)
        return 0

    if args.session_id:
        session_data = check_session(db, args.session_id)
        messages = check_transcript(db, args.session_id)
        checks = generate_verification_report(session_data, messages)

        # Return failure if critical checks failed
        critical = ["Session exists in Firestore", "Session status is completed"]
        if not all(checks.get(c, False) for c in critical):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
