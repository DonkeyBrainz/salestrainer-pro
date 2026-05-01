# Terraform state is stored in a GCS bucket.
#
# Before running `terraform init`, create this bucket manually:
#
#   Naming convention: {project-id}-terraform-state
#
#   gsutil mb gs://salescoach-494901-terraform-state
#   gsutil versioning set on gs://salescoach-494901-terraform-state

terraform {
  backend "gcs" {
    bucket = "salescoach-494901-terraform-state"
    prefix = "salestrainer-pro"
  }
}
