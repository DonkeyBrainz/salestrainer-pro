# ---------------------------------------------------------------------------
# Scheduled hot/cold scaling for the backend Cloud Run service
# ---------------------------------------------------------------------------
# Cloud Run's min-instances isn't time-aware on its own, so two Cloud Scheduler
# jobs flip it via the Cloud Run Admin API (v2) on a daily cron:
#   - 10:00 America/New_York -> min_instance_count = 1 (warm for business hours)
#   - 16:00 America/New_York -> min_instance_count = 0 (scale to zero off-hours)
# Using the IANA timezone (not a fixed UTC offset) makes Cloud Scheduler handle
# the EST/EDT transition automatically, so the window stays 10am-4pm local time
# year-round.
#
# Deploys (backend-deploy.yml) intentionally omit --min-instances so they don't
# fight this schedule - gcloud run deploy preserves the existing scaling setting
# when the flag is left unspecified.

resource "google_service_account" "scheduler" {
  account_id   = "salestrainer-pro-scheduler-sa"
  display_name = "SalesTrainer Pro Scheduler"
  description  = "Service account used by Cloud Scheduler to toggle backend min-instances"

  depends_on = [google_project_service.apis]
}

# Least-privilege: only allowed to update the backend Cloud Run service, not
# project-wide run.admin.
resource "google_cloud_run_v2_service_iam_member" "scheduler_run_developer" {
  project  = var.project_id
  location = google_cloud_run_v2_service.backend.location
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

# Updating a Cloud Run service that runs as the backend SA requires actAs on
# that runtime SA (same reason cloudbuild_act_as_backend exists in iam.tf).
# Without this the PATCH returns PERMISSION_DENIED.
resource "google_service_account_iam_member" "scheduler_act_as_backend" {
  service_account_id = google_service_account.backend.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "backend_scale_up" {
  name      = "salestrainer-pro-backend-scale-up"
  region    = var.region
  schedule  = "0 10 * * *"
  time_zone = "America/New_York"

  http_target {
    http_method = "PATCH"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/services/${google_cloud_run_v2_service.backend.name}?updateMask=template.scaling.minInstanceCount"
    headers = {
      "Content-Type" = "application/json"
    }
    body = base64encode(jsonencode({
      template = {
        scaling = {
          minInstanceCount = 1
        }
      }
    }))

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  depends_on = [
    google_project_service.apis,
    google_cloud_run_v2_service_iam_member.scheduler_run_developer,
  ]
}

resource "google_cloud_scheduler_job" "backend_scale_down" {
  name      = "salestrainer-pro-backend-scale-down"
  region    = var.region
  schedule  = "0 16 * * *"
  time_zone = "America/New_York"

  http_target {
    http_method = "PATCH"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/services/${google_cloud_run_v2_service.backend.name}?updateMask=template.scaling.minInstanceCount"
    headers = {
      "Content-Type" = "application/json"
    }
    body = base64encode(jsonencode({
      template = {
        scaling = {
          minInstanceCount = 0
        }
      }
    }))

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  depends_on = [
    google_project_service.apis,
    google_cloud_run_v2_service_iam_member.scheduler_run_developer,
  ]
}
