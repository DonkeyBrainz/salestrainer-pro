# ---------------------------------------------------------------------------
# Secret Manager
#
# Terraform creates the secret "containers" only. Secret VALUES (versions) are
# populated and rotated manually / out of band - Terraform does not track them:
#
#   echo -n "value" | gcloud secrets versions add SECRET_NAME --data-file=-
#
# See .github/workflows/README.md for how these are mounted at deploy time.
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

# Langfuse tracing (LANGFUSE_SECRET_KEY). Public key + base URL are non-secret
# and passed as plain env vars by the deploy workflow.
resource "google_secret_manager_secret" "langfuse_secret_key" {
  secret_id = "langfuse-secret-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# Amazon Bedrock (Nova Sonic) credentials for the least-privilege IAM user
# scoped to bedrock:InvokeModel* on the Nova Sonic model. Mounted as
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY at deploy time.
resource "google_secret_manager_secret" "aws_bedrock_access_key_id" {
  secret_id = "aws-bedrock-access-key-id"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "aws_bedrock_secret_access_key" {
  secret_id = "aws-bedrock-secret-access-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# NOTE: The initial "placeholder-update-me" bootstrap versions that used to live
# here have been removed. Real secret values are managed manually (versions 2+),
# so Terraform no longer tracks secret versions - only the containers above.
#
# The langfuse + aws-bedrock containers above were created out of band before
# they were codified here. Reconcile state before any apply (they already exist
# in GCP, so a plain apply would fail "already exists"):
#
#   terraform import google_secret_manager_secret.langfuse_secret_key \
#     projects/PROJECT_ID/secrets/langfuse-secret-key
#   terraform import google_secret_manager_secret.aws_bedrock_access_key_id \
#     projects/PROJECT_ID/secrets/aws-bedrock-access-key-id
#   terraform import google_secret_manager_secret.aws_bedrock_secret_access_key \
#     projects/PROJECT_ID/secrets/aws-bedrock-secret-access-key
