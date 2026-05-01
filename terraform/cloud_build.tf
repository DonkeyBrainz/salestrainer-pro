# ---------------------------------------------------------------------------
# Cloud Build Triggers - DISABLED FOR INITIAL DEPLOYMENT
#
# Pre-requisite: Connect the GitHub repo to Cloud Build via the Console:
#   Cloud Build > Triggers > Connect Repository > GitHub (Cloud Build App)
#
# These triggers use the `github` block which relies on that connection.
# Uncomment after connecting your GitHub repository to Cloud Build.
# ---------------------------------------------------------------------------

/*

# ---------------------------------------------------------------------------
# Backend - Deploy on push to main
# ---------------------------------------------------------------------------

resource "google_cloudbuild_trigger" "backend_deploy" {
  name        = "salescoach-backend-deploy"
  description = "Build and deploy backend on push to main"
  location    = var.region

  service_account = google_service_account.cloudbuild.id

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = "^main$"
    }
  }

  included_files = ["backend/**"]
  filename       = "backend/cloudbuild.yaml"

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Backend - CI checks on pull request
# ---------------------------------------------------------------------------

resource "google_cloudbuild_trigger" "backend_ci" {
  name        = "salescoach-backend-ci"
  description = "Lint, typecheck, and test backend on pull request"
  location    = var.region

  service_account = google_service_account.cloudbuild.id

  github {
    owner = var.github_owner
    name  = var.github_repo
    pull_request {
      branch = "^main$"
    }
  }

  included_files = ["backend/**"]
  filename       = "backend/cloudbuild-ci.yaml"

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Frontend - Deploy on push to main
# ---------------------------------------------------------------------------

resource "google_cloudbuild_trigger" "frontend_deploy" {
  name        = "salescoach-frontend-deploy"
  description = "Build and deploy frontend on push to main"
  location    = var.region

  service_account = google_service_account.cloudbuild.id

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = "^main$"
    }
  }

  included_files = ["frontend/**"]
  filename       = "frontend/cloudbuild.yaml"

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Frontend - CI checks on pull request
# ---------------------------------------------------------------------------

resource "google_cloudbuild_trigger" "frontend_ci" {
  name        = "salescoach-frontend-ci"
  description = "Typecheck and test frontend on pull request"
  location    = var.region

  service_account = google_service_account.cloudbuild.id

  github {
    owner = var.github_owner
    name  = var.github_repo
    pull_request {
      branch = "^main$"
    }
  }

  included_files = ["frontend/**"]
  filename       = "frontend/cloudbuild-ci.yaml"

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  depends_on = [google_project_service.apis]
}
*/
