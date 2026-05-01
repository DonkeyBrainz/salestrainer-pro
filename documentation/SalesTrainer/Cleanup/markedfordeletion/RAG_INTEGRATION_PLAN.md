# PDF Product Knowledge Integration Plan

## Objective
Integrate 8 product knowledge PDFs into the training system to:
1. Direct scenario/persona selection based on product context
2. Enhance coach hinting through RAG over product documentation

---

## Implementation Approach: Firestore Vector Search Only

### Decision
**Go directly to Firestore Vector Search** - Skip in-memory FAISS and Vertex AI Search. Already using Firestore, GCP-native integration, persistent storage from day one, no migration needed later.

### Trade-off Analysis

| Approach | Time to Production | Accuracy | Cost | Persistence | Scalability |
|----------|-------------------|----------|------|-------------|-------------|
| **Firestore Vector Search** | 4-5 days | ★★★★☆ | $0 | ✅ Yes | Excellent |
| FAISS (in-memory) | 2-3 days | ★★★★☆ | $0 | ❌ No (rebuilds) | Good <100 docs |
| Vertex AI Vector Search | 1-2 weeks | ★★★★★ | $50-100/mo | ✅ Yes | Excellent |
| Chroma + Cloud SQL | 1 week | ★★★★☆ | $20-50/mo | ✅ Yes | Good |

**Winner:** Firestore Vector Search
- **Why:** Already using Firestore, GCP-native, persistent storage, no migration needed
- **Trade-off:** Preview status (not GA) - accept potential API changes for cleaner architecture
- **Timeline:** 1-2 days longer than FAISS, but saves future migration work

---

## Implementation Plan

### Phase 1: Firestore Vector Search Integration (4-5 Days)

#### Goal
Get product-aware coach hints working with persistent vector storage in Firestore.

#### What Gets Built

**1. Firestore Vector Index Setup**
- Create `knowledge_chunks` collection in Firestore
- Each document contains:
  - `content`: Text chunk from PDF
  - `embedding`: Vector (768 dimensions from Gemini)
  - `metadata`: Source file, category, page number, chunk ID
- Enable vector search index on `embedding` field

**2. PDF Processing Pipeline** (`app/services/rag_service.py` - 250 lines)
- Load PDFs from Google Cloud Storage
- Chunk documents (800 chars, 200 overlap)
- Generate embeddings via Gemini text-embedding-004
- Store in Firestore `knowledge_chunks` collection
- One-time setup script + incremental update capability

**3. RAG Retrieval Service** (`app/services/rag_service.py`)
```python
async def retrieve(
    query: str,
    persona: CustomerPersona,
    stage: SalesStage,
    top_k: int = 3
) -> str:
    # 1. Embed query with Gemini
    query_embedding = await gemini.embed(query)

    # 2. Firestore vector search
    results = await db.collection("knowledge_chunks").find_nearest(
        vector_field="embedding",
        query_vector=query_embedding,
        distance_measure=DistanceMeasure.COSINE,
        limit=top_k
    ).get()

    # 3. Format context string
    context = "\n\n".join([doc["content"] for doc in results])
    return context
```

**4. GCS Bucket for PDFs** (`terraform/storage.tf` - 30 lines)
```
gs://ashley-ai-sales-coach-knowledge/
  └── products/
      ├── bedroom_furniture.pdf
      ├── living_room_seating.pdf
      ├── mattresses.pdf
      ├── dining_sets.pdf
      ├── home_office.pdf
      ├── outdoor.pdf
      ├── protection_plans.pdf
      └── financing_options.pdf
```

**5. Enhanced Coach Hints** (Modify `analyzer.py` + `prompts.py`)
- Before calling Gemini, query Firestore vector search
- Inject product context into coach analysis prompt
- LLM generates hints with specific product details

**6. One-Time Setup Script** (`scripts/build_knowledge_index.py` - 100 lines)
- Reads PDFs from GCS
- Chunks and embeds documents
- Populates Firestore collection
- Run once during deployment, then incremental updates

#### Critical Files Modified

| File | Change | Lines | Complexity |
|------|--------|-------|------------|
| `app/services/rag_service.py` | **NEW** - RAG with Firestore vector search | 250 | Medium |
| `app/agents/coach/analyzer.py` | Add RAG call before LLM | +15 | Low |
| `app/agents/coach/prompts.py` | Add product context to prompt | +30 | Low |
| `scripts/build_knowledge_index.py` | **NEW** - One-time indexing script | 100 | Medium |
| `terraform/firestore.tf` | **NEW** - Firestore indexes | 40 | Low |
| `terraform/storage.tf` | **NEW** - GCS bucket | 30 | Low |
| `pyproject.toml` | Add dependencies | +2 | Trivial |

**Total new code:** ~470 lines

