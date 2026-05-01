# RAG Phase 3: Advanced Retrieval Features

## Branch Info
**Branch name:** `feat/rag-phase-3-advanced-retrieval`
**Base branch:** `development` (after Phase 2 merged)
**Estimated duration:** 2-3 weeks (execute when needed)

---

## Objective
Implement advanced RAG features for improved retrieval quality and specialized use cases.

**Success criteria:**
- Hybrid search combining semantic + keyword matching
- LLM-based re-ranking for higher precision
- Conversation-aware retrieval using full context
- Objection handling database with fast lookup
- Measurable improvement in retrieval quality metrics

---

## When to Execute Phase 3

### Triggers (any of these):
- [ ] Document count grows >100 PDFs
- [ ] Retrieval precision <80% in production
- [ ] User feedback requests more specific hints
- [ ] Need specialized objection handling
- [ ] Conversation context not captured well

### Prerequisites
- [ ] Phase 1 and 2 deployed and stable in production
- [ ] Baseline metrics established (precision, recall, latency)
- [ ] Product team approval for advanced features
- [ ] Budget allocated for potential LLM re-ranking costs

---

## Feature 1: Hybrid Search

### Objective
Combine semantic (vector) search with keyword (BM25) search for better retrieval on exact terms.

### Use Case
- User asks: "What's the warranty on the Beautyrest Black?"
- Vector search: Gets general mattress info
- Keyword search: Gets exact "Beautyrest Black" warranty details
- Hybrid: Combines both for best results

### Implementation

**Files to modify:**
- `backend/app/services/rag_service.py` (+80 lines)

**New method:**
```python
async def hybrid_retrieve(
    self,
    query: str,
    persona: CustomerPersona,
    stage: SalesStage,
    top_k: int = 5,
    semantic_weight: float = 0.7,  # Weight for vector search
    keyword_weight: float = 0.3,   # Weight for keyword search
) -> str:
    """Hybrid search combining vector + keyword matching."""
    # 1. Semantic search (vector)
    semantic_results = await self._semantic_search(query, persona, top_k * 2)

    # 2. Keyword search (BM25 or Firestore full-text)
    keyword_results = await self._keyword_search(query, persona, top_k * 2)

    # 3. Reciprocal Rank Fusion (RRF) to combine results
    combined_results = self._reciprocal_rank_fusion(
        semantic_results,
        keyword_results,
        semantic_weight,
        keyword_weight
    )

    # 4. Return top_k after fusion
    top_results = combined_results[:top_k]
    context = "\n\n".join([doc["content"] for doc in top_results])
    return context

def _reciprocal_rank_fusion(
    self,
    semantic_results: list[dict],
    keyword_results: list[dict],
    semantic_weight: float,
    keyword_weight: float,
    k: int = 60  # RRF constant
) -> list[dict]:
    """Combine results using Reciprocal Rank Fusion."""
    scores = {}

    # Score semantic results
    for rank, doc in enumerate(semantic_results, start=1):
        doc_id = doc["chunk_id"]
        scores[doc_id] = scores.get(doc_id, 0) + semantic_weight / (k + rank)

    # Score keyword results
    for rank, doc in enumerate(keyword_results, start=1):
        doc_id = doc["chunk_id"]
        scores[doc_id] = scores.get(doc_id, 0) + keyword_weight / (k + rank)

    # Sort by combined score
    sorted_docs = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # Return documents in fused order
    return [self._get_doc_by_id(doc_id) for doc_id, _ in sorted_docs]
```

**Keyword search options:**
1. **Firestore full-text search** (if available)
2. **BM25 with in-memory index** (for <1000 docs)
3. **Elasticsearch** (if scaling beyond Firestore)

**Testing:**
- Compare hybrid vs semantic-only on brand names, model numbers
- Verify latency stays <500ms
- Measure precision improvement

---

## Feature 2: LLM Re-Ranking

### Objective
Use LLM to re-rank top-N results for better precision, especially for complex queries.

### Use Case
- Vector search returns 10 somewhat relevant chunks
- LLM re-ranks based on actual query intent
- Return top 3 most relevant chunks

### Implementation

**Files to modify:**
- `backend/app/services/rag_service.py` (+100 lines)

**New method:**
```python
async def retrieve_with_reranking(
    self,
    query: str,
    persona: CustomerPersona,
    stage: SalesStage,
    initial_k: int = 10,  # Retrieve more candidates
    final_k: int = 3,     # Return top 3 after re-ranking
) -> str:
    """Retrieve with LLM-based re-ranking for higher precision."""
    # 1. Initial retrieval (vector or hybrid)
    candidates = await self._get_candidates(query, persona, initial_k)

    # 2. Re-rank using LLM
    reranked = await self._rerank_with_llm(query, candidates, final_k)

    # 3. Format context
    context = "\n\n".join([doc["content"] for doc in reranked])
    return context

async def _rerank_with_llm(
    self,
    query: str,
    candidates: list[dict],
    top_k: int
) -> list[dict]:
    """Use Gemini Flash to re-rank candidate chunks."""
    # Build re-ranking prompt
    prompt = f"""Given the following query and candidate text chunks, rank the chunks by relevance to the query.
Return only the indices of the top {top_k} most relevant chunks in order.

Query: {query}

Chunks:
"""
    for idx, doc in enumerate(candidates):
        prompt += f"\n[{idx}] {doc['content'][:200]}...\n"

    prompt += f"\nReturn format: Just the indices as a comma-separated list (e.g., \"3,7,1\")"

    # Call Gemini Flash (cheap, fast)
    response = await self.genai_client.generate_content(
        model="gemini-2.0-flash-exp",
        prompt=prompt
    )

    # Parse indices
    indices = [int(i.strip()) for i in response.text.split(",")]

    # Return reranked documents
    return [candidates[i] for i in indices[:top_k]]
```

