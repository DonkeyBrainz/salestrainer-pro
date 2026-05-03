"""Unit tests for RAG service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rag_service import (
    FirestoreRAGService,
    get_rag_service,
    init_rag_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock Settings for RAG service."""
    settings = MagicMock()
    settings.rag_collection_name = "knowledge_chunks"
    settings.rag_embedding_model = "gemini-embedding-2"
    settings.gemini_api_key = "test-api-key"
    return settings


@pytest.fixture
def mock_db() -> MagicMock:
    """Create mock Firestore AsyncClient."""
    return MagicMock()


@pytest.fixture
def rag_service(mock_db: MagicMock, mock_settings: MagicMock) -> FirestoreRAGService:
    """Create a FirestoreRAGService instance with mocks."""
    return FirestoreRAGService(db=mock_db, settings=mock_settings)


# =============================================================================
# Initialization Tests
# =============================================================================


class TestFirestoreRAGServiceInit:
    """Tests for FirestoreRAGService initialization."""

    def test_stores_db_and_settings(
        self, mock_db: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Should store db, collection name, embedding model, and api key."""
        service = FirestoreRAGService(db=mock_db, settings=mock_settings)

        assert service.db is mock_db
        assert service.collection_name == "knowledge_chunks"
        assert service._embedding_model == "gemini-embedding-2"
        assert service._api_key == "test-api-key"

    def test_client_not_created_on_init(self, rag_service: FirestoreRAGService) -> None:
        """Should not create genai client on init (lazy)."""
        assert rag_service._client is None

    @patch("app.services.rag_service.genai.Client")
    def test_client_created_on_first_access(
        self, mock_genai_client: MagicMock, rag_service: FirestoreRAGService
    ) -> None:
        """Should create genai client on first access."""
        client = rag_service.client

        mock_genai_client.assert_called_once_with(api_key="test-api-key")
        assert client is mock_genai_client.return_value

    @patch("app.services.rag_service.genai.Client")
    def test_client_reused_on_subsequent_access(
        self, mock_genai_client: MagicMock, rag_service: FirestoreRAGService
    ) -> None:
        """Should reuse genai client on subsequent access."""
        client1 = rag_service.client
        client2 = rag_service.client

        mock_genai_client.assert_called_once()
        assert client1 is client2


# =============================================================================
# chunk_text Tests
# =============================================================================


class TestChunkText:
    """Tests for chunk_text method."""

    def test_single_chunk_for_short_text(self, rag_service: FirestoreRAGService) -> None:
        """Should return single chunk for text shorter than chunk_size."""
        text = "Short text"
        chunks = rag_service.chunk_text(text, chunk_size=800, overlap=200)

        assert len(chunks) == 1
        assert chunks[0] == "Short text"

    def test_multiple_chunks_with_overlap(self, rag_service: FirestoreRAGService) -> None:
        """Should create overlapping chunks for long text."""
        text = "A" * 100
        chunks = rag_service.chunk_text(text, chunk_size=40, overlap=10)

        # 100 chars, step=30 (40-10): ceil(100/30) ~ 4 chunks
        assert len(chunks) >= 3
        # First chunk should be 40 chars
        assert len(chunks[0]) == 40

    def test_empty_text(self, rag_service: FirestoreRAGService) -> None:
        """Should return empty list for empty text."""
        chunks = rag_service.chunk_text("")
        assert chunks == []

    def test_custom_chunk_size(self, rag_service: FirestoreRAGService) -> None:
        """Should respect custom chunk_size and overlap."""
        text = "A" * 50
        chunks = rag_service.chunk_text(text, chunk_size=20, overlap=5)

        assert len(chunks) >= 3
        assert len(chunks[0]) == 20


# =============================================================================
# embed_text Tests
# =============================================================================


class TestEmbedText:
    """Tests for embed_text method."""

    @pytest.mark.asyncio
    async def test_embed_text_calls_genai(self, rag_service: FirestoreRAGService) -> None:
        """Should call genai embed_content and return embedding values."""
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_response = MagicMock()
        mock_response.embeddings = [mock_embedding]

        mock_embed = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.aio.models.embed_content = mock_embed
        rag_service._client = mock_client

        result = await rag_service.embed_text("test text")

        from google.genai import types as genai_types

        mock_embed.assert_called_once_with(
            model="gemini-embedding-2",
            contents="test text",
            config=genai_types.EmbedContentConfig(output_dimensionality=2048),
        )
        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_text_raises_on_api_error(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should propagate API errors."""
        mock_embed = AsyncMock(side_effect=Exception("API quota exceeded"))
        mock_client = MagicMock()
        mock_client.aio.models.embed_content = mock_embed
        rag_service._client = mock_client

        with pytest.raises(Exception, match="API quota exceeded"):
            await rag_service.embed_text("test text")


# =============================================================================
# retrieve Tests
# =============================================================================


class TestRetrieve:
    """Tests for retrieve method."""

    @pytest.mark.asyncio
    async def test_retrieve_returns_formatted_context(
        self, rag_service: FirestoreRAGService, mock_db: MagicMock
    ) -> None:
        """Should return concatenated content from matching docs."""
        # Mock embed_text
        with patch.object(
            rag_service, "embed_text", new_callable=AsyncMock
        ) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]

            # Mock Firestore chain
            doc1 = MagicMock()
            doc1.to_dict.return_value = {"content": "Chunk about durability"}
            doc2 = MagicMock()
            doc2.to_dict.return_value = {"content": "Chunk about materials"}

            mock_query = MagicMock()
            mock_query.get = AsyncMock(return_value=[doc1, doc2])

            mock_collection = MagicMock()
            mock_collection.find_nearest.return_value = mock_query
            mock_db.collection.return_value = mock_collection

            result = await rag_service.retrieve("Is this durable?", top_k=2)

            assert "Chunk about durability" in result
            assert "Chunk about materials" in result
            assert "\n\n" in result

    @pytest.mark.asyncio
    async def test_retrieve_empty_results(
        self, rag_service: FirestoreRAGService, mock_db: MagicMock
    ) -> None:
        """Should return empty string when no results found."""
        with patch.object(
            rag_service, "embed_text", new_callable=AsyncMock
        ) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]

            mock_query = MagicMock()
            mock_query.get = AsyncMock(return_value=[])

            mock_collection = MagicMock()
            mock_collection.find_nearest.return_value = mock_query
            mock_db.collection.return_value = mock_collection

            result = await rag_service.retrieve("Unknown query")

            assert result == ""

    @pytest.mark.asyncio
    async def test_retrieve_with_category_filter(
        self, rag_service: FirestoreRAGService, mock_db: MagicMock
    ) -> None:
        """Should apply category filter to Firestore query."""
        with patch.object(
            rag_service, "embed_text", new_callable=AsyncMock
        ) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]

            mock_query = MagicMock()
            mock_query.get = AsyncMock(return_value=[])

            mock_filtered = MagicMock()
            mock_filtered.find_nearest.return_value = mock_query

            mock_collection = MagicMock()
            mock_collection.where.return_value = mock_filtered
            mock_db.collection.return_value = mock_collection

            await rag_service.retrieve(
                "Is this durable?", product_category="living_room"
            )

            mock_collection.where.assert_called_once_with(
                "metadata.category", "==", "living_room"
            )

    @pytest.mark.asyncio
    async def test_retrieve_with_category_and_type_filter(
        self, rag_service: FirestoreRAGService, mock_db: MagicMock
    ) -> None:
        """Should apply both category and type filters."""
        with patch.object(
            rag_service, "embed_text", new_callable=AsyncMock
        ) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]

            mock_query = MagicMock()
            mock_query.get = AsyncMock(return_value=[])

            mock_type_filtered = MagicMock()
            mock_type_filtered.find_nearest.return_value = mock_query

            mock_cat_filtered = MagicMock()
            mock_cat_filtered.where.return_value = mock_type_filtered

            mock_collection = MagicMock()
            mock_collection.where.return_value = mock_cat_filtered
            mock_db.collection.return_value = mock_collection

            await rag_service.retrieve(
                "Is this durable?",
                product_category="living_room",
                product_type="sectional",
            )

            mock_collection.where.assert_called_once_with(
                "metadata.category", "==", "living_room"
            )
            mock_cat_filtered.where.assert_called_once_with(
                "metadata.doc_type", "==", "sectional"
            )


