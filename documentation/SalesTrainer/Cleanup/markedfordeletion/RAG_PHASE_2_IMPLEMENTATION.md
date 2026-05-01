# RAG Phase 2: Metadata Filtering & Persona-Product Binding

## Branch Info
**Branch name:** `feat/rag-phase-2-metadata-filtering`
**Base branch:** `development` (after Phase 1 merged)
**Estimated duration:** 1-2 weeks

---

## Objective
Add product-aware persona selection and metadata-filtered Firestore queries for higher precision RAG retrieval.

**Success criteria:**
- Personas have product category metadata
- RAG queries filter by persona's product category
- New API endpoint for filtering personas by product
- Session stores product context for analytics
- Retrieval precision improves (fewer irrelevant results)

---

## Prerequisites

### Required before starting
- [ ] Phase 1 complete and deployed to production
- [ ] Firestore vector search working with coach hints
- [ ] All 11 personas reviewed for product categorization
- [ ] Product taxonomy defined (categories, types, keywords)

### Phase 1 dependencies
- Firestore `knowledge_chunks` collection populated
- Vector index active and performant
- RAG service functional
- Coach hints using product context

---

## Product Taxonomy

Define product categories and types for metadata filtering:

**Categories:**
- `bedroom` - Bedroom furniture
- `living_room` - Sofas, sectionals, chairs
- `mattress` - All mattress types
- `dining` - Dining sets, tables, chairs
- `home_office` - Desks, office chairs
- `outdoor` - Patio furniture
- `protection` - Protection plans, warranties
- `financing` - Financing options, payment plans

**Product types** (examples):
- `sectional`, `sofa`, `loveseat` (living_room)
- `bedroom_set`, `dresser`, `nightstand` (bedroom)
- `memory_foam`, `hybrid`, `innerspring` (mattress)
- `dining_set`, `dining_table`, `dining_chair` (dining)

---

## Files to Create

### 1. `backend/tests/unit/api/test_personas_filter.py` (NEW - 60 lines)
Unit tests for persona filtering endpoint.

**Test cases:**
- `test_filter_personas_by_category`
- `test_filter_personas_returns_empty_for_invalid_category`
- `test_filter_personas_validates_category_param`

### 2. `backend/tests/integration/test_rag_metadata_filtering.py` (NEW - 80 lines)
Integration tests for metadata-filtered RAG queries.

**Test scenarios:**
- Verify RAG query filters by persona category
- Test retrieval returns only relevant category chunks
- Validate metadata filtering improves precision

---

## Files to Modify

### 1. `backend/app/agents/state.py` (+15 lines)
Add product fields to CustomerPersona class.

**Changes:**
```python
@dataclass
class CustomerPersona:
    id: str
    name: str
    backstory: str
    looking_for: str
    difficulty: Difficulty
    is_evaluation_only: bool = False
    # NEW: Product metadata
    product_category: str | None = None  # e.g., "living_room", "bedroom"
    product_type: str | None = None      # e.g., "sectional", "bedroom_set"
    product_keywords: list[str] = field(default_factory=list)  # e.g., ["durability", "family-friendly"]
```

### 2. `backend/app/agents/personas.py` (+120 lines)
Update all 11 personas with product metadata.

**Example updates:**
```python
BUSY_PARENT = CustomerPersona(
    id="busy_parent",
    name="Jamie Chen",
    backstory="...",
    looking_for="...",
    difficulty=Difficulty.MEDIUM_REGARD,
    # NEW fields
    product_category="living_room",
    product_type="sectional",
    product_keywords=["durability", "stain-resistant", "family-friendly", "easy-clean"],
)

EAGER_NEWLYWED = CustomerPersona(
    id="eager_newlywed",
    name="Alex & Morgan",
    backstory="...",
    looking_for="...",
    difficulty=Difficulty.HIGH_REGARD,
    # NEW fields
    product_category="bedroom",
    product_type="bedroom_set",
    product_keywords=["modern", "affordable", "quality", "first-home"],
)

PRICE_RESISTANT = CustomerPersona(
    id="price_resistant",
    name="Robert Martinez",
    backstory="...",
    looking_for="...",
    difficulty=Difficulty.LOW_REGARD,
    # NEW fields
    product_category="mattress",
    product_type="memory_foam",
    product_keywords=["value", "financing", "warranty", "price-conscious"],
)
```

