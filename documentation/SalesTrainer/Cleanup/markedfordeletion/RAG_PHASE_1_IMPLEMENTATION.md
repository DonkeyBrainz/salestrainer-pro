# RAG Phase 1: Firestore Vector Search Integration

## Branch Info
**Branch name:** `feat/rag-phase-1-firestore-vector-search`
**Base branch:** `development`
**Estimated duration:** 4-5 days

---

## Objective
Get product-aware coach hints working with persistent vector storage in Firestore.

**Success criteria:**
- Coach hints reference specific product features from PDFs
- Firestore vector query latency <400ms
- No rebuild on startup (persistent index)
- Cost: $0/month (within free tier)
- End-to-end test passes with product context in hints

---

## Prerequisites

### Required before starting
- [ ] 8 product knowledge PDFs ready
- [ ] PDFs are text-based (not scanned images)
- [ ] GCP project has Firestore enabled
- [ ] Backend service account has required permissions

### PDF list (8 files)
1. bedroom_furniture.pdf
2. living_room_seating.pdf
3. mattresses.pdf
4. dining_sets.pdf
5. home_office.pdf
6. outdoor.pdf
7. protection_plans.pdf
8. financing_options.pdf

---

## Files to Create

### 1. `terraform/storage.tf` (NEW - 30 lines)
GCS bucket for storing product knowledge PDFs.

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

### 2. `terraform/firestore.tf` (NEW - 40 lines)
Firestore vector search indexes.

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

# Composite index for filtered vector search (Phase 2)
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

### 3. `backend/app/services/rag_service.py` (NEW - 250 lines)
RAG retrieval service with Firestore vector search.

**Key functions:**
- `chunk_text(text: str, chunk_size: int = 800, overlap: int = 200) -> list[str]`
- `async embed_text(text: str) -> list[float]`
- `async retrieve(query: str, persona: CustomerPersona, stage: SalesStage, top_k: int = 3) -> str`

**Implementation sketch:**
```python
from google.cloud import firestore
from google.genai import Client
from app.agents.state import CustomerPersona, SalesStage

class RAGService:
    def __init__(self, db: firestore.AsyncClient, genai_client: Client):
        self.db = db
        self.genai_client = genai_client

    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding using Gemini text-embedding-004."""
        response = await self.genai_client.embed_content(
            model="models/text-embedding-004",
            content=text
        )
        return response.embedding

    async def retrieve(
        self,
        query: str,
        persona: CustomerPersona,
        stage: SalesStage,
        top_k: int = 3
    ) -> str:
        """Retrieve relevant product context from Firestore vector search."""
        # 1. Embed query
        query_embedding = await self.embed_text(query)

        # 2. Firestore vector search
        results = await self.db.collection("knowledge_chunks").find_nearest(
            vector_field="embedding",
            query_vector=query_embedding,
            distance_measure=firestore.DistanceMeasure.COSINE,
            limit=top_k
        ).get()

        # 3. Format context string
        context = "\n\n".join([doc.to_dict()["content"] for doc in results])
        return context
```

### 4. `backend/scripts/build_knowledge_index.py` (NEW - 100 lines)
One-time script to process PDFs and populate Firestore.

**Key steps:**
1. Load PDFs from GCS
2. Extract text using pypdf
3. Chunk documents
4. Generate embeddings
5. Store in Firestore knowledge_chunks collection