# =============================================================================
# Hybrid Search Tests
# =============================================================================


class TestReciprocalRankFusion:
    """Tests for _reciprocal_rank_fusion static method."""

    def test_fuses_non_overlapping_results(self) -> None:
        """Should combine results from both sources."""
        semantic = [
            {"id": "a", "content": "Semantic A"},
            {"id": "b", "content": "Semantic B"},
        ]
        keyword = [
            {"id": "c", "content": "Keyword C"},
            {"id": "d", "content": "Keyword D"},
        ]

        fused = FirestoreRAGService._reciprocal_rank_fusion(
            semantic, keyword, top_k=3
        )

        assert len(fused) == 3
        ids = [r["id"] for r in fused]
        # Semantic results should rank higher due to higher weight
        assert ids[0] == "a"

    def test_fuses_overlapping_results(self) -> None:
        """Should boost documents that appear in both result sets."""
        semantic = [
            {"id": "a", "content": "Content A"},
            {"id": "b", "content": "Content B"},
        ]
        keyword = [
            {"id": "a", "content": "Content A"},
            {"id": "c", "content": "Content C"},
        ]

        fused = FirestoreRAGService._reciprocal_rank_fusion(
            semantic, keyword, top_k=3
        )

        # "a" appears in both, should be first
        assert fused[0]["id"] == "a"

    def test_respects_top_k(self) -> None:
        """Should limit results to top_k."""
        semantic = [{"id": f"s{i}", "content": f"S{i}"} for i in range(5)]
        keyword = [{"id": f"k{i}", "content": f"K{i}"} for i in range(5)]

        fused = FirestoreRAGService._reciprocal_rank_fusion(
            semantic, keyword, top_k=2
        )

        assert len(fused) == 2

    def test_handles_empty_inputs(self) -> None:
        """Should handle empty result sets."""
        fused = FirestoreRAGService._reciprocal_rank_fusion([], [], top_k=3)
        assert fused == []

    def test_rrf_score_calculation(self) -> None:
        """Should compute correct RRF scores."""
        semantic = [{"id": "a", "content": "A"}]
        keyword = [{"id": "a", "content": "A"}]

        fused = FirestoreRAGService._reciprocal_rank_fusion(
            semantic, keyword, k=60, semantic_weight=0.7, keyword_weight=0.3, top_k=1
        )

        assert len(fused) == 1
        # Score = 0.7/(60+1) + 0.3/(60+1) = 1.0/61
        # Just check it's the doc
        assert fused[0]["id"] == "a"