**Cost considerations:**
- Gemini Flash: ~$0.075 per 1M input tokens
- 10 chunks × 200 chars = ~500 tokens per re-rank
- ~2000 hints/day × 500 tokens = 1M tokens/day = $0.075/day = $2.25/month
- Still cheap, but no longer free tier

**Testing:**
- Compare re-ranked vs top-3 without re-ranking
- Measure precision improvement (target: +10%)
- Monitor cost and latency

---

## Feature 3: Conversation-Aware Retrieval

### Objective
Use full conversation history to improve retrieval, not just the latest message.

### Use Case
- Turn 1: "I need a sofa"
- Turn 2: "Do you have it in leather?"
- Turn 3: "What about stain protection?"

Current: Only searches "What about stain protection?"
Improved: Searches "leather sofa stain protection"

### Implementation

**Files to modify:**
- `backend/app/services/rag_service.py` (+60 lines)
- `backend/app/agents/coach/analyzer.py` (+5 lines)

**Updated analyzer.py:**
```python
async def analyze(
    self,
    salesperson_message: str,
    messages: list[BaseMessage],
    persona: CustomerPersona,
    stage_progress: EASYStageProgress,
) -> CoachAnalysis:
    # NEW: Pass conversation history to RAG
    rag_service = get_rag_service()
    product_context = await rag_service.retrieve_with_conversation(
        query=salesperson_message,
        conversation_history=messages,  # NEW parameter
        persona=persona,
        stage=stage_progress.current_stage,
        top_k=3
    )
    # ... rest of analyzer ...
```

**New RAG method:**
```python
async def retrieve_with_conversation(
    self,
    query: str,
    conversation_history: list[BaseMessage],
    persona: CustomerPersona,
    stage: SalesStage,
    top_k: int = 3
) -> str:
    """Retrieve using conversation context."""
    # 1. Build contextualized query
    context_query = self._build_context_query(query, conversation_history)

    # 2. Retrieve with enhanced query
    return await self.retrieve(context_query, persona, stage, top_k)

def _build_context_query(
    self,
    query: str,
    conversation_history: list[BaseMessage],
    max_history: int = 5
) -> str:
    """Build query with conversation context."""
    # Get last N messages
    recent = conversation_history[-max_history:] if len(conversation_history) > max_history else conversation_history

    # Extract key nouns/entities from history
    context_terms = []
    for msg in recent:
        # Simple extraction: look for product terms
        # In production: use NER or LLM to extract entities
        text = msg.content.lower()
        if "sofa" in text or "sectional" in text:
            context_terms.append("sofa")
        if "leather" in text:
            context_terms.append("leather")
        # ... more patterns ...

    # Combine current query with context terms
    if context_terms:
        enhanced_query = f"{query} {' '.join(set(context_terms))}"
    else:
        enhanced_query = query

    return enhanced_query
```

**Advanced option:**
Use LLM to generate enhanced query:
```python
async def _build_context_query_llm(
    self,
    query: str,
    conversation_history: list[BaseMessage]
) -> str:
    """Use LLM to generate context-enhanced query."""
    history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in conversation_history[-5:]])

    prompt = f"""Given the conversation history and latest query, create an enhanced search query that captures the full context.

Conversation:
{history_text}

Latest query: {query}

Enhanced search query (one line):"""

    response = await self.genai_client.generate_content(
        model="gemini-2.0-flash-exp",
        prompt=prompt
    )

    return response.text.strip()
```

**Testing:**
- Multi-turn conversations with context shifts
- Verify retrieval captures conversation context
- Compare with single-message retrieval

---

## Feature 4: Objection Handling Database

### Objective
Fast lookup for common objections with pre-indexed responses.

### Use Case
- Customer says: "That's too expensive"
- Fast lookup: Get financing options, value propositions, comparisons
- No vector search needed for common objections

### Implementation

**Firestore collection:**
```
objections/
  ├── price_too_high
  ├── need_to_think
  ├── shopping_around
  ├── quality_concerns
  └── delivery_timeline
```

**Document structure:**
```json
{
  "objection_id": "price_too_high",
  "triggers": [
    "too expensive",
    "can't afford",
    "out of my budget",
    "cheaper elsewhere"
  ],
  "responses": [
    "Mention financing options: 0% APR for 60 months",
    "Emphasize value: 10-year warranty vs competitors' 1-year",
    "Compare: Show price per day over product lifetime"
  ],
  "product_specific": {
    "mattress": "Our mattresses last 10-15 years vs 7 years for budget brands",
    "living_room": "Performance fabric resists stains, saving cleaning costs"
  }
}
```