#### Dependencies to Add
```toml
dependencies = [
    "google-cloud-storage>=2.14.0", # GCS PDF access
    "pypdf>=3.17.0",              # PDF parsing
    # google-cloud-firestore already in dependencies
]
```

#### Firestore Schema

**Collection:** `knowledge_chunks`

**Document Structure:**
```json
{
  "chunk_id": "living_room_001",
  "content": "The SECTIONAL features stain-resistant performance fabric...",
  "embedding": Vector([0.123, -0.456, ...]),  // 768 dimensions
  "metadata": {
    "source_file": "living_room_seating.pdf",
    "page": 3,
    "category": "living_room",
    "product_type": "sectional",
    "chunk_index": 1,
    "created_at": "2026-02-16T10:00:00Z"
  }
}
```

**Vector Index:**
```
Field: embedding
Dimensions: 768
Distance: COSINE
```

#### Success Criteria
- ✅ Coach hints reference specific product features
- ✅ Retrieval latency <200ms (Firestore query)
- ✅ Persistent index (no rebuild on startup)
- ✅ Cost: $0/month (within Firestore free tier)
- ✅ Incremental updates (add PDFs without full rebuild)

#### Example Output

**Before RAG:**
```
Hint: "Ask about the customer's concerns with durability."
```

**After RAG:**
```
Hint: "Great question! This sectional features performance fabric with
       stain-resistant technology - perfect for families with kids and pets.
       Mention it's easy to clean with just soap and water."
```

---

### Phase 2: Enhanced Retrieval with Metadata Filtering (1-2 Weeks)

#### Goal
Product-context persona selection + metadata-filtered Firestore queries for higher precision.

#### What Gets Added

**1. Product Metadata on Personas**
- Add fields: `product_category`, `product_type`, `product_keywords`
- Update all 11 personas with structured product data

**2. Metadata-Filtered Firestore Queries**
```python
# Filter by category before vector search
results = await db.collection("knowledge_chunks")
    .where("metadata.category", "==", persona.product_category)
    .find_nearest(
        vector_field="embedding",
        query_vector=query_embedding,
        limit=5
    ).get()
```

**3. Persona Filtering API**
- New endpoint: `GET /api/v1/personas/filter?category=living_room`
- Frontend filters personas by product category

**4. Session Product Context**
- Store `product_context` in session document
- Analytics: which products get most training

#### Critical Files Modified

| File | Change | Lines | Complexity |
|------|--------|-------|------------|
| `app/agents/state.py` | Add product fields to persona | +15 | Low |
| `app/agents/personas.py` | Update 11 personas with metadata | +120 | Medium |
| `app/api/personas.py` | New filtering endpoint | +30 | Low |
| `app/services/rag_service.py` | Add metadata filtering | +30 | Low |
| `app/models/session.py` | Add product_context field | +5 | Trivial |

**Total changes:** ~200 lines

---

### Phase 3: Advanced Features (Future)

#### When to Execute
- After Phase 2 is stable
- When document count grows >100
- When need advanced retrieval strategies

#### Advanced Features

**1. Hybrid Search**
- Combine semantic (vector) + keyword (BM25) search
- Use Firestore full-text search + vector search

**2. Re-ranking**
- Retrieve top 10 results
- Use LLM to re-rank → return top 3
- Improves precision for complex queries

**3. Conversation-Aware Retrieval**
- Use full conversation history for context
- Embed entire conversation + query
- Better understanding of user intent

**4. Objection Handling Database**
- Separate Firestore collection for common objections
- Pre-indexed objection + response pairs
- Fast lookup for objection handling

---

## Integration Flow

### Enhanced Flow with Firestore RAG
```
Salesperson Message
    ↓
WebSocket Receives
    ↓
CoachAnalyzer.analyze()
    ├─ **NEW: Query Firestore Vector Search**
    │   ├─ Embed message with Gemini
    │   ├─ Firestore find_nearest (COSINE similarity)
    │   └─ Get top 3 relevant chunks
    │
    ├─ Format conversation history
    ├─ Build coach prompt **+ product context**
    ├─ Call Gemini 2.0 Flash
    └─ Parse response
    ↓
CoachHint (with product details)
    ↓
WebSocket Sends
```

### Code Change Example

**File:** `app/agents/coach/analyzer.py`

**After (with Firestore RAG):**
```python
async def analyze(
    self,
    salesperson_message: str,
    messages: list[BaseMessage],
    persona: CustomerPersona,
    stage_progress: EASYStageProgress,
) -> CoachAnalysis:
    # NEW: Retrieve product context from Firestore
    rag_service = get_rag_service()
    product_context = await rag_service.retrieve(
        query=salesperson_message,
        persona=persona,
        stage=stage_progress.current_stage,
        top_k=3
    )

    # Format conversation history
    history_tuples = self._messages_to_tuples(messages)
    conversation_history = format_conversation_history(history_tuples)

    # Build prompt with product context
    prompt = build_coach_prompt(
        salesperson_message=salesperson_message,
        persona=persona,
        stage_progress=stage_progress,
        conversation_history=conversation_history,
        product_context=product_context,  # NEW
    )

    # Call Gemini
    response = await self._call_gemini(prompt)
    return self._parse_response(response, stage_progress.current_stage.value)
```