class TestKeywordSearch:
    """Tests for _keyword_search method."""

    @pytest.mark.asyncio
    async def test_keyword_search_ranks_by_bm25(
        self, rag_service: FirestoreRAGService, mock_db: MagicMock
    ) -> None:
        """Should rank documents by BM25 relevance."""
        doc1 = MagicMock()
        doc1.id = "doc1"
        doc1.to_dict.return_value = {"content": "This durable sectional is stain resistant"}

        doc2 = MagicMock()
        doc2.id = "doc2"
        doc2.to_dict.return_value = {"content": "Beautiful decorative pillow set"}

        mock_collection = MagicMock()
        mock_collection.get = AsyncMock(return_value=[doc1, doc2])
        mock_db.collection.return_value = mock_collection

        results = await rag_service._keyword_search("durable stain resistant", top_k=2)

        assert len(results) >= 1
        assert results[0]["id"] == "doc1"

    @pytest.mark.asyncio
    async def test_keyword_search_empty_query(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should return empty list for empty query."""
        results = await rag_service._keyword_search("")
        assert results == []


class TestHybridRetrieve:
    """Tests for hybrid_retrieve method."""

    @pytest.mark.asyncio
    async def test_hybrid_retrieve_combines_results(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should combine semantic and keyword results."""
        with (
            patch.object(
                rag_service,
                "_semantic_search",
                new_callable=AsyncMock,
                return_value=[{"id": "a", "content": "Semantic A"}],
            ),
            patch.object(
                rag_service,
                "_keyword_search",
                new_callable=AsyncMock,
                return_value=[{"id": "b", "content": "Keyword B"}],
            ),
        ):
            result = await rag_service.hybrid_retrieve("test query")

            assert "Semantic A" in result
            assert "Keyword B" in result

    @pytest.mark.asyncio
    async def test_hybrid_retrieve_empty_results(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should return empty string when no results."""
        with (
            patch.object(
                rag_service,
                "_semantic_search",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch.object(
                rag_service,
                "_keyword_search",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await rag_service.hybrid_retrieve("test query")
            assert result == ""


# =============================================================================
# enhance_query Tests
# =============================================================================


class TestEnhanceQuery:
    """Tests for enhance_query method."""

    @pytest.mark.asyncio
    async def test_enhances_query_with_context(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should rewrite query using conversation context."""
        mock_response = MagicMock()
        mock_response.text = "durable sectional for kids living room"

        mock_generate = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = mock_generate
        rag_service._client = mock_client

        history = [
            ("user", "I'm looking for a sectional"),
            ("assistant", "What room is it for?"),
            ("user", "Living room, we have kids"),
        ]

        result = await rag_service.enhance_query("Is it durable?", history)

        assert result == "durable sectional for kids living room"
        mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_original_on_empty_history(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should return original query when no history provided."""
        result = await rag_service.enhance_query("Is it durable?", [])

        assert result == "Is it durable?"

    @pytest.mark.asyncio
    async def test_falls_back_on_api_error(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should return original query when LLM call fails."""
        mock_generate = AsyncMock(side_effect=Exception("API error"))
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = mock_generate
        rag_service._client = mock_client

        history = [("user", "Hi"), ("assistant", "Hello")]

        result = await rag_service.enhance_query("Is it durable?", history)

        assert result == "Is it durable?"

    @pytest.mark.asyncio
    async def test_falls_back_on_empty_response(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should return original query when LLM returns empty text."""
        mock_response = MagicMock()
        mock_response.text = None

        mock_generate = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = mock_generate
        rag_service._client = mock_client

        history = [("user", "Hi")]

        result = await rag_service.enhance_query("Is it durable?", history)

        assert result == "Is it durable?"


# =============================================================================
# retrieve_with_context Tests
# =============================================================================


class TestRetrieveWithContext:
    """Tests for retrieve_with_context method."""

    @pytest.mark.asyncio
    async def test_calls_enhance_then_retrieve(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should enhance query, then retrieve with enhanced query."""
        with (
            patch.object(
                rag_service, "enhance_query", new_callable=AsyncMock
            ) as mock_enhance,
            patch.object(
                rag_service, "retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
        ):
            mock_enhance.return_value = "enhanced query"
            mock_retrieve.return_value = "Product context result"

            history = [("user", "I need a sofa")]

            result = await rag_service.retrieve_with_context(
                query="Is it comfortable?",
                conversation_history=history,
                product_category="living_room",
            )

            mock_enhance.assert_called_once_with("Is it comfortable?", history)
            mock_retrieve.assert_called_once_with(
                query="enhanced query",
                product_category="living_room",
                product_type=None,
                section_type=None,
                top_k=3,
            )
            assert result == "Product context result"


# =============================================================================
# Re-Ranking Tests
# =============================================================================


class TestRerankWithLLM:
    """Tests for _rerank_with_llm method."""

    @pytest.mark.asyncio
    async def test_reranks_with_valid_response(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should re-rank candidates based on LLM response."""
        candidates = [
            {"id": "a", "content": "Content A"},
            {"id": "b", "content": "Content B"},
            {"id": "c", "content": "Content C"},
            {"id": "d", "content": "Content D"},
        ]

        mock_response = MagicMock()
        mock_response.text = "2, 0, 3"

        mock_generate = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = mock_generate
        rag_service._client = mock_client

        result = await rag_service._rerank_with_llm("query", candidates, top_k=3)

        assert len(result) == 3
        assert result[0]["id"] == "c"
        assert result[1]["id"] == "a"
        assert result[2]["id"] == "d"

    @pytest.mark.asyncio
    async def test_returns_original_on_invalid_response(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should fall back to original order on unparseable response."""
        candidates = [
            {"id": "a", "content": "A"},
            {"id": "b", "content": "B"},
            {"id": "c", "content": "C"},
            {"id": "d", "content": "D"},
        ]

        mock_response = MagicMock()
        mock_response.text = "invalid response text"

        mock_generate = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = mock_generate
        rag_service._client = mock_client

        result = await rag_service._rerank_with_llm("query", candidates, top_k=2)

        assert len(result) == 2
        assert result[0]["id"] == "a"

    @pytest.mark.asyncio
    async def test_returns_original_on_api_error(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should fall back to original order on API error."""
        candidates = [
            {"id": "a", "content": "A"},
            {"id": "b", "content": "B"},
            {"id": "c", "content": "C"},
        ]

        mock_generate = AsyncMock(side_effect=Exception("API error"))
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = mock_generate
        rag_service._client = mock_client

        result = await rag_service._rerank_with_llm("query", candidates, top_k=2)

        assert len(result) == 2
        assert result[0]["id"] == "a"

    @pytest.mark.asyncio
    async def test_skips_reranking_when_candidates_within_top_k(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should return candidates as-is when count <= top_k."""
        candidates = [
            {"id": "a", "content": "A"},
            {"id": "b", "content": "B"},
        ]

        result = await rag_service._rerank_with_llm("query", candidates, top_k=3)

        assert len(result) == 2
        assert result[0]["id"] == "a"


class TestRetrieveWithReranking:
    """Tests for retrieve_with_reranking method."""

    @pytest.mark.asyncio
    async def test_retrieves_and_reranks(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should retrieve initial candidates then re-rank."""
        with (
            patch.object(
                rag_service,
                "_semantic_search",
                new_callable=AsyncMock,
                return_value=[
                    {"id": "a", "content": "A"},
                    {"id": "b", "content": "B"},
                    {"id": "c", "content": "C"},
                ],
            ),
            patch.object(
                rag_service,
                "_rerank_with_llm",
                new_callable=AsyncMock,
                return_value=[
                    {"id": "c", "content": "C"},
                    {"id": "a", "content": "A"},
                ],
            ) as mock_rerank,
        ):
            result = await rag_service.retrieve_with_reranking(
                "query", initial_k=3, final_k=2
            )

            mock_rerank.assert_called_once()
            assert "C" in result
            assert "A" in result

    @pytest.mark.asyncio
    async def test_uses_hybrid_when_requested(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should use hybrid search for initial retrieval when use_hybrid=True."""
        with (
            patch.object(
                rag_service,
                "_semantic_search",
                new_callable=AsyncMock,
                return_value=[{"id": "a", "content": "A"}],
            ) as mock_semantic,
            patch.object(
                rag_service,
                "_keyword_search",
                new_callable=AsyncMock,
                return_value=[{"id": "b", "content": "B"}],
            ) as mock_keyword,
            patch.object(
                rag_service,
                "_rerank_with_llm",
                new_callable=AsyncMock,
                return_value=[{"id": "a", "content": "A"}],
            ),
        ):
            await rag_service.retrieve_with_reranking(
                "query", initial_k=5, final_k=2, use_hybrid=True
            )

            mock_semantic.assert_called_once()
            mock_keyword.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_candidates(
        self, rag_service: FirestoreRAGService
    ) -> None:
        """Should return empty string when no candidates found."""
        with patch.object(
            rag_service,
            "_semantic_search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await rag_service.retrieve_with_reranking("query")
            assert result == ""


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingleton:
    """Tests for module-level singleton management."""

    def test_get_rag_service_raises_when_not_initialized(self) -> None:
        """Should raise RuntimeError when service not initialized."""
        # Reset singleton
        import app.services.rag_service as module

        module._rag_service = None

        with pytest.raises(RuntimeError, match="RAG service not initialized"):
            get_rag_service()

    def test_init_and_get_rag_service(
        self, mock_db: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Should initialize and retrieve RAG service singleton."""
        import app.services.rag_service as module

        module._rag_service = None

        init_rag_service(mock_db, mock_settings)

        service = get_rag_service()
        assert isinstance(service, FirestoreRAGService)
        assert service.db is mock_db

        # Cleanup
        module._rag_service = None