**Firestore document schema:**
```json
{
  "chunk_id": "living_room_001",
  "content": "The SECTIONAL features stain-resistant performance fabric...",
  "embedding": [0.123, -0.456, ...],  // 768 dimensions
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

### 5. `backend/tests/unit/services/test_rag_service.py` (NEW - 100 lines)
Unit tests for RAG service.

**Test cases:**
- `test_chunk_text_creates_overlapping_chunks`
- `test_embed_text_returns_768_dimensions`
- `test_retrieve_queries_firestore_vector_search`
- `test_retrieve_formats_context_string`

### 6. `backend/tests/integration/test_rag_integration.py` (NEW - 80 lines)
Integration tests for end-to-end RAG flow.

**Test scenarios:**
- Test with sample PDF
- Verify coach hint includes product details
- Test retrieval latency <400ms

---

## Files to Modify

### 1. `backend/pyproject.toml` (+2 lines)
Add dependencies for PDF processing and GCS access.

```toml
dependencies = [
    # ... existing dependencies ...
    "google-cloud-storage>=2.14.0",  # GCS PDF access
    "pypdf>=3.17.0",                 # PDF parsing
]
```

### 2. `backend/app/agents/coach/analyzer.py` (+15 lines)
Add RAG retrieval before LLM call.

**Changes:**
```python
async def analyze(
    self,
    salesperson_message: str,
    messages: list[BaseMessage],
    persona: CustomerPersona,
    stage_progress: EASYStageProgress,
) -> CoachAnalysis:
    # NEW: Retrieve product context from Firestore
    from app.services.rag_service import get_rag_service
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

    # Build prompt with product context (MODIFIED)
    prompt = build_coach_prompt(
        salesperson_message=salesperson_message,
        persona=persona,
        stage_progress=stage_progress,
        conversation_history=conversation_history,
        product_context=product_context,  # NEW parameter
    )

    # Call Gemini
    response = await self._call_gemini(prompt)
    return self._parse_response(response, stage_progress.current_stage.value)
```

### 3. `backend/app/agents/coach/prompts.py` (+30 lines)
Add product_context parameter to coach prompt.

**Changes:**
- Add `product_context: str = ""` parameter to `build_coach_prompt`
- Inject product context into system instruction if non-empty

```python
def build_coach_prompt(
    salesperson_message: str,
    persona: CustomerPersona,
    stage_progress: EASYStageProgress,
    conversation_history: str,
    product_context: str = "",  # NEW
) -> str:
    # ... existing prompt building ...

    # NEW: Add product context if available
    if product_context:
        prompt += f"""

## Product Knowledge Context
The following information may be relevant to this conversation:

{product_context}

Use this product knowledge to provide specific, accurate hints about features, benefits, and handling objections.
"""

    return prompt
