#!/usr/bin/env python3
"""Verify Firestore connectivity and basic operations.

Usage:
    uv run python scripts/verify_firestore.py
"""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud.firestore import AsyncClient

from app.config import get_settings


async def verify_firestore() -> bool:
    """Verify Firestore connection with write/read/delete cycle.

    Returns:
        True if all operations succeed, False otherwise
    """
    settings = get_settings()

    if not settings.gcp_project_id:
        print("ERROR: GCP_PROJECT_ID not configured in .env")
        return False

    print("Connecting to Firestore...")
    print(f"  Project: {settings.gcp_project_id}")
    print(f"  Database: {settings.firestore_database}")

    try:
        db = AsyncClient(
            project=settings.gcp_project_id,
            database=settings.firestore_database,
        )

        # Test document reference
        test_doc = db.collection("_health").document("verification_test")

        # Write test
        print("\n1. Writing test document...")
        test_data = {
            "verified_at": datetime.now(UTC),
            "message": "Firestore connectivity verified",
        }
        await test_doc.set(test_data)
        print("   Write successful")

        # Read test
        print("2. Reading test document...")
        doc = await test_doc.get()
        if not doc.exists:
            print("   ERROR: Document not found after write")
            return False
        read_data = doc.to_dict()
        print(f"   Read successful: {read_data}")

        # Delete test
        print("3. Deleting test document...")
        await test_doc.delete()
        print("   Delete successful")

        # Verify deletion
        doc = await test_doc.get()
        if doc.exists:
            print("   WARNING: Document still exists after delete")
        else:
            print("   Verified deletion")

        print("\nFirestore connectivity verified successfully!")
        return True

    except Exception as e:
        print(f"\nERROR: Firestore operation failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure GCP_PROJECT_ID is set correctly in .env")
        print("  2. Run: gcloud auth application-default login")
        print("  3. Verify Firestore is enabled in your GCP project")
        return False


def main() -> None:
    """Run the verification."""
    success = asyncio.run(verify_firestore())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
