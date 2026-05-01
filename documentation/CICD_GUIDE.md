# CI/CD Guide - Sales Coach on GCP

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [How the Pieces Fit Together](#how-the-pieces-fit-together)
3. [GCP Services Used](#gcp-services-used)
4. [Secrets Management](#secrets-management)
5. [Terraform Infrastructure](#terraform-infrastructure)
6. [Dockerfiles](#dockerfiles)
7. [Cloud Build Pipelines](#cloud-build-pipelines)
8. [Implementation Sequence](#implementation-sequence)
9. [Manual Setup Checklist](#manual-setup-checklist)
10. [Troubleshooting](#troubleshooting)

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
                          |   Cloud Build   |
                          |  (CI/CD runner) |
                          +--------+--------+
                                   |
                    +--------------+--------------+
                    |                             |
           backend changed?              frontend changed?
                    |                             |
              +-----v-----+                +-----v-----+
              | lint/test  |                |  test     |
              | build img  |                | build img |
              | push to AR |                | push to AR|
              | deploy CR  |                | deploy CR |
              +-----------+                 +-----------+
                    |                             |
           +-------v-------+             +-------v-------+
           |   Cloud Run   |             |   Cloud Run   |
           | salescoach-   |             | salescoach-   |
           |   backend     |             |   frontend    |
           |  (FastAPI)    |             |   (nginx)     |
           +-------+-------+             +---------------+
                   |
          +--------+--------+
          |                 |
    +-----v-----+    +-----v-----+
    | Firestore |    | Gemini API|
    +----------+     +-----------+
```

**What happens when you push code:**

1. You push to `main` on GitHub
2. Cloud Build detects the push via a trigger connected to your repo
3. Cloud Build checks which files changed (path filter: `backend/**` or `frontend/**`)
4. Only the affected service's pipeline runs
5. The pipeline lints, tests, builds a Docker image, pushes it to Artifact Registry, and deploys to Cloud Run
6. Cloud Run starts serving the new container (zero-downtime rolling update)

For PRs, only the lint/test steps run -- no deployment.

---

## How the Pieces Fit Together

### Terraform vs Cloud Build -- who does what?

This is a common point of confusion. Here's the split:

| Concern | Managed by | Why |
|---------|-----------|-----|
| Cloud Run service definitions | Terraform | Infrastructure that rarely changes (memory, CPU, scaling) |
| Artifact Registry | Terraform | Created once, used forever |
| Secret Manager secrets | Terraform | Creates the secret "containers"; values populated manually |
| Service accounts + IAM | Terraform | Security config, version-controlled |
| Cloud Build triggers | Terraform | Trigger config is infra |
| **Which Docker image is running** | **Cloud Build** | Changes on every deploy. Terraform doesn't track this |
| **Secret values** | **You, manually** | Never in code, never in Terraform state |

**Think of it this way**: Terraform builds the stage (infrastructure). Cloud Build performs the show (deployments).

### The frontend-backend URL problem

The frontend needs to know the backend URL at build time (it's baked into the JavaScript bundle via `VITE_API_BASE_URL`). But the backend URL comes from Cloud Run, which is assigned after deployment.

**Solution**: Deploy the backend first. The frontend Cloud Build pipeline fetches the backend's URL from Cloud Run before building:

```yaml
# In frontend/cloudbuild.yaml
- name: 'gcr.io/cloud-builders/gcloud'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      gcloud run services describe salescoach-backend \
        --region=us-central1 \
        --format='value(status.url)' > /workspace/backend_url.txt
```

If you later set up a custom domain (e.g., `api.salescoach.com`), you can hardcode it and skip this step.

---

## GCP Services Used

| Service | Purpose | Cost Model |
|---------|---------|-----------|
| **Cloud Run** | Runs containers (backend + frontend) | Pay per request + CPU/memory while handling requests. Free tier: 2M requests/month |
| **Cloud Build** | CI/CD pipeline runner | 120 free build-minutes/day on default machine. Charged per minute beyond that |
| **Artifact Registry** | Stores Docker images | Storage cost (~$0.10/GB/month). First 500MB free |
| **Secret Manager** | Stores API keys, OAuth creds | $0.06 per 10,000 access operations. 6 secret versions free |
| **Firestore** | Database (already in use) | Per-read/write pricing. Free tier: 50K reads, 20K writes/day |
| **Cloud Storage** | Terraform state file | ~$0.02/GB/month. Negligible for state files |

**Enable required APIs** (one-time):
```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com
```

---

## Secrets Management

This is the most important section to understand. There are three layers of secrets in this setup.

### Layer 1: GCP Secret Manager (runtime secrets)

These are the secrets your backend application reads at runtime. Cloud Run injects them as environment variables from Secret Manager.

**Secrets to create:**

| Secret Name | Value | Used By |
|-------------|-------|---------|
| `gemini-api-key` | Your Gemini API key | Backend - Gemini API calls |
| `google-oauth-client-id` | Google OAuth 2.0 client ID | Backend - user authentication |
| `google-oauth-client-secret` | Google OAuth 2.0 client secret | Backend - user authentication |
| `jwt-secret-key` | Random 32+ char string for signing JWTs | Backend - token signing |

**How to populate them:**

```bash
# Set your project
export PROJECT_ID=your-gcp-project-id
gcloud config set project $PROJECT_ID

# Create and populate each secret
# (replace the placeholder values with real ones)

# Gemini API key
echo -n "your-actual-gemini-api-key" | \
  gcloud secrets create gemini-api-key --data-file=-

# Google OAuth client ID
echo -n "your-oauth-client-id.apps.googleusercontent.com" | \
  gcloud secrets create google-oauth-client-id --data-file=-

# Google OAuth client secret
echo -n "your-oauth-client-secret" | \
  gcloud secrets create google-oauth-client-secret --data-file=-

# JWT secret key (generate a random one)
openssl rand -base64 32 | tr -d '\n' | \
  gcloud secrets create jwt-secret-key --data-file=-
```

**How they flow to your app:**

```
Secret Manager                Cloud Run                    Your App
+-----------------+          +------------------+         +------------------+
| gemini-api-key  | -------> | env: GEMINI_API_ | ------> | settings.gemini_ |
| (encrypted)     |  mount   |      KEY         |  read   |  api_key         |
+-----------------+          +------------------+         +------------------+
```

The Cloud Run deploy command maps them:
```bash
gcloud run deploy salescoach-backend \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest,\
GOOGLE_CLIENT_ID=google-oauth-client-id:latest,\
GOOGLE_CLIENT_SECRET=google-oauth-client-secret:latest,\
SECRET_KEY=jwt-secret-key:latest
```

**To update a secret value:**
```bash
echo -n "new-api-key-value" | \
  gcloud secrets versions add gemini-api-key --data-file=-

# Then redeploy the service to pick up the new version
gcloud run services update salescoach-backend --region=us-central1 \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest
```

### Layer 2: Cloud Build service account permissions

Cloud Build needs permission to:
- Read secrets from Secret Manager (to inject into Cloud Run)
- Push images to Artifact Registry
- Deploy to Cloud Run
- Act as the Cloud Run service account

These are IAM bindings, not secrets themselves. Terraform manages them:

```hcl
# In terraform/iam.tf

# Cloud Build SA can deploy to Cloud Run
resource "google_project_iam_member" "cloudbuild_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:salescoach-cloudbuild-sa@${var.project_id}.iam.gserviceaccount.com"
}

# Cloud Build SA can push to Artifact Registry
resource "google_project_iam_member" "cloudbuild_ar_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:salescoach-cloudbuild-sa@${var.project_id}.iam.gserviceaccount.com"
}

# Cloud Build SA can act as the backend service account
resource "google_service_account_iam_member" "cloudbuild_act_as_backend" {
  service_account_id = google_service_account.backend.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:salescoach-cloudbuild-sa@${var.project_id}.iam.gserviceaccount.com"
}
```

### Layer 3: GitHub connection to Cloud Build

Cloud Build connects to GitHub via the **Cloud Build GitHub App**. This is set up through the GCP Console (not via API/Terraform for the initial connection).

**Steps:**
1. Go to [Cloud Build > Triggers](https://console.cloud.google.com/cloud-build/triggers) in GCP Console
2. Click **Connect Repository**
3. Select **GitHub (Cloud Build GitHub App)**
4. Authenticate with GitHub and authorize the app
5. Select your repository (`gstudio_ts`)
6. Complete the connection

This installs a GitHub App on your repo that sends webhook events to Cloud Build. No GitHub secrets or tokens are needed on your side -- GCP manages the connection.

**Important**: You do NOT need GitHub Actions secrets. Cloud Build handles everything. The GitHub connection is purely for Cloud Build to receive push/PR events and read your code.

### What NOT to put in secrets

These are regular environment variables, not secrets. They go directly in Cloud Run env vars via Terraform or the deploy command:

| Variable | Value | Why not a secret |
|----------|-------|-----------------|
| `GCP_PROJECT_ID` | your-project-id | Not sensitive, publicly visible in URLs |
| `ENVIRONMENT` | production | Not sensitive |
| `FIRESTORE_DATABASE` | (default) | Not sensitive |
| `CORS_ORIGINS` | frontend Cloud Run URL | Not sensitive |
| `GOOGLE_REDIRECT_URI` | frontend callback URL | Not sensitive |
| `LOG_LEVEL` | INFO | Not sensitive |
| `LOG_JSON` | true | Not sensitive |

### Secret rotation

To rotate a secret:
```bash
# 1. Add a new version
echo -n "new-value" | gcloud secrets versions add gemini-api-key --data-file=-

# 2. Redeploy to pick it up (`:latest` always points to newest version)
gcloud run services update salescoach-backend --region=us-central1 \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest

# 3. (Optional) Disable old version
gcloud secrets versions disable 1 --secret=gemini-api-key
```

---

## Terraform Infrastructure

### Project structure

```
terraform/
├── provider.tf              # GCP provider + required APIs
├── backend.tf               # Where Terraform stores its own state (GCS bucket)
├── variables.tf             # Input variables (project_id, region)
├── main.tf                  # Artifact Registry + Cloud Run services
├── secrets.tf               # Secret Manager secret definitions
├── iam.tf                   # Service accounts + permissions
├── cloud_build.tf           # Cloud Build triggers
├── outputs.tf               # Outputs (service URLs)
├── terraform.tfvars.example # Example variable values
└── .gitignore               # Exclude state files and .terraform/
```

**Why flat, not modules?** Modules add abstraction. For a single-environment project with ~20 resources, flat files are easier to read, debug, and learn from. When you add staging, you can refactor into modules then.

### Key concepts for Terraform beginners

**State**: Terraform tracks every resource it creates in a state file. This file maps your `.tf` code to real GCP resources. We store it in a GCS bucket so it's shared and backed up.

**Plan vs Apply**: `terraform plan` shows what would change. `terraform apply` actually makes the changes. Always plan first.

**Imports**: If you already created resources manually (e.g., Firestore), you can import them into Terraform state without recreating them.

### Terraform state bucket (manual, one-time)

```bash
export PROJECT_ID=your-gcp-project-id

gcloud storage buckets create gs://${PROJECT_ID}-terraform-state \
  --project=$PROJECT_ID \
  --location=us-central1 \
  --uniform-bucket-level-access \
  --public-access-prevention

# Enable versioning (so you can recover from bad applies)
gcloud storage buckets update gs://${PROJECT_ID}-terraform-state --versioning
```

### Running Terraform

```bash
cd terraform/

# First time: initialize providers and backend
terraform init

# See what would be created/changed
terraform plan -var="project_id=your-project-id"

# Apply changes (creates real resources, costs money)
terraform apply -var="project_id=your-project-id"

# See current state
terraform state list

# See details of a specific resource
terraform state show google_cloud_run_service.backend
```

---

## Dockerfiles

### Backend Dockerfile (multi-stage)

**Why multi-stage?** The build stage has compilers and build tools (~800MB). The runtime stage only has what's needed to run the app (~200MB). Smaller images = faster deploys + less attack surface.

```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*
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

**Key decisions:**
- `uv` for fast dependency installation
- Non-root `appuser` for security (Cloud Run best practice)
- HEALTHCHECK for container health monitoring
- No .env file copied (secrets come from Secret Manager at runtime)

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
- `VITE_API_BASE_URL` passed as build arg (baked into JS bundle)
- `npm ci` (not `npm install`) for reproducible builds
- nginx on port 8080 (Cloud Run convention -- it sets the PORT env var to 8080)
- No node_modules in final image (just static HTML/CSS/JS)

### nginx.conf (frontend)

```nginx
server {
    listen 8080;
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing: all paths serve index.html, React Router handles the rest
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets aggressively (Vite adds content hashes to filenames)
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;
}
```

---

## Cloud Build Pipelines

### Backend pipeline (`backend/cloudbuild.yaml`)

```yaml
steps:
  # 1. Install dependencies
  - name: 'python:3.11-slim'
    id: 'install'
    entrypoint: 'bash'
    args:
      - '-c'
      - 'pip install uv && uv pip install --system .[dev]'
    dir: 'backend'

  # 2. Lint
  - name: 'python:3.11-slim'
    id: 'lint'
    entrypoint: 'bash'
    args: ['-c', 'ruff check app/']
    dir: 'backend'
    waitFor: ['install']

  # 3. Type check
  - name: 'python:3.11-slim'
    id: 'typecheck'
    entrypoint: 'bash'
    args: ['-c', 'mypy app/']
    dir: 'backend'
    waitFor: ['install']

  # 4. Test
  - name: 'python:3.11-slim'
    id: 'test'
    entrypoint: 'bash'
    args: ['-c', 'pytest --cov=app --cov-report=term -q']
    dir: 'backend'
    waitFor: ['install']

  # 5. Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    id: 'build'
    args:
      - 'build'
      - '-t'
      - '${_AR_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/backend:$SHORT_SHA'
      - '-t'
      - '${_AR_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/backend:latest'
      - '.'
    dir: 'backend'
    waitFor: ['lint', 'typecheck', 'test']

  # 6. Push to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    id: 'push'
    args: ['push', '--all-tags', '${_AR_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/backend']
    waitFor: ['build']

  # 7. Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    id: 'deploy'
    args:
      - 'run'
      - 'deploy'
      - 'salescoach-backend'
      - '--image=${_AR_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/backend:$SHORT_SHA'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--service-account=salescoach-backend-sa@$PROJECT_ID.iam.gserviceaccount.com'
      - '--set-secrets=GEMINI_API_KEY=gemini-api-key:latest,GOOGLE_CLIENT_ID=google-oauth-client-id:latest,GOOGLE_CLIENT_SECRET=google-oauth-client-secret:latest,SECRET_KEY=jwt-secret-key:latest'
      - '--set-env-vars=GCP_PROJECT_ID=$PROJECT_ID,ENVIRONMENT=production,LOG_JSON=true'
      - '--memory=1Gi'
      - '--cpu=2'
      - '--timeout=300'
      - '--max-instances=10'
    waitFor: ['push']

substitutions:
  _REGION: us-central1
  _AR_REGION: us
  _AR_REPO: salescoach

options:
  logging: CLOUD_LOGGING_ONLY
timeout: '1200s'
```

**How `waitFor` works**: Steps with the same `waitFor` run in parallel. lint, typecheck, and test all wait for install, then run concurrently. Build waits for all three to pass.

**Substitutions**: Variables prefixed with `_` are user-defined. `$PROJECT_ID` and `$SHORT_SHA` are built-in Cloud Build variables.

### Frontend pipeline (`frontend/cloudbuild.yaml`)

```yaml
steps:
  # 1. Get backend URL
  - name: 'gcr.io/cloud-builders/gcloud'
    id: 'get-backend-url'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        gcloud run services describe salescoach-backend \
          --region=${_REGION} \
          --format='value(status.url)' > /workspace/backend_url.txt
        echo "Backend URL: $(cat /workspace/backend_url.txt)"

  # 2. Install dependencies
  - name: 'node:20-alpine'
    id: 'install'
    entrypoint: 'npm'
    args: ['ci']
    dir: 'frontend'

  # 3. Type check
  - name: 'node:20-alpine'
    id: 'typecheck'
    entrypoint: 'npm'
    args: ['run', 'typecheck']
    dir: 'frontend'
    waitFor: ['install']

  # 4. Test
  - name: 'node:20-alpine'
    id: 'test'
    entrypoint: 'npm'
    args: ['run', 'test:run']
    dir: 'frontend'
    waitFor: ['install']

  # 5. Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    id: 'build'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        docker build \
          --build-arg VITE_API_BASE_URL=$(cat /workspace/backend_url.txt) \
          -t ${_AR_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/frontend:$SHORT_SHA \
          -t ${_AR_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/frontend:latest \
          .
    dir: 'frontend'
    waitFor: ['typecheck', 'test', 'get-backend-url']

  # 6. Push to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    id: 'push'
    args: ['push', '--all-tags', '${_AR_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/frontend']
    waitFor: ['build']

  # 7. Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    id: 'deploy'
    args:
      - 'run'
      - 'deploy'
      - 'salescoach-frontend'
      - '--image=${_AR_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/frontend:$SHORT_SHA'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--memory=256Mi'
      - '--cpu=1'
      - '--timeout=60'
      - '--max-instances=5'
    waitFor: ['push']

substitutions:
  _REGION: us-central1
  _AR_REGION: us
  _AR_REPO: salescoach

options:
  logging: CLOUD_LOGGING_ONLY
timeout: '1200s'
```

---

## Implementation Sequence

Seven PRs, each building on the previous. Merge each before starting the next.

| PR | Scope | Files | Depends On |
|----|-------|-------|------------|
| 1 | Backend Dockerfile + .dockerignore | `backend/Dockerfile`, `backend/.dockerignore` | Nothing |
| 2 | Frontend Dockerfile + nginx + .dockerignore | `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/.dockerignore` | Nothing |
| 3 | Terraform core (AR, secrets, IAM) | `terraform/*.tf`, `terraform/.gitignore` | Manual: state bucket, APIs enabled |
| 4 | Terraform Cloud Run services | `terraform/main.tf`, `terraform/outputs.tf` | PR 3 merged + `terraform apply` |
| 5 | Cloud Build backend pipeline | `backend/cloudbuild.yaml` | PR 1, PR 3-4 applied |
| 6 | Cloud Build frontend pipeline | `frontend/cloudbuild.yaml` | PR 2, PR 5 (backend deployed first) |
| 7 | Terraform Cloud Build triggers | `terraform/cloud_build.tf` | PR 5-6, GitHub connected to Cloud Build |

PRs 1 and 2 can be done in parallel. PRs 3 and 4 are sequential (infra must exist before services). PRs 5 and 6 are sequential (backend URL needed for frontend). PR 7 ties it all together.

---

## Manual Setup Checklist

Complete these steps before running Terraform or Cloud Build.

### 1. Enable GCP APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  firestore.googleapis.com
```

### 2. Create Terraform state bucket

```bash
export PROJECT_ID=$(gcloud config get-value project)

gcloud storage buckets create gs://${PROJECT_ID}-terraform-state \
  --project=$PROJECT_ID \
  --location=us-central1 \
  --uniform-bucket-level-access \
  --public-access-prevention

gcloud storage buckets update gs://${PROJECT_ID}-terraform-state --versioning
```

### 3. Populate Secret Manager

```bash
# Gemini API key
echo -n "YOUR_GEMINI_API_KEY" | \
  gcloud secrets create gemini-api-key --data-file=-

# OAuth client ID
echo -n "YOUR_CLIENT_ID.apps.googleusercontent.com" | \
  gcloud secrets create google-oauth-client-id --data-file=-

# OAuth client secret
echo -n "YOUR_CLIENT_SECRET" | \
  gcloud secrets create google-oauth-client-secret --data-file=-

# JWT signing key (auto-generated)
openssl rand -base64 32 | tr -d '\n' | \
  gcloud secrets create jwt-secret-key --data-file=-
```

### 4. Connect GitHub to Cloud Build

1. Go to **Cloud Build > Triggers** in [GCP Console](https://console.cloud.google.com/cloud-build/triggers)
2. Click **Connect Repository**
3. Choose **GitHub (Cloud Build GitHub App)**
4. Authorize and select your `gstudio_ts` repository
5. Complete the connection wizard

This creates a GitHub App installation. No GitHub secrets needed.

### 5. Update OAuth redirect URI

In the [Google Cloud Console > APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials):

1. Edit your OAuth 2.0 Client ID
2. Add the production frontend URL to **Authorized redirect URIs**:
   `https://salescoach-frontend-HASH-uc.a.run.app/auth/callback`
3. Also add it to **Authorized JavaScript origins**

You'll get the exact URL after the frontend deploys to Cloud Run.

---

## Troubleshooting

### Cloud Build fails: "Permission denied" on deploy

The Cloud Build service account needs `roles/run.admin` and `roles/iam.serviceAccountUser`. Check:
```bash
gcloud projects get-iam-policy $PROJECT_ID \
  --filter="bindings.members:salescoach-cloudbuild-sa" \
  --format="table(bindings.role)"
```

### Cloud Build fails: "Secret not found"

Verify secrets exist:
```bash
gcloud secrets list
```

Verify the Cloud Run service account can access them:
```bash
gcloud secrets get-iam-policy gemini-api-key
```

### Frontend can't reach backend (CORS errors)

Update the backend's `CORS_ORIGINS` env var to include the frontend URL:
```bash
FRONTEND_URL=$(gcloud run services describe salescoach-frontend --region=us-central1 --format='value(status.url)')

gcloud run services update salescoach-backend --region=us-central1 \
  --update-env-vars=CORS_ORIGINS="[\"${FRONTEND_URL}\"]"
```

### Cloud Run cold start is slow

Increase minimum instances to avoid cold starts:
```bash
gcloud run services update salescoach-backend --region=us-central1 --min-instances=1
```
This keeps at least one instance warm but costs more (always-on billing).

### Terraform state is locked

Someone else is running `terraform apply`, or a previous run crashed:
```bash
# Check who holds the lock
terraform force-unlock LOCK_ID

# LOCK_ID is shown in the error message
```

### How to rollback a bad deploy

```bash
# List revisions
gcloud run revisions list --service=salescoach-backend --region=us-central1

# Route traffic back to previous revision
gcloud run services update-traffic salescoach-backend \
  --region=us-central1 \
  --to-revisions=salescoach-backend-PREVIOUS_REVISION=100
```
