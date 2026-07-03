"""RAG (Retrieval-Augmented Generation) service for product knowledge retrieval.

This service handles vector search in Firestore to retrieve relevant product
knowledge chunks that help the coach agent provide accurate, product-specific hints.
"""

import asyncio
import logging
import math
import re
from typing import Any, Protocol

from google import genai
from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.genai import types

from app.config import Settings

logger = logging.getLogger(__name__)


class RAGService(Protocol):
    """Protocol for RAG service interface."""

    async def retrieve(
        self,
        query: str,
        product_category: str | None = None,
        product_type: str | None = None,
        section_type: str | None = None,
        top_k: int = 3,
    ) -> str:
        """Retrieve relevant product context from vector search."""
        ...


class FirestoreRAGService:
    """RAG service using Firestore vector search with metadata filtering."""

    def __init__(self, db: firestore.AsyncClient, settings: Settings) -> None:
        """Initialize RAG service.

        Args:
            db: Async Firestore client instance
            settings: Application settings for API key and model config
        """
        self.db = db
        self.collection_name = settings.rag_collection_name
        self._embedding_model = settings.rag_embedding_model
        self._api_key = settings.gemini_api_key
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        """Get or create the Gemini client (lazy initialization)."""
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks for embedding.

        Args:
            text: Text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Number of overlapping characters between chunks

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for text using Gemini embedding model.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            Exception: If the embedding API call fails
        """
        response = await self.client.aio.models.embed_content(
            model=self._embedding_model,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=2048),
        )
        if not response.embeddings:
            raise ValueError("No embeddings returned from API")
        values = response.embeddings[0].values
        if values is None:
            raise ValueError("Embedding values are None")
        return list(values)

    async def retrieve(
        self,
        query: str,
        product_category: str | None = None,
        product_type: str | None = None,
        section_type: str | None = None,
        top_k: int = 3,
    ) -> str:
        """Retrieve relevant product context with metadata filtering.

        Args:
            query: The search query (e.g., "Is this durable for kids?")
            product_category: Filter by category (e.g., "property_1", "calden")
            product_type: Filter by doc type (e.g., "training_guide", "property_listing")
            section_type: Filter by section type for property chunks
                          (e.g., "objection_handlers", "neighborhood_profile")
            top_k: Number of results to retrieve

        Returns:
            Concatenated context string from top-k relevant chunks
        """
        query_embedding = await self.embed_text(query)

        collection_ref = self.db.collection(self.collection_name)

        if product_category:
            collection_ref = collection_ref.where("metadata.category", "==", product_category)

        if product_type:
            collection_ref = collection_ref.where("metadata.doc_type", "==", product_type)

        if section_type:
            collection_ref = collection_ref.where("metadata.section_type", "==", section_type)

        results = await collection_ref.find_nearest(
            vector_field="embedding",
            query_vector=query_embedding,
            distance_measure=DistanceMeasure.COSINE,
            limit=top_k,
        ).get()

        if not results:
            return ""

        context_chunks = [doc.to_dict()["content"] for doc in results]
        return "\n\n".join(context_chunks)

    async def _semantic_search(
        self,
        query: str,
        product_category: str | None = None,
        product_type: str | None = None,
        section_type: str | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Perform vector-based semantic search.

        Args:
            query: Search query text
            product_category: Optional category filter
            product_type: Optional doc_type filter
            section_type: Optional section_type filter for property chunks
            top_k: Number of results

        Returns:
            List of dicts with 'id' and 'content' keys
        """
        query_embedding = await self.embed_text(query)

        collection_ref = self.db.collection(self.collection_name)

        if product_category:
            collection_ref = collection_ref.where("metadata.category", "==", product_category)
        if product_type:
            collection_ref = collection_ref.where("metadata.doc_type", "==", product_type)
        if section_type:
            collection_ref = collection_ref.where("metadata.section_type", "==", section_type)

        results = await collection_ref.find_nearest(
            vector_field="embedding",
            query_vector=query_embedding,
            distance_measure=DistanceMeasure.COSINE,
            limit=top_k,
        ).get()

        return [{"id": doc.id, "content": doc.to_dict()["content"]} for doc in results]

    async def _keyword_search(
        self,
        query: str,
        product_category: str | None = None,
        product_type: str | None = None,
        section_type: str | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Perform in-memory BM25-style keyword search.

        Fetches category-filtered chunks from Firestore and ranks by
        term frequency. Assumes small collection (< 1000 docs).

        Args:
            query: Search query text
            product_category: Optional category filter
            product_type: Optional doc_type filter
            section_type: Optional section_type filter for property chunks
            top_k: Number of results

        Returns:
            List of dicts with 'id' and 'content' keys, ranked by BM25
        """
        query_tokens = set(re.findall(r"[a-z]+", query.lower()))
        if not query_tokens:
            return []

        collection_ref = self.db.collection(self.collection_name)

        if product_category:
            collection_ref = collection_ref.where("metadata.category", "==", product_category)
        if product_type:
            collection_ref = collection_ref.where("metadata.doc_type", "==", product_type)
        if section_type:
            collection_ref = collection_ref.where("metadata.section_type", "==", section_type)

        docs = await collection_ref.get()
        if not docs:
            return []

        # BM25 scoring parameters
        k1 = 1.2
        b = 0.75
        num_docs = len(docs)
        avg_dl = sum(len(doc.to_dict()["content"].split()) for doc in docs) / num_docs

        # Count document frequency for each query term
        doc_freq: dict[str, int] = {}
        for token in query_tokens:
            doc_freq[token] = sum(1 for doc in docs if token in doc.to_dict()["content"].lower())

        scored: list[tuple[float, dict[str, Any]]] = []
        for doc in docs:
            content = doc.to_dict()["content"]
            content_lower = content.lower()
            doc_len = len(content.split())
            score = 0.0

            for token in query_tokens:
                tf = content_lower.count(token)
                df = doc_freq.get(token, 0)
                if df == 0:
                    continue
                idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1)
                tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_dl))
                score += idf * tf_norm

            scored.append((score, {"id": doc.id, "content": content}))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    @staticmethod
    def _reciprocal_rank_fusion(
        semantic_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        k: int = 60,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Combine semantic and keyword results using Reciprocal Rank Fusion.

        Args:
            semantic_results: Results from vector search
            keyword_results: Results from keyword search
            k: RRF smoothing constant (default 60)
            semantic_weight: Weight for semantic results
            keyword_weight: Weight for keyword results
            top_k: Number of fused results to return

        Returns:
            Fused and re-ranked results
        """
        scores: dict[str, float] = {}
        content_map: dict[str, str] = {}

        for rank, result in enumerate(semantic_results):
            doc_id = result["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + semantic_weight / (k + rank + 1)
            content_map[doc_id] = result["content"]

        for rank, result in enumerate(keyword_results):
            doc_id = result["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + keyword_weight / (k + rank + 1)
            content_map[doc_id] = result["content"]

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [{"id": doc_id, "content": content_map[doc_id]} for doc_id, _ in ranked[:top_k]]

    async def hybrid_retrieve(
        self,
        query: str,
        product_category: str | None = None,
        product_type: str | None = None,
        section_type: str | None = None,
        top_k: int = 3,
    ) -> str:
        """Retrieve using hybrid search (semantic + keyword with RRF fusion).

        Runs semantic and keyword search in parallel, then fuses results
        using Reciprocal Rank Fusion.

        Args:
            query: Search query text
            product_category: Optional category filter
            product_type: Optional doc_type filter
            section_type: Optional section_type filter for property chunks
            top_k: Number of results

        Returns:
            Concatenated context string from fused results
        """
        semantic_results, keyword_results = await asyncio.gather(
            self._semantic_search(query, product_category, product_type, section_type, top_k),
            self._keyword_search(query, product_category, product_type, section_type, top_k),
        )

        fused = self._reciprocal_rank_fusion(semantic_results, keyword_results, top_k=top_k)

        if not fused:
            return ""

        return "\n\n".join(r["content"] for r in fused)

    async def enhance_query(
        self,
        query: str,
        conversation_history: list[tuple[str, str]],
        max_history: int = 5,
    ) -> str:
        """Rewrite a RAG query using conversation context for better retrieval.

        Uses Gemini Flash to produce a standalone search query that incorporates
        context from prior conversation turns.

        Args:
            query: The current salesperson message
            conversation_history: List of (role, content) tuples
            max_history: Maximum conversation turns to include

        Returns:
            Enhanced query string, or original query on failure
        """
        if not conversation_history:
            return query

        recent = conversation_history[-max_history:]
        history_text = "\n".join(f"{role}: {content}" for role, content in recent)

        prompt = (
            "Rewrite the following message as a standalone product search query, "
            "incorporating relevant context from the conversation.\n\n"
            f"Conversation:\n{history_text}\n\n"
            f"Current message: {query}\n\n"
            "Rewritten search query:"
        )

        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=100,
                ),
            )
            if response.text:
                return response.text.strip()
            return query
        except Exception as e:
            logger.warning(f"Query enhancement failed, using original: {e}")
            return query

    async def retrieve_with_context(
        self,
        query: str,
        conversation_history: list[tuple[str, str]],
        product_category: str | None = None,
        product_type: str | None = None,
        section_type: str | None = None,
        top_k: int = 3,
    ) -> str:
        """Retrieve with conversation-aware query enhancement.

        Enhances the query using conversation context before retrieval.

        Args:
            query: The salesperson message
            conversation_history: List of (role, content) tuples
            product_category: Optional category filter
            product_type: Optional doc_type filter
            section_type: Optional section_type filter for property chunks
            top_k: Number of results to retrieve

        Returns:
            Concatenated context string from top-k relevant chunks
        """
        enhanced = await self.enhance_query(query, conversation_history)
        return await self.retrieve(
            query=enhanced,
            product_category=product_category,
            product_type=product_type,
            section_type=section_type,
            top_k=top_k,
        )

    async def _rerank_with_llm(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        model: str = "gemini-2.5-flash",
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Re-rank candidate chunks using Gemini Flash.

        Asks the LLM to select the most relevant chunks by index.
        Falls back to original order on parse or API error.

        Args:
            query: The search query
            candidates: List of candidate dicts with 'id' and 'content'
            model: Gemini model for re-ranking
            top_k: Number of top results to return

        Returns:
            Re-ranked candidates, reduced to top_k
        """
        if len(candidates) <= top_k:
            return candidates

        numbered = "\n".join(f"[{i}] {c['content'][:200]}" for i, c in enumerate(candidates))

        prompt = (
            f'Given the query: "{query}"\n\n'
            f"Rank these document chunks by relevance. "
            f"Return ONLY the indices of the top {top_k} most relevant chunks "
            f"as comma-separated numbers (e.g., 2,0,4).\n\n"
            f"{numbered}"
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=50,
                ),
            )
            if not response.text:
                return candidates[:top_k]

            # Parse comma-separated indices
            indices = []
            for part in response.text.strip().split(","):
                part = part.strip()
                if part.isdigit():
                    idx = int(part)
                    if 0 <= idx < len(candidates) and idx not in indices:
                        indices.append(idx)

            if not indices:
                return candidates[:top_k]

            return [candidates[i] for i in indices[:top_k]]

        except Exception as e:
            logger.warning(f"LLM re-ranking failed, using original order: {e}")
            return candidates[:top_k]

    async def retrieve_with_reranking(
        self,
        query: str,
        product_category: str | None = None,
        product_type: str | None = None,
        section_type: str | None = None,
        initial_k: int = 10,
        final_k: int = 3,
        use_hybrid: bool = False,
        reranking_model: str = "gemini-2.5-flash",
    ) -> str:
        """Retrieve with LLM re-ranking as the final precision layer.

        Retrieves initial_k candidates (via hybrid or semantic search),
        then re-ranks to final_k using Gemini Flash.

        Args:
            query: Search query
            product_category: Optional category filter
            product_type: Optional doc_type filter
            section_type: Optional section_type filter for property chunks
            initial_k: Number of candidates to retrieve before re-ranking
            final_k: Number of results after re-ranking
            use_hybrid: Whether to use hybrid search for initial retrieval
            reranking_model: Gemini model for re-ranking

        Returns:
            Concatenated context string from re-ranked results
        """
        # Get initial candidates
        if use_hybrid:
            semantic_results, keyword_results = await asyncio.gather(
                self._semantic_search(
                    query, product_category, product_type, section_type, initial_k
                ),
                self._keyword_search(
                    query, product_category, product_type, section_type, initial_k
                ),
            )
            candidates = self._reciprocal_rank_fusion(
                semantic_results, keyword_results, top_k=initial_k
            )
        else:
            candidates = await self._semantic_search(
                query, product_category, product_type, section_type, initial_k
            )

        if not candidates:
            return ""

        # Re-rank candidates
        reranked = await self._rerank_with_llm(
            query, candidates, model=reranking_model, top_k=final_k
        )

        return "\n\n".join(r["content"] for r in reranked)


# Singleton for dependency injection
_rag_service: FirestoreRAGService | None = None


def get_rag_service() -> FirestoreRAGService:
    """Get RAG service singleton.

    Returns:
        FirestoreRAGService instance

    Raises:
        RuntimeError: If service not initialized
    """
    global _rag_service
    if _rag_service is None:
        raise RuntimeError("RAG service not initialized")
    return _rag_service


def init_rag_service(db: firestore.AsyncClient, settings: Settings) -> None:
    """Initialize RAG service with Firestore client and settings.

    Args:
        db: Async Firestore client instance
        settings: Application settings
    """
    global _rag_service
    _rag_service = FirestoreRAGService(db, settings)
