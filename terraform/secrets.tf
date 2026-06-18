# ---------------------------------------------------------------------------
# Secret Manager
#
# Terraform creates the secret "containers" only. Secret VALUES (versions) are
# populated and rotated manually / out of band - Terraform does not track them:
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

# NOTE: The initial "placeholder-update-me" bootstrap versions that used to live
# here have been removed. Real secret values are managed manually (versions 2+),
# so Terraform no longer tracks secret versions - only the containers above.
