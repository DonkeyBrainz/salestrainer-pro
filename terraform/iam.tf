# ---------------------------------------------------------------------------
# Service Accounts
# ---------------------------------------------------------------------------

resource "google_service_account" "backend" {
  account_id   = "salestrainer-pro-backend-sa"
  display_name = "SalesTrainer Pro Backend"
  description  = "Service account for the SalesTrainer Pro backend Cloud Run service"

  depends_on = [google_project_service.apis]
}

resource "google_service_account" "cloudbuild" {
  account_id   = "salestrainer-pro-cloudbuild-sa"
  display_name = "SalesTrainer Pro Cloud Build"
  description  = "Service account for SalesTrainer Pro Cloud Build CI/CD pipelines"

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Backend SA permissions
# ---------------------------------------------------------------------------

# Access Firestore
resource "google_project_iam_member" "backend_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Read secrets at runtime
resource "google_secret_manager_secret_iam_member" "backend_gemini" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_oauth_id" {
  secret_id = google_secret_manager_secret.google_oauth_client_id.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_oauth_secret" {
  secret_id = google_secret_manager_secret.google_oauth_client_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_jwt" {
  secret_id = google_secret_manager_secret.jwt_secret_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_langfuse" {
  secret_id = google_secret_manager_secret.langfuse_secret_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_aws_bedrock_access_key_id" {
  secret_id = google_secret_manager_secret.aws_bedrock_access_key_id.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_aws_bedrock_secret_access_key" {
  secret_id = google_secret_manager_secret.aws_bedrock_secret_access_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

# ---------------------------------------------------------------------------
# Cloud Build SA permissions
# ---------------------------------------------------------------------------

# Deploy to Cloud Run
resource "google_project_iam_member" "cloudbuild_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# Push images to Artifact Registry
resource "google_project_iam_member" "cloudbuild_ar_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# Act as the backend service account when deploying Cloud Run
resource "google_service_account_iam_member" "cloudbuild_act_as_backend" {
  service_account_id = google_service_account.backend.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# View Cloud Run services (needed to read backend URL during frontend deploy)
resource "google_project_iam_member" "cloudbuild_run_viewer" {
  project = var.project_id
  role    = "roles/run.viewer"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# Write build logs
resource "google_project_iam_member" "cloudbuild_logs_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}