**All 11 personas to update:**
1. EAGER_NEWLYWED - bedroom
2. BUSY_PARENT - living_room
3. SKEPTICAL_SHOPPER - living_room
4. DEMANDING_PROFESSIONAL - bedroom
5. PRICE_RESISTANT - mattress
6. TECH_SAVVY_MILLENNIAL - home_office
7. EMPTY_NESTER - bedroom
8. YOUNG_PROFESSIONAL - living_room
9. LUXURY_RENOVATOR - dining
10. FRUGAL_RETIREE - mattress
11. INDECISIVE_COUPLE_REP - living_room

### 3. `backend/app/api/personas.py` (+30 lines)
Add filtering endpoint for personas by product category.

**New endpoint:**
```python
@router.get("/filter", response_model=PersonaListResponse)
async def filter_personas(
    category: str | None = None,
    product_type: str | None = None,
) -> PersonaListResponse:
    """Filter personas by product category or type."""
    personas = []

    for persona in ALL_PERSONAS:
        # Skip evaluation-only personas for training
        if persona.is_evaluation_only:
            continue

        # Filter by category
        if category and persona.product_category != category:
            continue

        # Filter by product type
        if product_type and persona.product_type != product_type:
            continue

        personas.append(_persona_to_response(persona))

    return PersonaListResponse(personas=personas)
```

### 4. `backend/app/services/rag_service.py` (+30 lines)
Add metadata filtering to Firestore vector queries.

**Modified retrieve method:**
```python
async def retrieve(
    self,
    query: str,
    persona: CustomerPersona,
    stage: SalesStage,
    top_k: int = 3
) -> str:
    """Retrieve relevant product context with metadata filtering."""
    # 1. Embed query
    query_embedding = await self.embed_text(query)

    # 2. Build Firestore query with category filter
    collection_ref = self.db.collection("knowledge_chunks")

    # NEW: Filter by persona's product category if available
    if persona.product_category:
        collection_ref = collection_ref.where(
            "metadata.category", "==", persona.product_category
        )

    # 3. Vector search on filtered collection
    results = await collection_ref.find_nearest(
        vector_field="embedding",
        query_vector=query_embedding,
        distance_measure=firestore.DistanceMeasure.COSINE,
        limit=top_k
    ).get()

    # 4. Format context string
    context = "\n\n".join([doc.to_dict()["content"] for doc in results])
    return context
```

### 5. `backend/app/models/session.py` (+5 lines)
Add product_context field to session model for analytics.

**Changes:**
```python
class Session(BaseModel):
    session_id: str
    user_id: str
    session_type: SessionType
    status: SessionStatus
    # ... existing fields ...

    # NEW: Track product context
    product_category: str | None = None
    product_type: str | None = None
```

### 6. `backend/app/api/sessions.py` (+10 lines)
Store product context when creating session.

**Modify create_session endpoint:**
```python
@router.post("", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    user: UserInfo = Depends(get_current_user),
    session_repo: SessionRepository = Depends(get_session_repository),
) -> SessionResponse:
    # ... existing logic ...

    # NEW: Store product context if persona has it
    if session_data.persona_id:
        persona = get_persona_by_id(session_data.persona_id)
        if persona:
            session.product_category = persona.product_category
            session.product_type = persona.product_type

    # ... rest of endpoint ...
```

---

## Implementation Steps

### Week 1: Backend Implementation

**Day 1-2: Persona metadata**
1. Define product taxonomy (categories, types, keywords)
2. Update `state.py` with new fields
3. Update all 11 personas in `personas.py` with metadata
4. Write unit tests for updated personas
5. Run tests: `uv run pytest tests/unit/agents/test_personas.py -v`

**Day 3: Persona filtering API**
1. Add `/api/v1/personas/filter` endpoint
2. Write unit tests for filtering logic
3. Test endpoint manually:
   ```bash
   curl http://localhost:8000/api/v1/personas/filter?category=living_room
   ```

**Day 4-5: RAG metadata filtering**
1. Update `rag_service.py` with category filtering
2. Write integration tests for filtered queries
3. Verify retrieval precision improves
4. Test with different personas and categories

### Week 2: Session tracking & deployment

**Day 1-2: Session product context**
1. Update `session.py` model with product fields
2. Modify session creation to store product context
3. Add analytics queries for product tracking
4. Test session creation with product metadata

