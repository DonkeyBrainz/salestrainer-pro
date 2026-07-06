"""Local smoke test for the RAG pipeline.

Tests each layer independently:
1. Objection detection (in-memory, no external deps)
2. embed_text (requires GEMINI_API_KEY)
3. RAG retrieve (requires Firestore + populated knowledge_chunks collection)
4. Conversation-aware query enhancement (requires GEMINI_API_KEY)
5. Full coach analysis with RAG context (requires all of the above)

Usage:
    cd backend
    uv run python scripts/test_rag_pipeline.py              # All tests
    uv run python scripts/test_rag_pipeline.py objections    # Objection tests only
    uv run python scripts/test_rag_pipeline.py embed         # Embedding test only
    uv run python scripts/test_rag_pipeline.py enhance       # Query enhancement only
    uv run python scripts/test_rag_pipeline.py retrieve      # RAG retrieval only
    uv run python scripts/test_rag_pipeline.py coach         # Coach analysis only
"""

import asyncio
import os
import sys

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_objections() -> None:
    """Test objection detection (no external deps)."""
    print("\n=== 1. Objection Detection ===")

    from app.services.objection_service import ObjectionLookupService

    service = ObjectionLookupService()

    test_cases = [
        ("That's way more than I wanted to spend.", "price"),
        ("I need to talk to my wife first.", "authority"),
        ("I need to think about it.", "timing"),
        ("I saw it cheaper at Rooms To Go.", "competition"),
        ("I'm not sure about the quality.", "trust"),
        ("I need to measure my space first.", "logistics"),
        ("This sofa looks really comfortable!", None),
        ("What colors does it come in?", None),
    ]

    passed = 0
    for msg, expected_category in test_cases:
        result = service.detect_objection(msg)
        actual = result["category"].value if result else None
        status = "PASS" if actual == expected_category else "FAIL"
        if status == "PASS":
            passed += 1
        print(f'  [{status}] "{msg[:50]}" -> {actual} (expected: {expected_category})')
        if result and status == "PASS":
            context = service.get_resolution_context(result)
            print(f"         Resolution: {context[:80]}...")

    print(f"\n  Results: {passed}/{len(test_cases)} passed")


async def test_embed() -> None:
    """Test embedding generation (requires GEMINI_API_KEY)."""
    print("\n=== 2. Embed Text ===")

    from app.config import get_settings

    settings = get_settings()
    if not settings.gemini_api_key:
        print("  [SKIP] GEMINI_API_KEY not set")
        return

    from unittest.mock import MagicMock

    from app.services.rag_service import FirestoreRAGService

    # Create service with a dummy db (we won't use it for embedding)
    service = FirestoreRAGService(db=MagicMock(), settings=settings)

    try:
        embedding = await service.embed_text("durable stain-resistant sectional sofa")
        print(f"  [PASS] Generated embedding: {len(embedding)} dimensions")
        print(f"         First 5 values: {embedding[:5]}")
    except Exception as e:
        print(f"  [FAIL] {e}")


async def test_enhance_query() -> None:
    """Test conversation-aware query enhancement (requires GEMINI_API_KEY)."""
    print("\n=== 3. Query Enhancement ===")

    from app.config import get_settings

    settings = get_settings()
    if not settings.gemini_api_key:
        print("  [SKIP] GEMINI_API_KEY not set")
        return

    from unittest.mock import MagicMock

    from app.services.rag_service import FirestoreRAGService

    service = FirestoreRAGService(db=MagicMock(), settings=settings)

    history = [
        ("user", "Hi, I'm looking for a new sofa for my living room"),
        ("assistant", "Welcome! What's important to you in a sofa?"),
        ("user", "I have two kids and a dog, so it needs to handle a lot"),
        ("assistant", "Durability is key then! Let me show you some options."),
    ]

    original = "Is it stain resistant?"
    try:
        enhanced = await service.enhance_query(original, history)
        print(f'  [PASS] Original:  "{original}"')
        print(f'         Enhanced:  "{enhanced}"')
    except Exception as e:
        print(f"  [FAIL] {e}")


