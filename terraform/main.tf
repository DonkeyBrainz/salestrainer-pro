# ---------------------------------------------------------------------------
# Required APIs
# ---------------------------------------------------------------------------

locals {
  services = [
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.services)
  project  = var.project_id
  service  = each.value

  disable_on_destroy = false
}

# ---------------------------------------------------------------------------
# Artifact Registry
# ---------------------------------------------------------------------------

resource "google_artifact_registry_repository" "salestrainer_pro" {
  location      = var.region
  repository_id = "salestrainer-pro"
  description   = "Docker images for SalesTrainer Pro backend and frontend"
  format        = "DOCKER"

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Cloud Run - Backend
# ---------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "backend" {
  name     = "salestrainer-pro-backend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.backend.email

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    timeout = "300s"

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
      }

      # --- Secrets from Secret Manager ---
      # Populated with placeholder values initially
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GOOGLE_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_oauth_client_id.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GOOGLE_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_oauth_client_secret.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.jwt_secret_key.secret_id
            version = "latest"
          }
        }
      }

      # --- Plain environment variables ---
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "FIRESTORE_DATABASE"
        value = "salestrainer-pro"
      }
      env {
        name  = "LOG_JSON"
        value = "true"
      }
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        period_seconds = 30
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret.gemini_api_key,
    google_secret_manager_secret.google_oauth_client_id,
    google_secret_manager_secret.google_oauth_client_secret,
    google_secret_manager_secret.jwt_secret_key,
  ]
}

# Allow unauthenticated access (app handles its own auth)
resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = var.project_id
  location = google_cloud_run_v2_service.backend.location
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ---------------------------------------------------------------------------
# Cloud Run - Frontend
# ---------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "frontend" {
  name     = "salestrainer-pro-frontend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    timeout = "60s"

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      startup_probe {
        http_get {
          path = "/"
          port = 8080
        }
        initial_delay_seconds = 2
        period_seconds        = 5
        failure_threshold     = 3
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# Allow unauthenticated access
resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = google_cloud_run_v2_service.frontend.location
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