**Changes:** +8 lines, minimal risk

---

## Terraform Configuration

### Firestore Vector Index

**File:** `terraform/firestore.tf` (NEW)

```hcl
# Enable Firestore vector search index
resource "google_firestore_index" "knowledge_chunks_vector" {
  project    = var.project_id
  collection = "knowledge_chunks"

  fields {
    field_path   = "embedding"
    vector_config {
      dimension = 768
      flat {}
    }
  }

  fields {
    field_path = "metadata.category"
    order      = "ASCENDING"
  }

  query_scope = "COLLECTION"
}

# Composite index for filtered vector search
resource "google_firestore_index" "knowledge_chunks_filtered" {
  project    = var.project_id
  collection = "knowledge_chunks"

  fields {
    field_path = "metadata.category"
    order      = "ASCENDING"
  }

  fields {
    field_path = "metadata.product_type"
    order      = "ASCENDING"
  }

  query_scope = "COLLECTION"
}
```

### GCS Bucket

**File:** `terraform/storage.tf` (NEW)

```hcl
resource "google_storage_bucket" "knowledge_bucket" {
  name          = "${var.project_id}-sales-coach-knowledge"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

resource "google_storage_bucket_iam_member" "backend_storage_reader" {
  bucket = google_storage_bucket.knowledge_bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.backend.email}"
}
```

---

## Implementation Timeline

### Week 1: Firestore Vector Search Setup

**Day 1:**
- [ ] Create GCS bucket via Terraform
- [ ] Upload 8 PDFs to GCS
- [ ] Add dependencies to pyproject.toml
- [ ] Create Firestore indexes via Terraform
- [ ] Wait for index build (may take 30-60 minutes)

**Day 2-3:**
- [ ] Implement `rag_service.py` with Firestore queries
- [ ] Write `scripts/build_knowledge_index.py`
- [ ] Run index build script (embed + store in Firestore)
- [ ] Write unit tests for RAG service
- [ ] Verify Firestore documents created correctly

**Day 4:**
- [ ] Modify `analyzer.py` to call RAG
- [ ] Update `prompts.py` with product context
- [ ] Integration tests
- [ ] Local testing with Firestore emulator

**Day 5 (Deploy):**
- [ ] Deploy to development environment
- [ ] Smoke tests
- [ ] Deploy to production
- [ ] Monitor Firestore query performance

### Week 2-3: Phase 2 (Metadata Filtering)

**Week 2:**
- [ ] Add product metadata to personas
- [ ] Implement persona filtering endpoint
- [ ] Update RAG with metadata filtering
- [ ] Add product_context to sessions

**Week 3:**
- [ ] Frontend integration (persona filtering)
- [ ] Testing and refinement
- [ ] Deploy to production

---

## Data Requirements

### PDF Specifications
- **Count:** 8 files to start
- **Format:** Text-based PDFs (not scanned images)
- **Content:** Product features, specs, objection handling, pricing, comparisons
- **Size:** ~5-10MB each (typical product catalog)

### Recommended PDF Contents

1. **Bedroom Furniture Catalog**
2. **Living Room Seating Catalog**
3. **Mattress Guide**
4. **Dining Sets Catalog**
5. **Home Office Furniture**
6. **Outdoor Furniture**
7. **Protection Plans**
8. **Financing Options**

---

## Testing Strategy

### Unit Tests
- `tests/unit/services/test_rag_service.py`
  - Test document chunking
  - Test embedding generation
  - Test Firestore document creation
  - Test vector search queries
  - Mock Firestore for fast tests

### Integration Tests
- `tests/integration/test_rag_integration.py`
  - Test with real Firestore (test database)
  - Test with sample PDFs
  - Test coach hint includes product details
  - Test end-to-end flow

### Manual Testing Scenarios

**Scenario 1: Living Room Furniture**
- Persona: BUSY_PARENT (sectional)
- Message: "Is this durable for kids?"
- Expected: Hint mentions stain-resistant fabric from PDF

**Scenario 2: Bedroom Furniture**
- Persona: DEMANDING_PROFESSIONAL (bedroom set)
- Message: "What's the quality?"
- Expected: Hint references wood type, construction details

**Scenario 3: Objection Handling**
- Persona: PRICE_RESISTANT (mattress)
- Message: "Too expensive"
- Expected: Hint suggests financing options from PDF

---

## Performance Targets