async def test_retrieve() -> None:
    """Test RAG retrieval from Firestore (requires populated knowledge_chunks)."""
    print("\n=== 4. RAG Retrieval ===")

    from app.config import get_settings

    settings = get_settings()
    if not settings.gemini_api_key:
        print("  [SKIP] GEMINI_API_KEY not set")
        return

    try:
        from google.cloud.firestore import AsyncClient

        db = AsyncClient(
            project=settings.gcp_project_id,
            database=settings.firestore_database,
        )
    except Exception as e:
        print(f"  [SKIP] Cannot connect to Firestore: {e}")
        return

    from app.services.rag_service import FirestoreRAGService

    service = FirestoreRAGService(db=db, settings=settings)

    # Check if knowledge_chunks collection has data
    try:
        docs = await db.collection(settings.rag_collection_name).limit(1).get()
        if not docs:
            print(f"  [SKIP] No documents in '{settings.rag_collection_name}' collection")
            print("         Populate the collection first, then re-run this test")
            return
        print(f"  Collection '{settings.rag_collection_name}' has data")
    except Exception as e:
        print(f"  [SKIP] Cannot read collection: {e}")
        return

    queries = [
        "Is the sectional stain resistant?",
        "Tell me about the warranty",
        "What payment options do you offer?",
    ]

    for query in queries:
        try:
            result = await service.retrieve(query=query, top_k=2)
            if result:
                preview = result[:120].replace("\n", " ")
                print(f'  [PASS] "{query}"')
                print(f"         -> {preview}...")
            else:
                print(f'  [WARN] "{query}" -> No results')
        except Exception as e:
            print(f'  [FAIL] "{query}" -> {e}')


async def test_coach_analysis() -> None:
    """Test coach analysis with RAG context (full pipeline)."""
    print("\n=== 5. Coach Analysis with RAG ===")

    from app.config import get_settings

    settings = get_settings()
    if not settings.gemini_api_key:
        print("  [SKIP] GEMINI_API_KEY not set")
        return

    from langchain_core.messages import AIMessage, HumanMessage

    from app.agents.coach.analyzer import CoachAnalyzer
    from app.agents.personas import BUSY_PARENT
    from app.agents.state import CoreStageProgress, SalesStage
    from app.services.objection_service import init_objection_service

    # Init objection service (normally done at startup)
    init_objection_service()

    analyzer = CoachAnalyzer()

    messages = [
        HumanMessage(content="Hi there! Beautiful day outside, isn't it?"),
        AIMessage(content="Yeah it's nice. I'm looking for a new sofa."),
        HumanMessage(content="Great! What room is it for?"),
        AIMessage(content="Living room. But honestly, that's more than I wanted to spend."),
    ]

    progress = CoreStageProgress(
        current_stage=SalesStage.ASK,
        engage={
            "non_business_greet": True,
            "established_rapport": True,
            "manager_mention": False,
        },
    )

    try:
        result = await analyzer.analyze(
            salesperson_message="I completely understand. Let me show you our payment options.",
            messages=messages,
            persona=BUSY_PARENT,
            stage_progress=progress,
        )

        print("  [PASS] Analysis completed:")
        print(f"         Techniques: {result.techniques_detected}")
        print(f"         Deviations: {result.deviations}")
        print(f"         Intervention: {result.intervention_level.value}")
        if result.hint:
            print(f"         Hint: {result.hint[:100]}")
        if result.example_phrase:
            print(f"         Example: {result.example_phrase[:100]}")
    except Exception as e:
        print(f"  [FAIL] {e}")


async def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    print("RAG Pipeline Local Smoke Test")
    print("=" * 50)

    if target in ("all", "objections"):
        test_objections()

    if target in ("all", "embed"):
        await test_embed()

    if target in ("all", "enhance"):
        await test_enhance_query()

    if target in ("all", "retrieve"):
        await test_retrieve()

    if target in ("all", "coach"):
        await test_coach_analysis()

    print("\n" + "=" * 50)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
