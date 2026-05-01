# ---------------------------------------------------------------------------
# Secret Manager
#
# Terraform creates the secret "containers" only. Populate values manually:
#
#   echo -n "value" | gcloud secrets versions add SECRET_NAME --data-file=-
#
# See documentation/CICD_GUIDE.md for the full list of commands.
# ---------------------------------------------------------------------------

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "google_oauth_client_id" {
  secret_id = "google-oauth-client-id"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "google_oauth_client_secret" {
  secret_id = "google-oauth-client-secret"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "jwt_secret_key" {
  secret_id = "jwt-secret-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Initial empty secret versions (so Cloud Run can start)
# ---------------------------------------------------------------------------

resource "google_secret_manager_secret_version" "gemini_api_key_placeholder" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = "placeholder-update-me"
}

resource "google_secret_manager_secret_version" "google_oauth_client_id_placeholder" {
  secret      = google_secret_manager_secret.google_oauth_client_id.id
  secret_data = "placeholder-update-me"
}

resource "google_secret_manager_secret_version" "google_oauth_client_secret_placeholder" {
  secret      = google_secret_manager_secret.google_oauth_client_secret.id
  secret_data = "placeholder-update-me"
}

resource "google_secret_manager_secret_version" "jwt_secret_key_placeholder" {
  secret      = google_secret_manager_secret.jwt_secret_key.id
  secret_data = "placeholder-update-me-with-random-string"
}