| Metric | Target | Critical |
|--------|--------|----------|
| Firestore vector query latency | <200ms | <400ms |
| Index build time (one-time) | <5 min | <10 min |
| Total hint latency | <2.5s | <4s |
| Firestore reads/hint | 3-5 | 10 |

---

## Cost Analysis

### Firestore Vector Search Costs

**Storage:**
- 8 PDFs × 100 chunks = 800 documents
- Each document: ~2KB (content + embedding + metadata)
- Total: 1.6MB stored
- Cost: $0.00/month (within 1GB free tier)

**Vector Search Queries:**
- Estimate: 100 training sessions/day × 20 hints/session = 2,000 queries/day
- Cost: $0.00/month (within 20K reads/day free tier)

**Embeddings (Gemini):**
- One-time: 800 chunks embedded
- Ongoing: 2,000 query embeddings/day
- Cost: $0/month (within Gemini free tier)

**Total Cost: $0/month**

**When costs start:**
- > 1GB stored (~500,000 chunks): $0.18/GB/month
- > 20K reads/day: $0.06 per 100K reads

---

## Rollback Plan

### If Firestore Vector Search Has Issues

**Quick Rollback (<10 minutes):**
```bash
# Revert code deployment
gcloud run services update-traffic salescoach-backend \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region us-central1
```

**Graceful Degradation (Built-in):**
```python
try:
    product_context = await rag_service.retrieve(...)
except Exception as e:
    logger.warning(f"Firestore RAG failed: {e}, using fallback")
    product_context = ""  # Generic hints still work
```

---

## Key Decisions & Rationale

### 1. Why Firestore Vector Search over FAISS?
- **Already using Firestore** - Same database for everything
- **GCP-native** - Same auth, monitoring, billing
- **Persistent storage** - No rebuild on startup
- **Incremental updates** - Add PDFs without full reindex
- **Metadata filtering** - Built-in Firestore queries
- **Trade-off:** Preview status (not GA) - accept API change risk

### 2. Why Gemini Embeddings?
- Already using Gemini for LLM
- Same API client, auth, billing
- Strong performance (768 dimensions)
- Free tier covers usage

### 3. Why One-Time Setup Script?
- Separate indexing from runtime
- Can re-run when PDFs change
- Doesn't slow down backend startup
- Can run as Cloud Function or locally

### 4. Why Not Fine-tune Gemini?
- RAG is faster (days vs weeks)
- RAG handles document updates
- RAG provides source attribution
- Fine-tuning overkill for 8 PDFs

---

## Success Metrics

### Technical Metrics
- ✅ Firestore vector query latency <200ms (P95)
- ✅ 85%+ top-3 recall on test queries
- ✅ Zero production incidents from RAG

### Business Metrics
- 📊 % of coach hints using product context (target: >60%)
- 📊 Avg hint length increases (more specific)
- 📊 User satisfaction surveys

### Quality Metrics
- Manual review: 50 hints with RAG
- Criteria: Relevant? Accurate? Better than generic?
- Target: >80% improved by RAG

---

## Firestore Preview Status: What to Watch

### Known Limitations (as of Feb 2026)
- **Preview API** - May have breaking changes
- **Index build time** - Can take 30-60 minutes initially
- **Query limits** - Check current quota limits
- **Distance measures** - COSINE, EUCLIDEAN, DOT_PRODUCT supported

### Monitoring Strategy
- Watch GCP release notes for Firestore Vector Search updates
- Monitor Firestore query latencies in Cloud Monitoring
- Set up alerts for query failures or high latencies
- Track vector index performance metrics in GCP Console

---

## Verification Checklist

### Phase 1 Complete When:
- [ ] Firestore `knowledge_chunks` collection created
- [ ] Vector index built and active
- [ ] 800+ documents in collection (8 PDFs × ~100 chunks)
- [ ] Coach hint in TRAINING session mentions specific product feature
- [ ] Firestore query latency <400ms (check logs)
- [ ] No errors in Cloud Run logs related to RAG
- [ ] Manual test: 3 scenarios pass (living room, bedroom, objection)

### Phase 2 Complete When:
- [ ] Personas filterable by category via API
- [ ] Metadata filtering works in Firestore queries
- [ ] RAG scoped to persona's product_category
- [ ] Frontend can filter personas

---

## Next Actions

**To start Phase 1:**
1. ✅ Decision made: Use Firestore Vector Search
2. Collect 8 PDFs (product knowledge documents)
3. Review PDF quality (text-based, not scanned)
4. Approve this plan
5. Begin implementation:
   - Day 1: Infrastructure (GCS, Firestore indexes)
   - Day 2-3: Indexing script + RAG service
   - Day 4: Integration with coach agent
   - Day 5: Deploy and test

**Questions:**
- Do you have the 8 PDFs ready?
- Any specific products to prioritize?
- Prefer to start with fewer PDFs (e.g., 3-4) for faster testing?