**Files to create:**
- `backend/app/services/objection_service.py` (NEW - 120 lines)

**Implementation:**
```python
class ObjectionService:
    def __init__(self, db: firestore.AsyncClient):
        self.db = db

    async def detect_objection(self, message: str) -> str | None:
        """Detect if message contains a common objection."""
        message_lower = message.lower()

        # Query objections collection
        objections = await self.db.collection("objections").get()

        for objection_doc in objections:
            objection = objection_doc.to_dict()
            for trigger in objection["triggers"]:
                if trigger in message_lower:
                    return objection["objection_id"]

        return None

    async def get_objection_response(
        self,
        objection_id: str,
        product_category: str | None = None
    ) -> str:
        """Get response for detected objection."""
        doc = await self.db.collection("objections").document(objection_id).get()
        objection = doc.to_dict()

        responses = objection["responses"]

        # Add product-specific response if available
        if product_category and product_category in objection.get("product_specific", {}):
            responses.append(objection["product_specific"][product_category])

        return "\n".join(responses)
```

**Integration with coach:**
```python
# In analyzer.py
async def analyze(...):
    # Check for objection first
    objection_service = get_objection_service()
    objection_id = await objection_service.detect_objection(salesperson_message)

    if objection_id:
        # Fast path: use objection database
        product_context = await objection_service.get_objection_response(
            objection_id,
            persona.product_category
        )
    else:
        # Normal path: RAG retrieval
        product_context = await rag_service.retrieve(...)

    # ... rest of analyzer ...
```

**Benefits:**
- Fast lookup (<10ms vs 200ms for vector search)
- Consistent responses for common objections
- Easy to update and maintain

**Testing:**
- Test common objections are detected
- Verify fast lookup performance
- Compare with vector search quality

---

## Implementation Priority

### Recommended order:
1. **Objection Handling Database** (1 week)
   - Easiest to implement
   - Immediate value for common scenarios
   - No cost increase

2. **Conversation-Aware Retrieval** (1 week)
   - Moderate complexity
   - Improves multi-turn conversations
   - Minimal cost increase

3. **Hybrid Search** (1-2 weeks)
   - Requires keyword search infrastructure
   - Good for exact match queries
   - No cost increase

4. **LLM Re-Ranking** (1 week)
   - Easy to implement
   - Highest cost increase ($2-3/month)
   - Best precision improvement

---

## Performance & Cost Impact

### Latency targets:

| Feature | Added Latency | Total Target |
|---------|---------------|--------------|
| Hybrid Search | +50ms | <450ms |
| LLM Re-Ranking | +300ms | <700ms |
| Conversation-Aware | +20ms | <420ms |
| Objection DB | -190ms | <210ms |

### Cost estimates:

| Feature | Monthly Cost |
|---------|-------------|
| Hybrid Search | $0 |
| LLM Re-Ranking | $2-3 |
| Conversation-Aware | $0.50 |
| Objection DB | $0 |

**Total Phase 3:** ~$3-4/month (if all features enabled)

---

## Testing Strategy

### A/B Testing
- Compare Phase 2 vs Phase 3 features
- Metrics: precision, recall, user satisfaction
- Run for 2 weeks before full rollout

### Evaluation Dataset
Create 50 test queries with:
- Ground truth relevant chunks
- Common objections
- Multi-turn conversations
- Brand/model-specific queries

### Success Metrics
- Precision@3: >85% (vs 70% baseline)
- Recall@10: >90% (vs 75% baseline)
- Latency P95: <700ms
- User satisfaction: >4.5/5

---

## Rollback Plan

### Feature flags
Enable/disable each feature independently:
```python
# config.py
class RAGConfig(BaseModel):
    use_hybrid_search: bool = False
    use_reranking: bool = False
    use_conversation_context: bool = False
    use_objection_db: bool = True  # Safe to enable by default
```

### Gradual rollout
1. Enable for 10% of sessions
2. Monitor metrics
3. Increase to 50% if stable
4. Full rollout after 1 week

---

## Acceptance Criteria

### Phase 3 is complete when:
- [ ] All 4 features implemented
- [ ] Feature flags working
- [ ] A/B testing shows improvement
- [ ] Latency within targets
- [ ] Cost within budget
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Deployed to production
- [ ] Monitoring dashboards created

---

## Future Enhancements

### Beyond Phase 3:
- **Multi-modal RAG:** Include product images in retrieval
- **Personalized retrieval:** Learn user preferences over time
- **Agentic RAG:** Agent decides when/what to retrieve
- **External knowledge:** Integrate competitor data, reviews
- **Real-time updates:** Stream new product info without reindex

---

## Decision: When to Start Phase 3

### Start Phase 3 if:
- Phase 2 stable for >1 month
- Retrieval precision <80% in production
- Document count >100
- Budget approved for LLM costs

### Postpone Phase 3 if:
- Phase 2 meeting all needs
- Precision >90% already
- Team focused on other priorities
- Cost constraints