**Day 3: Testing & refinement**
1. Run full test suite
2. Integration testing with all personas
3. Verify metadata filtering works correctly
4. Performance testing (latency should stay <400ms)

**Day 4-5: Deploy**
1. Create PR for Phase 2
2. Code review
3. Deploy to development
4. Smoke tests in dev
5. Deploy to production
6. Monitor performance and accuracy

---

## Testing Requirements

### Unit Tests

**File:** `tests/unit/api/test_personas_filter.py`
- `test_filter_by_category_returns_matching_personas`
- `test_filter_by_product_type_returns_matching_personas`
- `test_filter_excludes_evaluation_personas`
- `test_filter_with_no_matches_returns_empty_list`

**File:** `tests/unit/services/test_rag_service.py` (additions)
- `test_retrieve_filters_by_persona_category`
- `test_retrieve_without_category_queries_all_chunks`
- `test_retrieve_filtered_results_more_precise`

### Integration Tests

**File:** `tests/integration/test_rag_metadata_filtering.py`
1. **Living room persona retrieval**
   - Use BUSY_PARENT (category: living_room)
   - Query: "Is this durable?"
   - Verify: Only living_room chunks returned
   - Verify: No bedroom or mattress chunks in results

2. **Bedroom persona retrieval**
   - Use EAGER_NEWLYWED (category: bedroom)
   - Query: "What's the quality?"
   - Verify: Only bedroom chunks returned
   - Verify: More relevant results than unfiltered

3. **Mattress persona retrieval**
   - Use PRICE_RESISTANT (category: mattress)
   - Query: "Too expensive"
   - Verify: Mattress + financing chunks returned
   - Verify: No furniture chunks in results

### Manual Testing Checklist
- [ ] Call `/api/v1/personas/filter?category=living_room`
- [ ] Verify returns only living_room personas (BUSY_PARENT, SKEPTICAL_SHOPPER, etc.)
- [ ] Start session with BUSY_PARENT
- [ ] Verify session has product_category="living_room"
- [ ] Send message, check coach hint uses only living_room products
- [ ] Check Firestore query logs show category filter

---

## Acceptance Criteria

### Phase 2 is complete when:
- [ ] All 11 personas have product_category and product_type
- [ ] `/api/v1/personas/filter` endpoint works correctly
- [ ] RAG queries filter by persona category in Firestore
- [ ] Sessions store product_category and product_type
- [ ] Retrieval precision improved (fewer irrelevant results)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Manual testing scenarios pass
- [ ] PR merged to development
- [ ] Deployed to production
- [ ] Monitoring shows category filtering working

---

## Performance Monitoring

### Metrics to track
1. **Retrieval precision**
   - % of results matching persona category
   - Target: >90% of results from correct category

2. **Query latency**
   - Should stay <400ms with filtering
   - May improve due to smaller result set

3. **Product analytics**
   - Track which categories get most training
   - Identify popular product types
   - Guide future PDF additions

### Queries to add
```sql
-- Sessions by product category
SELECT product_category, COUNT(*) as sessions
FROM sessions
WHERE session_type = 'training'
GROUP BY product_category
ORDER BY sessions DESC;

-- Popular product types
SELECT product_type, COUNT(*) as sessions
FROM sessions
WHERE session_type = 'training'
GROUP BY product_type
ORDER BY sessions DESC;
```

---

## Next Phase
After Phase 2 is complete and stable, consider:
**RAG_PHASE_3_IMPLEMENTATION.md** - Advanced features (hybrid search, re-ranking, conversation-aware retrieval)

---

## Rollback Plan

### If issues arise:
1. **Metadata filtering problems:**
   - Feature flag to disable category filtering
   - Fall back to unfiltered vector search
   - Investigate Firestore index issues

2. **Performance degradation:**
   - Check Firestore query logs
   - Verify composite index is being used
   - Adjust query structure if needed

3. **Code rollback:**
   ```bash
   gcloud run services update-traffic salescoach-backend \
     --to-revisions=PREVIOUS_REVISION=100 \
     --region us-central1
   ```

---

## Cost Impact

**Phase 2 costs:** Still $0/month

- No additional storage (metadata is small)
- Filtered queries may be faster (fewer results to process)
- Same Firestore read counts
- Same embedding API usage

All within existing free tiers.
