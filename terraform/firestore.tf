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

# IMPORTANT: Firestore Vector Search is currently in preview (as of Feb 2026).
# For this collection (~200 docs) index builds complete in minutes, not the
# 30-60 min worst case. Monitor status in GCP Console: Firestore → Indexes.
#
# Embeddings are gemini-embedding-2 at 2048 dimensions (see Settings.rag_*).
# The vector field on every index must therefore be dimension = 2048.

# Bare vector index on the embedding field. Serves unfiltered find_nearest
# queries (FirestoreRAGService.retrieve with no metadata filters).
# The google provider requires >=2 fields blocks, so the implicit __name__
# field (which Firestore always appends) is declared explicitly to match the
# live single-vector-field index for import.
resource "google_firestore_index" "knowledge_chunks_vector" {
  project    = var.project_id
  collection = "knowledge_chunks"
  database   = google_firestore_database.database.name

  fields {
    field_path = "__name__"
    order      = "ASCENDING"
  }

  fields {
    field_path = "embedding"
    vector_config {
      dimension = 2048
      flat {}
    }
  }

  query_scope = "COLLECTION"
}

# Composite vector index: category + doc_type + embedding.
# Required by the coach's default RAG path, which filters
# .where("metadata.category").where("metadata.doc_type").find_nearest("embedding")
# (CONNECT / OBSERVE stages and the re-ranking path). Firestore requires the
# equality-filter fields to precede the vector field, in query order.
resource "google_firestore_index" "knowledge_chunks_category_doctype" {
  project    = var.project_id
  collection = "knowledge_chunks"
  database   = google_firestore_database.database.name

  fields {
    field_path = "metadata.category"
    order      = "ASCENDING"
  }

  fields {
    field_path = "metadata.doc_type"
    order      = "ASCENDING"
  }

  # Firestore auto-inserts __name__ ahead of the vector field in composite
  # vector indexes; declared explicitly so config matches the live index and
  # terraform doesn't force a destroy/recreate.
  fields {
    field_path = "__name__"
    order      = "ASCENDING"
  }

  fields {
    field_path = "embedding"
    vector_config {
      dimension = 2048
      flat {}
    }
  }

  query_scope = "COLLECTION"
}

# Composite vector index: category + doc_type + section_type + embedding.
# Required by the stage-narrowed RAG path (RECOMMEND -> agent_talking_points,
# EXECUTE -> objection_handlers), which adds a .where("metadata.section_type")
# filter before find_nearest.
resource "google_firestore_index" "knowledge_chunks_category_doctype_section" {
  project    = var.project_id
  collection = "knowledge_chunks"
  database   = google_firestore_database.database.name

  fields {
    field_path = "metadata.category"
    order      = "ASCENDING"
  }

  fields {
    field_path = "metadata.doc_type"
    order      = "ASCENDING"
  }

  fields {
    field_path = "metadata.section_type"
    order      = "ASCENDING"
  }

  # See note above: __name__ is auto-inserted before the vector field.
  fields {
    field_path = "__name__"
    order      = "ASCENDING"
  }

  fields {
    field_path = "embedding"
    vector_config {
      dimension = 2048
      flat {}
    }
  }

  query_scope = "COLLECTION"
}

# Composite scalar index: category + content_type.
# NOTE: legacy / currently unused - the ingestion pipeline writes metadata.doc_type,
# not metadata.content_type, so this indexes a field that no document carries and no
# query targets. Left in place (it already exists live and is harmless) pending a
# separate cleanup; do not rely on it.
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
# Composite index for evaluations collection
# ---------------------------------------------------------------------------
# Required by EvaluationRepository.list_by_user (used by the dashboard stats
# endpoint), which filters .where("user_id", "==", ...) and
# .order_by("created_at", direction=DESCENDING) — Firestore requires a
# composite index whenever an equality filter and an order_by target
# different fields.
resource "google_firestore_index" "evaluations_user_created" {
  project    = var.project_id
  collection = "evaluations"
  database   = google_firestore_database.database.name

  fields {
    field_path = "user_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "created_at"
    order      = "DESCENDING"
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
#   "chunk_id": "property_1_objection_handlers",
#   "content": "## OBJECTION HANDLERS & TALKING POINTS ...",
#   "embedding": Vector([0.123, -0.456, ...]),  // 2048 dimensions
#   "metadata": {
#     "source_file": "Property_1_Maple_Grove_Starter.md",
#     "category": "property_1",        // == persona.property_id
#     "doc_type": "property_listing",
#     "section_type": "objection_handlers",
#     "property_name": "Maple Grove Starter Home",
#     "chunk_index": 7,
#     "created_at": "2026-05-01T10:00:00Z"
#   }
# }
