# Terraform Configuration

Infrastructure-as-Code for SalesTrainer Pro deployment on GCP.

## Quick Start

### Prerequisites
- Terraform >= 1.5.0
- Personal GCP project with billing enabled
- `gcloud` CLI authenticated
- Service account key for SalesTrainer Pro

### Configuration

1. **Set up your project variables:**
```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project details
```

2. **Required variables in `terraform.tfvars`:**
```hcl
project_id   = "your-gcp-project-id"
region       = "us-central1"
github_owner = "your-github-username"
github_repo  = "salestrainer-pro"
```

### Deployment

```bash
# Initialize and plan
terraform init
terraform plan

# Deploy infrastructure
terraform apply
```

## Infrastructure Components

### Core Services
- **Cloud Run**: Backend and frontend services
- **Firestore**: Document database for sessions and knowledge
- **Cloud Storage**: Training materials and document storage
- **Secret Manager**: Secure API keys and credentials
- **Artifact Registry**: Container images

### Firestore Collections
- `sessions` - Training session data
- `knowledge_chunks` - RAG training content with vector embeddings
- `users` - User profiles and progress

### Storage Buckets
- `{project-id}-salestrainer-pro-knowledge` - Training materials

## Services Created

- **salestrainer-pro-backend** - FastAPI backend service
- **salestrainer-pro-frontend** - React frontend service

## Required Secrets

After deployment, populate these secrets in Google Secret Manager:

```bash
# Gemini API key
echo -n "your-gemini-api-key" | gcloud secrets versions add gemini-api-key --data-file=-

# JWT secret key
echo -n "your-random-secret-key" | gcloud secrets versions add jwt-secret-key --data-file=-

# OAuth client ID
echo -n "your-oauth-client-id" | gcloud secrets versions add google-oauth-client-id --data-file=-

# OAuth client secret
echo -n "your-oauth-client-secret" | gcloud secrets versions add google-oauth-client-secret --data-file=-
```

## Service Accounts

- **salestrainer-pro-backend-sa** - Backend Cloud Run service account
- **salestrainer-pro-cloudbuild-sa** - CI/CD pipeline service account

## Vector Search Setup

The Firestore vector indexes support RAG functionality:
- Vector search on 768-dimensional embeddings (Gemini)
- Metadata filtering by category and content type
- Training material knowledge retrieval

## State Storage

Terraform state is stored in GCS bucket:
- **Bucket**: `{project-id}-terraform-state`
- **Prefix**: `salestrainer-pro`

## Troubleshooting

### Common Issues

1. **Firestore index creation takes time**: Vector indexes can take 30-60 minutes to build
2. **Cloud Run cold starts**: First request after idle may be slow
3. **Missing secrets**: Ensure all required secrets are populated

### Useful Commands

```bash
# View terraform state
gsutil cat gs://{project-id}-terraform-state/salestrainer-pro/terraform.tfstate | jq

# Check service status
gcloud run services list --platform managed

# View logs
gcloud logging read "resource.type=cloud_run_revision"
```