```

---

## Implementation Steps

### Day 1: Infrastructure Setup

1. **Add dependencies**
   ```bash
   cd backend
   # Edit pyproject.toml to add google-cloud-storage and pypdf
   uv sync
   ```

2. **Create Terraform resources**
   ```bash
   cd terraform
   # Create storage.tf
   # Create firestore.tf
   terraform init
   terraform plan
   terraform apply
   ```

3. **Upload PDFs to GCS**
   ```bash
   gsutil -m cp *.pdf gs://<PROJECT_ID>-sales-coach-knowledge/products/
   ```

4. **Wait for Firestore index build**
   - Check GCP Console → Firestore → Indexes
   - May take 30-60 minutes for index to become active

### Day 2-3: RAG Service Implementation

1. **Create RAG service**
   - Implement `app/services/rag_service.py`
   - Add helper functions for chunking, embedding, retrieval

2. **Create indexing script**
   - Implement `scripts/build_knowledge_index.py`
   - Load PDFs from GCS
   - Chunk and embed documents
   - Store in Firestore

3. **Run indexing script**
   ```bash
   cd backend
   uv run python scripts/build_knowledge_index.py
   ```

4. **Verify Firestore data**
   - Check Firestore Console
   - Should see ~800 documents in knowledge_chunks collection
   - Verify embedding field is populated (768 dimensions)

5. **Write unit tests**
   - Create `tests/unit/services/test_rag_service.py`
   - Mock Firestore for fast tests
   - Test chunking, embedding, retrieval logic

### Day 4: Integration with Coach Agent

1. **Modify analyzer.py**
   - Add RAG retrieval call before LLM
   - Handle exceptions gracefully (fallback to empty context)

2. **Update prompts.py**
   - Add product_context parameter
   - Inject context into system prompt

3. **Write integration tests**
   - Create `tests/integration/test_rag_integration.py`
   - Test end-to-end flow with sample PDF
   - Verify coach hint includes product details

4. **Local testing**
   ```bash
   # Start backend with Firestore emulator
   cd backend
   uv run pytest tests/integration/test_rag_integration.py -v
   ```

### Day 5: Deploy and Validate

1. **Run full test suite**
   ```bash
   cd backend
   uv run pytest
   uv run ruff check .
   uv run mypy app/
   ```

2. **Deploy to development**
   ```bash
   # Push to development branch
   git push origin feat/rag-phase-1-firestore-vector-search
   # Cloud Build will deploy automatically
   ```

3. **Smoke tests in dev environment**
   - Start training session
   - Send message: "Is this durable for kids?"
   - Verify hint mentions product-specific details

4. **Deploy to production** (after validation)
   - Create PR to main/development
   - Merge after review
   - Monitor Firestore query performance

---

## Testing Requirements

### Unit Tests
**File:** `tests/unit/services/test_rag_service.py`

Required test cases:
- `test_chunk_text_creates_chunks_with_overlap`
- `test_chunk_text_handles_empty_string`
- `test_embed_text_returns_correct_dimensions`
- `test_embed_text_mocked_response`
- `test_retrieve_queries_firestore_with_correct_params`
- `test_retrieve_formats_context_from_results`
- `test_retrieve_handles_empty_results`

### Integration Tests
**File:** `tests/integration/test_rag_integration.py`

Required scenarios:
1. **Living Room Furniture**
   - Persona: BUSY_PARENT
   - Message: "Is this durable for kids?"
   - Expected: Hint mentions stain-resistant fabric

2. **Bedroom Furniture**
   - Persona: DEMANDING_PROFESSIONAL
   - Message: "What's the quality?"
   - Expected: Hint references wood type, construction

3. **Objection Handling**
   - Persona: PRICE_RESISTANT
   - Message: "Too expensive"
   - Expected: Hint suggests financing options

### Manual Testing Checklist
- [ ] Start training session with BUSY_PARENT persona
- [ ] Ask: "Is this sectional good for kids and pets?"
- [ ] Verify coach hint includes "stain-resistant", "performance fabric", "easy to clean"
- [ ] Check logs for Firestore query latency (<400ms)
- [ ] Verify no errors in Cloud Run logs

---

## Performance Targets

| Metric | Target | Critical |
|--------|--------|----------|
| Firestore vector query latency | <200ms | <400ms |
| Index build time (one-time) | <5 min | <10 min |
| Total coach hint latency | <2.5s | <4s |
| Firestore reads per hint | 3-5 | 10 |

---

## Acceptance Criteria

### Phase 1 is complete when:
- [ ] Firestore `knowledge_chunks` collection created
- [ ] Vector index built and active in GCP Console
- [ ] 800+ documents in collection (8 PDFs × ~100 chunks each)
- [ ] Coach hint in TRAINING session mentions specific product feature
- [ ] Firestore query latency <400ms (check Cloud Run logs)
- [ ] No errors in Cloud Run logs related to RAG
- [ ] All unit tests pass (coverage >80%)
- [ ] All integration tests pass
- [ ] Manual test scenarios pass (3/3)
- [ ] PR merged to development
- [ ] Deployed to production

---

## Rollback Plan

### If issues arise:
1. **Quick rollback** (<10 minutes)
   ```bash
   gcloud run services update-traffic salescoach-backend \
     --to-revisions=PREVIOUS_REVISION=100 \
     --region us-central1
   ```

2. **Graceful degradation** (built-in)
   ```python
   try:
       product_context = await rag_service.retrieve(...)
   except Exception as e:
       logger.warning(f"RAG failed: {e}, using fallback")
       product_context = ""  # Generic hints still work
   ```

---

## Next Phase
After Phase 1 is complete and stable, proceed to:
**RAG_PHASE_2_IMPLEMENTATION.md** - Metadata filtering and persona-product binding

---

## Cost Estimate

**Phase 1 costs:** $0/month

- Firestore storage: 1.6MB (within 1GB free tier)
- Vector search queries: ~2,000/day (within 20K/day free tier)
- Gemini embeddings: One-time 800 chunks + 2,000 queries/day (within free tier)

Costs start if:
- >1GB stored (~500,000 chunks): $0.18/GB/month
- >20K reads/day: $0.06 per 100K reads
