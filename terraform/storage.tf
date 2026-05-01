# ---------------------------------------------------------------------------
# GCS Bucket for Training Knowledge Documents
# ---------------------------------------------------------------------------
# This bucket stores the training materials and reference documents that will be
# indexed for RAG retrieval. The backend service account needs read access
# to load documents during the indexing process.

resource "google_storage_bucket" "knowledge_bucket" {
  name          = "${var.project_id}-salestrainer-pro-knowledge"
  location      = var.region
  force_destroy = false  # Prevent accidental deletion of documents

  uniform_bucket_level_access = true

  versioning {
    enabled = true  # Keep version history of PDFs
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions = 3  # Keep last 3 versions only
    }
  }
}

# Grant backend service account read access to documents
resource "google_storage_bucket_iam_member" "backend_storage_reader" {
  bucket = google_storage_bucket.knowledge_bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.backend.email}"
}

# ---------------------------------------------------------------------------
# Expected bucket structure after manual upload:
# ---------------------------------------------------------------------------
# gs://<PROJECT_ID>-salestrainer-pro-knowledge/
#   └── training_materials/
#       ├── sales_methodology.pdf
#       ├── industry_guide_real_estate.pdf
#       ├── industry_guide_saas.pdf
#       ├── industry_guide_automotive.pdf
#       ├── objection_handling.pdf
#       ├── customer_personas.pdf
#       ├── conversation_examples.pdf
#       ├── best_practices.pdf
#       └── advanced_techniques.pdf
