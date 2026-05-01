# ---------------------------------------------------------------------------
# Firestore Database
# ---------------------------------------------------------------------------
# Creates the Firestore database in Native mode for NoSQL document storage

resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Firestore Indexes for Vector Search
# ---------------------------------------------------------------------------
# These indexes enable vector similarity search on the knowledge_chunks
# collection. Vector search is used for RAG (Retrieval Augmented Generation)
# to find relevant training content for sales coaching.

# IMPORTANT: Firestore Vector Search is currently in preview (as of Feb 2026)
# The index creation may take 30-60 minutes to complete.
# Monitor status in GCP Console: Firestore → Indexes

# Vector search index on embedding field (768 dimensions from Gemini)
resource "google_firestore_index" "knowledge_chunks_vector" {
  project    = var.project_id
  collection = "knowledge_chunks"
  database   = google_firestore_database.database.name

  fields {
    field_path = "embedding"
    vector_config {
      dimension = 768  # Gemini text-embedding-004 produces 768-dim vectors
      flat {}          # Use flat index for <10K documents (faster build)
    }
  }

  # Enable filtering by category during vector search
  fields {
    field_path = "metadata.category"
    order      = "ASCENDING"
  }

  query_scope = "COLLECTION"
}

# Composite index for metadata filtering (Phase 2)
# Allows filtering by both category AND content_type before vector search
resource "google_firestore_index" "knowledge_chunks_filtered" {
  project    = var.project_id
  collection = "knowledge_chunks"
  database   = google_firestore_database.database.name

  fields {
    field_path = "metadata.category"
    order      = "ASCENDING"
  }

  fields {
    field_path = "metadata.content_type"
    order      = "ASCENDING"
  }

  query_scope = "COLLECTION"
}

# ---------------------------------------------------------------------------
# Expected Firestore document structure:
# ---------------------------------------------------------------------------
# Collection: knowledge_chunks
# Document ID: auto-generated
#
# {
#   "chunk_id": "sales_methodology_001",
#   "content": "The C.O.R.E. framework consists of...",
#   "embedding": Vector([0.123, -0.456, ...]),  // 768 dimensions
#   "metadata": {
#     "source_file": "sales_methodology.pdf",
#     "page": 3,
#     "category": "objection_handling",
#     "content_type": "technique",
#     "chunk_index": 1,
#     "created_at": "2026-02-17T10:00:00Z"
#   }
# }
