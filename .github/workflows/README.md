# GitHub Actions — CI/CD

Path-filtered CI and Cloud Run deploys. GCP auth is **keyless via Workload Identity Federation** — the deploy/auth steps mint a GitHub OIDC token, build an `external_account` credential config, and `gcloud auth login --cred-file`. No third-party auth actions, no long-lived SA keys.

## Workflows

| File | Trigger | Does |
|------|---------|------|
| `backend-ci.yml` | PR to `main`/`development` on `backend/**`; `workflow_dispatch` | `uv sync --dev`, ruff check + format --check, mypy, pytest (coverage) on Python 3.13 |
| `frontend-ci.yml` | PR to `main`/`development` on `frontend/**`; `workflow_dispatch` | `npm ci`, `npm run typecheck`, `npm run test:run` on Node 20 |
| `backend-deploy.yml` | push to `main` on `backend/**`; `workflow_dispatch` | Re-runs quality gates, then builds/pushes image and deploys `salestrainer-pro-backend` |
| `frontend-deploy.yml` | push to `main` on `frontend/**`; `workflow_dispatch` | Fetches backend URL, builds with `VITE_API_BASE_URL`, deploys `salestrainer-pro-frontend` |
| `test-gcp-auth.yml` | `workflow_dispatch` only | Smoke-tests WIF auth (`gcloud run services list`) |

## Required config (repo-level)

`vars`: `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `GCP_PROJECT_ID`.
`secrets`: `LANGFUSE_PUBLIC_KEY` (public key passed as env; secret-manager secrets are referenced by name at deploy). Deploy jobs need `permissions: id-token: write`.

## Deploy details

Both deploy jobs: OIDC auth → describe the sibling service for its URL → `docker build`/`push` to Artifact Registry (`us-central1-docker.pkg.dev/$PROJECT/salestrainer-pro/{backend,frontend}`, tagged with short SHA + `latest`) → `gcloud run deploy` in `us-central1` as `salestrainer-pro-backend-sa`, `--allow-unauthenticated`.

Runtime config lives **in the deploy command, not the image**:
- **Backend** — secrets `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID/SECRET`, `SECRET_KEY`(jwt), `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` (Nova/Bedrock), `LANGFUSE_SECRET_KEY`; env sets `LIVE_PROVIDER=nova` + allowlist `["gemini","nova"]`, `RAG_ENABLED`, `FIRESTORE_DATABASE=(default)`, `AWS_REGION=us-east-1`, Langfuse endpoint, and CORS/`GOOGLE_REDIRECT_URI` derived from the frontend URL. `--min-instances` is intentionally omitted (owned by the Terraform scheduler jobs).
- **Frontend** — backend URL baked at build time via `--build-arg VITE_API_BASE_URL`, so a backend URL change requires a frontend redeploy.

Credentials are written to `/tmp` and removed in an `if: always()` cleanup step.

## Rollback

```bash
gcloud run revisions list --service=salestrainer-pro-backend --region=us-central1
gcloud run services update-traffic salestrainer-pro-backend \
  --region=us-central1 --to-revisions=<REVISION>=100
```
