---
tags: [#infrastructure, #terraform, #gcp, #devops]
---

# Terraform Infrastructure Guide

## Overview

The Luxe Sales Coach uses **GCP-native infrastructure** provisioned entirely with Terraform (v1.5+). All resources are centralized in the `ashley-ai` GCP project with the `us-central1` region. The setup is production-focused with no separate dev/staging environments.

---

## Architecture at a Glance

### Production (Load Balancer Enabled)

```
                          Internet
                             │
                             ▼
                 salescoach.ashleyfurniture.com
                        (Load Balancer)
                             │
              ┌──────────────┴──────────────┐
              │                             │
         /* (default)                    /api/*, /ws/*, /auth/*
              │                             │
              ▼                             ▼
     ┌─────────────────┐         ┌─────────────────┐
     │  Cloud Run      │         │  Cloud Run      │
     │  (Frontend)     │         │  (Backend)      │
     │  Port 8080      │         │  Port 8000      │
     │  Internal LB    │         │  Internal LB    │
     └─────────────────┘         └─────────────────┘
              ▲                             ▲
              └─────────────┬───────────────┘
                            │
                   ┌────────┴─────────┐
                   │ Artifact Registry│
                   │ (Docker images)  │
                   └────────┬─────────┘
                            ▲
                   ┌────────┴─────────┐
                   │   Cloud Build    │
                   │   4 Triggers     │
                   └────────┬─────────┘
                            ▲
             afi-internal/ai-ml-sales-coach (GitHub)

Benefits:
  ✓ First-party cookies (works in incognito)
  ✓ Backend not publicly accessible
  ✓ No CORS needed (same origin)
  ✓ Simple OAuth (single domain)
```

### Development (Direct Cloud Run)

```
Frontend:  https://salescoach-frontend-<hash>.a.run.app
Backend:   https://salescoach-backend-<hash>.a.run.app

Issues:
  ✗ Third-party cookies (blocked in incognito)
  ✗ CORS required
  ✗ Backend publicly accessible
```

---

## Terraform File Structure

| File | Purpose |
|------|---------|
| `provider.tf` | GCP provider configuration (v5.x), terraform version constraint |
| `backend.tf` | Remote state storage in GCS (`ashley-ai-ai-ml-sales-coach-tf-state`) |
| `variables.tf` | Input variables: project_id, region, GitHub details, domain, enable_load_balancer |
| `main.tf` | Core resources: Cloud Run services, Artifact Registry, APIs |
| `load_balancer.tf` | **NEW**: Cloud Load Balancer, SSL cert, URL routing (optional) |
| `iam.tf` | Service accounts and IAM role bindings |
| `secrets.tf` | Secret Manager containers for API keys & credentials |
| `cloud_build.tf` | 4 Cloud Build triggers for CI/CD |
| `outputs.tf` | Exported values: service URLs, registry path, load balancer IP |
| `terraform.tfvars` | Variable values (project_id, region, github_owner, github_repo, domain) |

---

## Load Balancer Configuration (Optional)

**Controlled by**: `var.enable_load_balancer` (default: `true`)

When enabled, deploys a Cloud Load Balancer for custom domain with first-party cookies.

### Components

| Resource | Purpose |
|----------|---------|
| **Global External IP** | `salescoach-ip` - Static IP for DNS A record |
| **SSL Certificate** | `salescoach-ssl-cert` - Google-managed, auto-renewing |
| **Serverless NEGs** | Connect Cloud Run services to load balancer |
| **Backend Services** | Define routing to NEGs (frontend + backend) |
| **URL Map** | Route `/api/*`, `/ws/*`, `/auth/*` → backend, `/*` → frontend |
| **HTTPS Proxy** | TLS termination with SSL cert |
| **HTTP Proxy** | Redirect HTTP → HTTPS |
| **Forwarding Rules** | Bind IP to proxies (ports 80, 443) |

### URL Routing Rules

```
salescoach.ashleyfurniture.com/api/*         → Backend Cloud Run
salescoach.ashleyfurniture.com/ws/*          → Backend Cloud Run (WebSockets)
salescoach.ashleyfurniture.com/auth/*        → Backend Cloud Run (OAuth)
salescoach.ashleyfurniture.com/health        → Backend Cloud Run
salescoach.ashleyfurniture.com/docs          → Backend Cloud Run (API docs)
salescoach.ashleyfurniture.com/redoc         → Backend Cloud Run
salescoach.ashleyfurniture.com/*             → Frontend Cloud Run (default)
```

### Benefits

- **First-party cookies**: `SameSite=Lax` works in incognito mode
- **Backend security**: Not publicly accessible (only via load balancer)
- **No CORS**: Same-origin requests
- **Simple OAuth**: Single redirect URI domain
- **CDN**: Cloud CDN enabled for frontend static assets

### When Load Balancer is Enabled

1. **Cloud Run ingress** → `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`
2. **Public IAM binding** → Removed (`allUsers` invoker role)
3. **OAuth redirect URI** → Uses custom domain
4. **Cookies** → `SameSite=Lax` (first-party)

### When Load Balancer is Disabled

1. **Cloud Run ingress** → `INGRESS_TRAFFIC_ALL`
2. **Public IAM binding** → Present (`allUsers` can invoke)
3. **OAuth redirect URI** → Uses Cloud Run URLs
4. **Cookies** → `SameSite=Lax` (but cross-origin in production)

**To disable**: Set `enable_load_balancer = false` in `terraform.tfvars`

**Manual setup guide**: See `documentation/CUSTOM_DOMAIN_SETUP.md` for step-by-step instructions

---

## Compute Layer: Cloud Run

### Backend Service

| Property | Value |
|----------|-------|
| **Name** | `salescoach-backend` |
| **Port** | 8000 (FastAPI) |
| **CPU** | 2 cores |
| **Memory** | 1 Gi |
| **Scaling** | Min: 0, Max: 10 instances |
| **Health Check (Startup)** | `/health` endpoint, 5s initial delay, 3 retries |
| **Health Check (Liveness)** | `/health` endpoint, 30s period, 3 retries |
| **Public Access** | Yes (allUsers can invoke) |
| **Image Source** | Artifact Registry (updated by Cloud Build) |
| **Service Account** | `salescoach-backend-sa` |

**Environment Variables** (injected at deployment):
```
GEMINI_API_KEY          ← Secret Manager
GOOGLE_CLIENT_ID        ← Secret Manager
GOOGLE_CLIENT_SECRET    ← Secret Manager
SECRET_KEY              ← Secret Manager
GCP_PROJECT_ID          = ashley-ai
ENVIRONMENT             = production
FIRESTORE_DATABASE      = ai-ml-native
LOG_JSON                = true
LOG_LEVEL               = INFO
```

### Frontend Service

| Property | Value |
|----------|-------|
| **Name** | `salescoach-frontend` |
| **Port** | 8080 (React/Vite) |
| **CPU** | 1 core |
| **Memory** | 256 Mi |
| **Scaling** | Min: 0, Max: 5 instances |
| **Health Check (Startup)** | `/` endpoint, 2s initial delay, 3 retries |
| **Public Access** | Yes (allUsers can invoke) |
| **Image Source** | Artifact Registry (updated by Cloud Build) |

---

## Container Registry: Artifact Registry

**Repository**: `salescoach`
- **Location**: `us-central1`
- **Format**: Docker
- **Path**: `us-central1-docker.pkg.dev/ashley-ai/salescoach`
- **Image naming**:
  - Backend: `...docker.pkg.dev/ashley-ai/salescoach/backend:<git-sha>`
  - Frontend: `...docker.pkg.dev/ashley-ai/salescoach/frontend:<git-sha>`

---

## Secrets: Secret Manager

| Secret | Purpose |
|--------|---------|
| `gemini-api-key` | Gemini API authentication |
| `google-oauth-client-id` | OAuth login flow (frontend) |
| `google-oauth-client-secret` | OAuth token exchange (backend) |
| `jwt-secret-key` | JWT token signing/verification |

**Replication**: Auto-managed by GCP
**Access**: Granted only to `salescoach-backend-sa` via IAM role `secretmanager.secretAccessor`

---

## CI/CD: Cloud Build

### 4 Triggers Configured

#### 1. Backend Deploy
- **Trigger**: Push to `main` branch
- **Build file**: `backend/cloudbuild.yaml`
- **Steps**:
  - Build Docker image from `backend/Dockerfile`
  - Push to Artifact Registry
  - Deploy to Cloud Run (`salescoach-backend` service)
  - Inject secrets as environment variables
- **Service Account**: `salescoach-cloudbuild-sa`

#### 2. Backend CI
- **Trigger**: Pull request to `main` branch
- **Build file**: `backend/cloudbuild-ci.yaml`
- **Steps**:
  - Lint (ruff)
  - Type check (mypy)
  - Run tests (pytest)
- **Purpose**: Gates merges to main

#### 3. Frontend Deploy
- **Trigger**: Push to `main` branch
- **Build file**: `frontend/cloudbuild.yaml`
- **Steps**:
  - Build static assets (npm build)
  - Push to Artifact Registry
  - Deploy to Cloud Run (`salescoach-frontend` service)
- **Service Account**: `salescoach-cloudbuild-sa`

#### 4. Frontend CI
- **Trigger**: Pull request to `main` branch
- **Build file**: `frontend/cloudbuild-ci.yaml`
- **Steps**:
  - Type check (TypeScript)
  - Run tests (Jest/Vitest)
- **Purpose**: Gates merges to main

---

## IAM & Service Accounts

### Service Accounts

#### `salescoach-backend-sa`
**Purpose**: Runs backend Cloud Run service

**Permissions**:
- `roles/datastore.user` on Firestore database `ai-ml-native`
  - Allows read/write to Firestore collections
- `roles/secretmanager.secretAccessor` on all 4 secrets
  - Allows reading API keys at runtime

#### `salescoach-cloudbuild-sa`
**Purpose**: Executes Cloud Build pipelines

**Permissions**:
- `roles/run.admin`
  - Deploy to Cloud Run services
  - Update service definitions
- `roles/artifactregistry.writer`
  - Push Docker images to registry
  - Manage image metadata
- `roles/iam.serviceAccountUser` on `salescoach-backend-sa`
  - Act as backend service account (for deployments)
- `roles/run.viewer`
  - Read Cloud Run service details
- `roles/logging.logWriter`
  - Write build logs to Cloud Logging

---

## APIs Enabled

```
run.googleapis.com
  → Cloud Run (serverless container execution)

cloudbuild.googleapis.com
  → Cloud Build (CI/CD automation)

artifactregistry.googleapis.com
  → Artifact Registry (container registry)

secretmanager.googleapis.com
  → Secret Manager (secret storage)

iam.googleapis.com
  → Identity & Access Management

cloudresourcemanager.googleapis.com
  → Resource management

compute.googleapis.com
  → Compute Engine (required for Cloud Load Balancer)
```

---

## Data & State Management

### Terraform State
- **Location**: GCS bucket `ashley-ai-ai-ml-sales-coach-tf-state`
- **Path**: `production/terraform.tfstate`
- **Versioning**: Enabled for recovery
- **Locking**: Automatic (prevents concurrent modifications)

### Firestore Database
- **Name**: `ai-ml-native`
- **Status**: Pre-created (not provisioned by Terraform)
- **Collections**:
  - `sessions` - User training sessions
  - `transcripts` - Full message history
  - `evaluations` - Post-session scoring
  - etc. (managed by application code)

---

## Deployment Flow

### On Git Push to Main

```
Push to afi-internal/ai-ml-sales-coach main branch
           ▼
Cloud Build triggers (backend-deploy, frontend-deploy)
           ▼
Build Docker images
  - Backend: Python FastAPI → Docker
  - Frontend: React/npm build → Docker
           ▼
Push to Artifact Registry
  - Tag: Git commit SHA
  - Path: us-central1-docker.pkg.dev/ashley-ai/salescoach/[backend|frontend]:SHA
           ▼
Inject secrets from Secret Manager
  - GEMINI_API_KEY, OAUTH credentials, JWT secret
           ▼
Deploy to Cloud Run
  - Backend: salescoach-backend service (port 8000)
  - Frontend: salescoach-frontend service (port 8080)
           ▼
Health checks verify service is running
  - Backend: GET /health
  - Frontend: GET /
```

### On Pull Request to Main

```
Pull request to afi-internal/ai-ml-sales-coach main
           ▼
Cloud Build triggers (backend-ci, frontend-ci)
           ▼
Run lint/type-check/tests
  - Backend: ruff, mypy, pytest
  - Frontend: TypeScript check, Jest/Vitest
           ▼
Report status to PR
  - Green: Ready to merge
  - Red: Fix issues before merge
```

---

## Environment Configuration

**Current Setup: Production Only**

| Setting | Value |
|---------|-------|
| **GCP Project** | `ashley-ai` |
| **Region** | `us-central1` |
| **GitHub Org** | `afi-internal` |
| **GitHub Repo** | `ai-ml-sales-coach` |
| **Watch Branch** | `main` |
| **Firestore DB** | `ai-ml-native` |
| **Environment** | `production` |

**To add Dev/Staging**:
1. Add `environment` variable to `terraform.tfvars`
2. Create separate Cloud Run services with different names (e.g., `salescoach-backend-dev`)
3. Create separate Cloud Build triggers pointing to different branches
4. Update outputs to include all environments

---

## Key Outputs

After `terraform apply`, the following values are available:

### Without Load Balancer
```hcl
backend_url              = "https://salescoach-backend-REGION-HASH.a.run.app"
frontend_url             = "https://salescoach-frontend-REGION-HASH.a.run.app"
artifact_registry_repo   = "us-central1-docker.pkg.dev/ashley-ai/salescoach"
application_url          = "https://salescoach-frontend-REGION-HASH.a.run.app"
load_balancer_ip         = null
```

### With Load Balancer Enabled
```hcl
backend_url              = "https://salescoach-backend-REGION-HASH.a.run.app" (internal only)
frontend_url             = "https://salescoach-frontend-REGION-HASH.a.run.app" (internal only)
artifact_registry_repo   = "us-central1-docker.pkg.dev/ashley-ai/salescoach"
application_url          = "https://salescoach.ashleyfurniture.com"
load_balancer_ip         = "34.xxx.xxx.xxx" (use this for DNS A record)
dns_configuration        = {
  domain    = "salescoach.ashleyfurniture.com"
  type      = "A"
  value     = "34.xxx.xxx.xxx"
  ttl       = 300
  message   = "Create an A record for salescoach.ashleyfurniture.com pointing to 34.xxx.xxx.xxx"
}
```

**Usage**:
- Use `application_url` for public access
- Use `load_balancer_ip` for DNS configuration
- `backend_url` and `frontend_url` are internal only when load balancer is enabled

---

## Security Practices

1. **No Hardcoded Secrets**: All credentials stored in Secret Manager
2. **Least Privilege**: Separate service accounts for backend and Cloud Build
3. **Firestore Access**: Restricted via IAM role, only backend service account can access
4. **Public Endpoints**: Cloud Run services are public, but auth is handled by backend (OAuth + JWT)
5. **State Security**: Terraform state stored in GCS with versioning enabled
6. **Image Scanning**: Artifact Registry can scan images for vulnerabilities (optional, not yet configured)

---

## Important Notes

- **GitHub Connection**: Cloud Build → GitHub OAuth must be manually set up in the GCP console first. Terraform only creates the triggers.
- **Firestore Database**: Referenced but not provisioned by Terraform. The `ai-ml-native` database must exist before deployment.
- **Image Placeholders**: Both Cloud Run services start with placeholder images. Cloud Build updates them on the first deploy.
- **No Dev/Staging**: Currently production-only. To add other environments, duplicate Cloud Run/Cloud Build resources with environment suffixes.
- **Custom Domain Setup**: Load balancer configuration is in `load_balancer.tf`. Requires manual DNS configuration. See `CUSTOM_DOMAIN_SETUP.md` for step-by-step instructions.
- **SSL Certificate Provisioning**: Takes 15-60 minutes after DNS is configured. Certificate will show `PROVISIONING` status until Google verifies domain ownership.
- **Load Balancer Cost**: ~$36-50/month base cost plus traffic charges when enabled.

---

## Common Terraform Commands

```bash
# From terraform/ directory

# Initialize (first time)
terraform init

# Plan changes
terraform plan

# Apply changes
terraform apply

# View current state
terraform show

# Check state in remote GCS
gsutil cat gs://ashley-ai-ai-ml-sales-coach-tf-state/production/terraform.tfstate

# Destroy (⚠️ deletes all resources)
terraform destroy
```

---

## File Locations

- `terraform/provider.tf` - GCP provider config
- `terraform/backend.tf` - State bucket config
- `terraform/variables.tf` - Input variable definitions
- `terraform/main.tf` - Cloud Run & Artifact Registry
- `terraform/iam.tf` - Service accounts & roles
- `terraform/secrets.tf` - Secret Manager resources
- `terraform/cloud_build.tf` - CI/CD triggers
- `terraform/outputs.tf` - Exported values
- `terraform/terraform.tfvars` - Variable values (sensitive, check `.gitignore`)
- `terraform/.terraform.lock.hcl` - Provider version lock (commit to git)
