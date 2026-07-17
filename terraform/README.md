# Terraform — SalesTrainer Pro GCP infra

Bootstraps the GCP footprint for SalesTrainer Pro. **Terraform owns the service shells + IAM only** — the live Cloud Run containers (image, env vars, secrets, min-instances) are owned by CI (`gcloud run deploy`) and Cloud Scheduler, and are excluded via `lifecycle.ignore_changes`. Do not blanket-`apply` expecting to manage runtime config here; you will only revert the placeholder image.

## Layout

| File | Contents |
|------|----------|
| `provider.tf` | google provider `~> 5.0`, TF `>= 1.5` |
| `backend.tf` | GCS remote state (`salescoach-494901-terraform-state`, prefix `salestrainer-pro`) |
| `main.tf` | Required APIs, Artifact Registry (`salestrainer-pro`), both Cloud Run services + public invoker IAM |
| `secrets.tf` | Secret **containers** only (values managed out of band) |
| `iam.tf` | Backend + Cloud Build service accounts and role bindings |
| `firestore.tf` | Firestore DB + vector/composite indexes |
| `storage.tf` | Knowledge GCS bucket (RAG source docs) |
| `scheduler.tf` | Cloud Scheduler jobs for time-based min-instance scaling |
| `cloud_build.tf` | Cloud Build triggers — **commented out** (CI runs via GitHub Actions instead) |
| `variables.tf` / `outputs.tf` | Inputs (`project_id`, `region`, `github_owner`, `github_repo`) and outputs (service URLs, AR repo) |

## Usage

```bash
cp terraform.tfvars.example terraform.tfvars   # set project_id, region, github_owner/repo
# One-time: create the state bucket before init (see backend.tf)
gsutil mb gs://salescoach-494901-terraform-state && gsutil versioning set on gs://...
terraform init && terraform plan && terraform apply
```

## Cloud Run

Two `google_cloud_run_v2_service`: `salestrainer-pro-backend` (port 8000, 2 CPU / 1Gi, `/health` probes) and `salestrainer-pro-frontend` (port 8080, 1 CPU / 512Mi). Both start on the `cloudrun/hello` placeholder and are public (`allUsers` → `run.invoker`); the app enforces its own auth. `ignore_changes` covers image/env/scaling so CI deploys and the scheduler aren't reverted.

## Secrets

Terraform creates the containers; **values (versions) are populated manually** and not tracked:

```bash
echo -n "VALUE" | gcloud secrets versions add SECRET_NAME --data-file=-
```

Backend-consumed secrets: `gemini-api-key`, `jwt-secret-key`, `google-oauth-client-id`, `google-oauth-client-secret`. (CI also wires additional secrets not defined here — `aws-bedrock-*` for Nova, `langfuse-secret-key`.) The backend SA gets `secretAccessor` on each.

## Firestore

Native mode. Vector indexes on `knowledge_chunks.embedding` at **2048 dims** (`gemini-embedding-2`) power RAG: a bare vector index plus composite indexes (`category`+`doc_type`, +`section_type`) matching the coach's filtered `find_nearest` paths. Note the explicit `__name__` field in vector indexes — Firestore auto-inserts it, so it's declared to match the live index and avoid destroy/recreate churn. Also a composite scalar index on `evaluations` (`user_id` + `created_at DESC`) for the dashboard. `knowledge_chunks_filtered` is legacy/unused (indexes `content_type`, which no doc writes) — left in place, don't rely on it.

## Scheduling

`min_instance_count` isn't time-aware, so two Cloud Scheduler jobs PATCH the backend via the Cloud Run Admin API: scale to 1 at 10:00 and to 0 at 16:00 `America/New_York` (IANA tz handles EST/EDT). A dedicated least-privilege scheduler SA holds `run.developer` on the backend service + `actAs` on the backend runtime SA. Deploys omit `--min-instances` so they don't fight the schedule.

## State & ops

State: `gs://salescoach-494901-terraform-state/salestrainer-pro`. Vector index builds are usually minutes (30-60 min worst case) for this ~200-doc collection.

```bash
gcloud run services list --platform managed
gcloud logging read "resource.type=cloud_run_revision"
```
