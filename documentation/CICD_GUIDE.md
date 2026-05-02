# CI/CD Guide - SalesTrainer Pro on GCP

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [How the Pieces Fit Together](#how-the-pieces-fit-together)
3. [GCP Services Used](#gcp-services-used)
4. [Secrets Management](#secrets-management)
5. [Terraform Infrastructure](#terraform-infrastructure)
6. [Dockerfiles](#dockerfiles)
7. [GitHub Actions Pipelines](#github-actions-pipelines)
8. [Workload Identity Federation Setup](#workload-identity-federation-setup)
9. [Implementation Sequence](#implementation-sequence)
10. [Manual Setup Checklist](#manual-setup-checklist)
11. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
                          +-----------------+
                          |     GitHub      |
                          |  (source code)  |
                          +--------+--------+
                                   |
                          push to main / PR
                                   |
                          +--------v--------+
                          |  GitHub Actions |
                          |  (CI/CD runner) |
                          +--------+--------+
                                   |
                    +--------------+--------------+
                    |                             |
           backend/** changed?          frontend/** changed?
                    |                             |
              +-----v-----+                +-----v-----+
              | lint/test  |                |  test     |
              | type check |                | type check|
              | build img  |                | build img |
              | push to AR |                | push to AR|
              | deploy CR  |                | deploy CR |
              +-----------+                 +-----------+
                    |                             |
           +-------v-------+             +-------v-------+
           |   Cloud Run   |             |   Cloud Run   |
           | salestrainer- |             | salestrainer- |
           | pro-backend   |             | pro-frontend  |
           |  (FastAPI)    |             |   (nginx)     |
           +-------+-------+             +---------------+
                   |
          +--------+--------+
          |                 |
    +-----v-----+    +-----v-----+
    | Firestore |    | Gemini API|
    +----------+     +-----------+
```

**What happens when you push to `main`:**

1. GitHub Actions detects the push
2. Path filters determine which workflow runs (`backend/**` or `frontend/**`)
3. Quality gates run first: lint, type check, tests
4. On success: Docker image is built, pushed to Artifact Registry, deployed to Cloud Run
5. Cloud Run starts serving the new container (zero-downtime rolling update)

For PRs, only quality gates run — no deployment.

---

## How the Pieces Fit Together

### Terraform vs GitHub Actions — who does what?

| Concern | Managed by | Why |
|---------|-----------|-----|
| Cloud Run service definitions | Terraform | Infrastructure that rarely changes (memory, CPU, scaling) |
| Artifact Registry | Terraform | Created once, used forever |
| Secret Manager secrets | Terraform | Creates the secret "containers"; values populated manually |
| Service accounts + IAM | Terraform | Security config, version-controlled |
| Workload Identity Pool/Provider | Terraform | WIF setup for GitHub Actions |
| **Which Docker image is running** | **GitHub Actions** | Changes on every deploy |
| **Secret values** | **You, manually** | Never in code, never in Terraform state |

**Think of it this way**: Terraform builds the stage (infrastructure). GitHub Actions performs the show (deployments).

### Authentication: Workload Identity Federation

GitHub Actions authenticates to GCP without any service account keys. Instead, GitHub's OIDC token is exchanged for a short-lived GCP access token via Workload Identity Federation (WIF).

```
GitHub Actions runner
       |
       | OIDC token (from $ACTIONS_ID_TOKEN_REQUEST_URL)
       v
GCP Workload Identity Pool
       |
       | exchanges token, impersonates SA
       v
GCP Service Account (salestrainer-pro-backend-sa)
       |
       | short-lived access token
       v
Artifact Registry + Cloud Run APIs
```

No long-lived credentials are stored anywhere. The WIF provider validates that the OIDC token came from your specific GitHub repo.

### The frontend-backend URL problem

The frontend needs to know the backend URL at build time (baked into the JS bundle via `VITE_API_BASE_URL`). The backend URL comes from Cloud Run.

**Solution**: The frontend workflow fetches the backend URL from Cloud Run before building:

```yaml
- name: Get backend URL
  run: |
    URL=$(gcloud run services describe salestrainer-pro-backend \
      --region=${{ env.REGION }} \
      --format='value(status.url)')
    echo "url=$URL" >> $GITHUB_OUTPUT
```

If you later set up a custom domain, hardcode it and skip this step.

---

## GCP Services Used

| Service | Purpose | Cost Model |
|---------|---------|-----------|
| **Cloud Run** | Runs containers (backend + frontend) | Pay per request + CPU/memory while handling requests. Free tier: 2M requests/month |
| **Artifact Registry** | Stores Docker images | Storage cost (~$0.10/GB/month). First 500MB free |
| **Secret Manager** | Stores API keys, OAuth creds | $0.06 per 10,000 access operations. 6 secret versions free |
| **Firestore** | Database | Per-read/write pricing. Free tier: 50K reads, 20K writes/day |
| **Cloud Storage** | Terraform state file | ~$0.02/GB/month. Negligible for state files |
| **IAM / WIF** | Keyless GitHub Actions auth | No additional cost |

**Enable required APIs** (one-time):
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  firestore.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com
```

---

## Secrets Management

### Layer 1: GCP Secret Manager (runtime secrets)

These are secrets your backend reads at runtime. Cloud Run injects them as environment variables.

**Secrets to create:**

| Secret Name | Value | Used By |
|-------------|-------|---------|
| `gemini-api-key` | Your Gemini API key | Backend - Gemini API calls |
| `google-oauth-client-id` | Google OAuth 2.0 client ID | Backend - user authentication |
| `google-oauth-client-secret` | Google OAuth 2.0 client secret | Backend - user authentication |
| `jwt-secret-key` | Random 32+ char string | Backend - JWT signing |

**How to populate them:**

```bash
export PROJECT_ID=your-gcp-project-id
gcloud config set project $PROJECT_ID

echo -n "your-actual-gemini-api-key" | \
  gcloud secrets create gemini-api-key --data-file=-

echo -n "your-oauth-client-id.apps.googleusercontent.com" | \
  gcloud secrets create google-oauth-client-id --data-file=-

echo -n "your-oauth-client-secret" | \
  gcloud secrets create google-oauth-client-secret --data-file=-

openssl rand -base64 32 | tr -d '\n' | \
  gcloud secrets create jwt-secret-key --data-file=-
```

**To update a secret:**
```bash
echo -n "new-value" | gcloud secrets versions add gemini-api-key --data-file=-

# Redeploy to pick it up (`:latest` always points to newest version)
gcloud run services update salestrainer-pro-backend --region=us-central1 \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest
```

### Layer 2: GitHub Repository Variables

GitHub Actions reads these as `${{ vars.VARIABLE_NAME }}`. These are **not** secrets — they're configuration values. Set them under **Settings → Secrets and variables → Actions → Variables**:

| Variable | Value | Purpose |
|----------|-------|---------|
| `GCP_PROJECT_ID` | your-gcp-project-id | GCP project to deploy into |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID` | WIF provider path for OIDC exchange |
| `GCP_SERVICE_ACCOUNT` | `salestrainer-pro-backend-sa@PROJECT_ID.iam.gserviceaccount.com` | SA to impersonate during deploy |

**How to get `GCP_WORKLOAD_IDENTITY_PROVIDER`:**
```bash
# After running terraform apply:
terraform output workload_identity_provider
```

### Layer 3: What NOT to put in secrets

Regular environment variables go directly in the Cloud Run deploy command, not in Secret Manager:

| Variable | Why not a secret |
|----------|-----------------|
| `GCP_PROJECT_ID` | Not sensitive |
| `ENVIRONMENT` | Not sensitive |
| `FIRESTORE_DATABASE` | Not sensitive |
| `CORS_ORIGINS` | Not sensitive |
| `GOOGLE_REDIRECT_URI` | Not sensitive |
| `LOG_LEVEL` | Not sensitive |

---

## Terraform Infrastructure

### Project structure

```
terraform/
├── provider.tf              # GCP provider + required APIs
├── backend.tf               # Terraform state (GCS bucket)
├── variables.tf             # Input variables (project_id, region)
├── main.tf                  # Artifact Registry + Cloud Run services
├── secrets.tf               # Secret Manager secret definitions
├── iam.tf                   # Service accounts + WIF + permissions
├── outputs.tf               # Outputs (service URLs, WIF provider path)
├── terraform.tfvars.example # Example variable values
└── .gitignore               # Exclude state files and .terraform/
```

**Key resources created by Terraform:**
- Artifact Registry repo `salestrainer-pro`
- Cloud Run services `salestrainer-pro-backend` and `salestrainer-pro-frontend`
- Service account `salestrainer-pro-backend-sa` with roles for Firestore, Secret Manager, Gemini
- Workload Identity Pool and Provider for GitHub Actions keyless auth
- IAM binding allowing the GitHub repo to impersonate the service account

### Terraform state bucket (manual, one-time)

```bash
export PROJECT_ID=your-gcp-project-id

gcloud storage buckets create gs://${PROJECT_ID}-terraform-state \
  --project=$PROJECT_ID \
  --location=us-central1 \
  --uniform-bucket-level-access \
  --public-access-prevention

gcloud storage buckets update gs://${PROJECT_ID}-terraform-state --versioning
```

### Running Terraform

```bash
cd terraform/

terraform init

terraform plan -var="project_id=your-project-id"

terraform apply -var="project_id=your-project-id"

# After apply, grab the WIF provider value for GitHub Variables
terraform output workload_identity_provider
terraform output backend_url
terraform output frontend_url
```

---

## Dockerfiles

### Backend Dockerfile (multi-stage)

```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock* ./
RUN uv pip install --system --no-cache .

# Stage 2: Runtime
FROM python:3.11-slim
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY app/ ./app/
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile (multi-stage)

```dockerfile
# Stage 1: Build React app
FROM node:20-alpine AS builder
WORKDIR /build
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

**Key decisions:**
- `VITE_API_BASE_URL` passed as build arg — baked into JS bundle at build time
- nginx on port 8080 (Cloud Run convention)
- No node_modules in final image

### nginx.conf (frontend)

```nginx
server {
    listen 8080;
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing: all paths serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets aggressively (Vite adds content hashes)
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;
}
```

---

## GitHub Actions Pipelines

Both workflows live in `.github/workflows/`. They use GitHub's built-in OIDC token for keyless GCP authentication — no service account JSON files anywhere.

### Backend pipeline (`.github/workflows/backend-deploy.yml`)

**Triggers**: Push to `main` with changes under `backend/**`

**Steps:**
1. Python 3.11 setup + `uv` install
2. `uv run ruff check app/` — lint
3. `uv run mypy app/` — type check
4. `uv run pytest --cov=app` — tests with coverage
5. Authenticate to GCP via WIF (OIDC token → access token)
6. Fetch frontend URL from Cloud Run (for CORS env var)
7. Build and push Docker image to Artifact Registry
8. `gcloud run deploy salestrainer-pro-backend` with secrets + env vars

**Key deploy flags:**
```yaml
gcloud run deploy salestrainer-pro-backend \
  --image=us-central1-docker.pkg.dev/PROJECT/salestrainer-pro/backend:SHA \
  --service-account=salestrainer-pro-backend-sa@PROJECT.iam.gserviceaccount.com \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest,... \
  --set-env-vars='^||^GCP_PROJECT_ID=...||CORS_ORIGINS=[...]||...'
```

The `'^||^'` delimiter is required when env var values contain commas (like the CORS array).

### Frontend pipeline (`.github/workflows/frontend-deploy.yml`)

**Triggers**: Push to `main` with changes under `frontend/**`

**Steps:**
1. Node 20 setup
2. `npm ci`
3. `npm run typecheck`
4. `npm run test:run`
5. Authenticate to GCP via WIF
6. Fetch backend URL from Cloud Run (injected as `VITE_API_BASE_URL` build arg)
7. Build and push Docker image to Artifact Registry
8. `gcloud run deploy salestrainer-pro-frontend`

**Key deploy flags:**
```yaml
gcloud run deploy salestrainer-pro-frontend \
  --image=us-central1-docker.pkg.dev/PROJECT/salestrainer-pro/frontend:SHA \
  --service-account=salestrainer-pro-backend-sa@PROJECT.iam.gserviceaccount.com \
  --allow-unauthenticated
```

### GCP Authentication in workflows (no third-party actions)

Both workflows authenticate to GCP manually using the GitHub OIDC token — no `google-github-actions/auth` action required:

```bash
# 1. Fetch OIDC token from GitHub's token endpoint
OIDC_TOKEN=$(curl -sS \
  -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
  "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=https://iam.googleapis.com/$WIF_PROVIDER" \
  | jq -r '.value')

# 2. Write token to file
echo "$OIDC_TOKEN" > /tmp/oidc_token

# 3. Create external account credential config
cat > /tmp/gha_creds.json << EOF
{
  "type": "external_account",
  "audience": "//iam.googleapis.com/$WIF_PROVIDER",
  "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
  "token_url": "https://sts.googleapis.com/v1/token",
  "credential_source": { "file": "/tmp/oidc_token", "format": { "type": "text" } },
  "service_account_impersonation_url": "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/$SA:generateAccessToken"
}
EOF

# 4. Authenticate gcloud
gcloud auth login --cred-file=/tmp/gha_creds.json --quiet
```

Credentials are cleaned up at the end of every run with `if: always()`.

---

## Workload Identity Federation Setup

WIF is configured via Terraform. Here's what it creates:

```hcl
# Workload Identity Pool
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions Pool"
}

# Provider: validates tokens from your specific GitHub repo
resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions-provider"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  attribute_condition = "attribute.repository == 'YOUR_GITHUB_ORG/YOUR_REPO'"
}

# Allow GitHub Actions to impersonate the backend service account
resource "google_service_account_iam_member" "github_wif" {
  service_account_id = google_service_account.backend.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${pool_name}/attribute.repository/YOUR_GITHUB_ORG/YOUR_REPO"
}
```

After `terraform apply`, set the GitHub repository variable:
```
GCP_WORKLOAD_IDENTITY_PROVIDER = projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider
```

---

## Implementation Sequence

| Step | Scope | Depends On |
|------|-------|------------|
| 1 | Create Terraform state bucket (manual) | GCP project exists, APIs enabled |
| 2 | `terraform apply` — creates all infrastructure | Step 1 |
| 3 | Populate Secret Manager values (manual) | Step 2 |
| 4 | Set GitHub repository variables | Step 2 (need WIF provider path from outputs) |
| 5 | Push backend code → triggers backend workflow | Steps 3, 4 |
| 6 | Push frontend code → triggers frontend workflow | Step 5 (needs backend URL) |
| 7 | Update OAuth redirect URIs with production frontend URL | Step 6 |

Steps 3 and 4 can be done in parallel. Steps 5 and 6 must be sequential (frontend bakes in backend URL).

---

## Manual Setup Checklist

### 1. Enable GCP APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  firestore.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  storage.googleapis.com
```

### 2. Create Terraform state bucket

```bash
export PROJECT_ID=$(gcloud config get-value project)

gcloud storage buckets create gs://${PROJECT_ID}-terraform-state \
  --location=us-central1 \
  --uniform-bucket-level-access \
  --public-access-prevention

gcloud storage buckets update gs://${PROJECT_ID}-terraform-state --versioning
```

### 3. Run Terraform

```bash
cd terraform/
terraform init
terraform apply -var="project_id=$PROJECT_ID"

# Save these outputs
terraform output workload_identity_provider
terraform output backend_service_account
```

### 4. Populate Secret Manager

```bash
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
echo -n "YOUR_CLIENT_ID.apps.googleusercontent.com" | gcloud secrets create google-oauth-client-id --data-file=-
echo -n "YOUR_CLIENT_SECRET" | gcloud secrets create google-oauth-client-secret --data-file=-
openssl rand -base64 32 | tr -d '\n' | gcloud secrets create jwt-secret-key --data-file=-
```

### 5. Set GitHub Repository Variables

In your GitHub repo: **Settings → Secrets and variables → Actions → Variables**

| Name | Value |
|------|-------|
| `GCP_PROJECT_ID` | your-project-id |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | (from `terraform output workload_identity_provider`) |
| `GCP_SERVICE_ACCOUNT` | (from `terraform output backend_service_account`) |

### 6. Update OAuth Redirect URIs

After frontend deploys, add its URL to your Google OAuth client:

1. [APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
2. Edit your OAuth 2.0 Client ID
3. Add to **Authorized redirect URIs**: `https://salestrainer-pro-frontend-HASH-uc.a.run.app/auth/callback`
4. Add to **Authorized JavaScript origins**: `https://salestrainer-pro-frontend-HASH-uc.a.run.app`

Get the exact URL: `gcloud run services describe salestrainer-pro-frontend --region=us-central1 --format='value(status.url)'`

---

## Troubleshooting

### GitHub Actions: "Permission denied" / WIF auth fails

Verify the workload identity provider is configured correctly:
```bash
gcloud iam workload-identity-pools providers describe github-actions-provider \
  --workload-identity-pool=github-actions-pool \
  --location=global
```

Check the `attribute_condition` matches your GitHub org/repo exactly (case-sensitive).

Verify the SA IAM binding:
```bash
gcloud iam service-accounts get-iam-policy \
  salestrainer-pro-backend-sa@$PROJECT_ID.iam.gserviceaccount.com
```

### GitHub Actions: "Secret not found" on deploy

Verify secrets exist and the SA can access them:
```bash
gcloud secrets list
gcloud secrets get-iam-policy gemini-api-key
```

The service account needs `roles/secretmanager.secretAccessor`.

### Frontend can't reach backend (CORS errors)

The backend's `CORS_ORIGINS` env var is set dynamically from the frontend Cloud Run URL during deploy. If the frontend URL changed, redeploy the backend:
```bash
git commit --allow-empty -m "chore: redeploy backend"
git push
```

Or update it manually:
```bash
FRONTEND_URL=$(gcloud run services describe salestrainer-pro-frontend \
  --region=us-central1 --format='value(status.url)')

gcloud run services update salestrainer-pro-backend --region=us-central1 \
  --update-env-vars="CORS_ORIGINS=[\"${FRONTEND_URL}\",\"http://localhost:3000\",\"http://localhost:5173\"]"
```

### Cloud Run cold start is slow

Increase minimum instances to keep one warm:
```bash
gcloud run services update salestrainer-pro-backend --region=us-central1 --min-instances=1
```

This costs more (always-on billing) but eliminates cold starts.

### How to rollback a bad deploy

```bash
# List revisions
gcloud run revisions list --service=salestrainer-pro-backend --region=us-central1

# Route 100% traffic to a previous revision
gcloud run services update-traffic salestrainer-pro-backend \
  --region=us-central1 \
  --to-revisions=salestrainer-pro-backend-PREVIOUS_REVISION=100
```

### Terraform state is locked

```bash
# LOCK_ID is shown in the error message
terraform force-unlock LOCK_ID
```
