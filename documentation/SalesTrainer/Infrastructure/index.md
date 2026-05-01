# Infrastructure

Deployment, CI/CD, and operational guides for SalesTrainer Pro.

**Tags:** #infrastructure #deployment #devops #gcp

## Core Infrastructure

### GCP Terraform
- **[[TERRAFORM_INFRASTRUCTURE]]** - Complete IaC definition for GCP
  - Cloud Run services (backend, frontend)
  - Firestore database and vector indexes
  - Cloud Storage buckets
  - Secret Manager integration
  - Service accounts and IAM roles

### CI/CD Pipeline
- **[[CICD_GUIDE]]** - GitHub Actions workflows and deployment process
  - Build pipeline triggers
  - Testing and linting checks
  - Container image builds
  - Deployment to Cloud Run
  - Secrets management

## Quick Deployment

### Prerequisites
See [[TERRAFORM_SETUP|../Getting%20Started/TERRAFORM_SETUP.md]] for initial setup.

### Deploy Infrastructure
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Deploy Application
GitHub Actions handles deployment automatically on push to main.

For manual deployment:
```bash
# See CICD_GUIDE for details
gcloud run deploy salestrainer-pro-backend ...
gcloud run deploy salestrainer-pro-frontend ...
```

## Services & Components

| Service | Location | Purpose |
|---------|----------|---------|
| Backend | Cloud Run | FastAPI server |
| Frontend | Cloud Run | React SPA |
| Database | Firestore | Sessions, users, knowledge |
| Storage | GCS | Training materials, documents |
| Secrets | Secret Manager | API keys, credentials |
| Logging | Cloud Logging | Centralized application logs |
| Images | Artifact Registry | Container images |

## Key Decisions

| Decision | Rationale | Implication |
|----------|-----------|-------------|
| Cloud Run | Serverless, scales to zero | Cold starts on idle, simpler ops |
| Firestore | Managed, vector search | Schema-less, auto-scaling |
| GCS buckets | Cheap storage, CDN-able | Separate from database |
| Secret Manager | Secure, audit trail | No hardcoded secrets |
| Terraform | IaC, reproducible | Single source of truth for infra |

## Monitoring & Troubleshooting

### Check Service Status
```bash
gcloud run services list --platform managed
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

### Common Issues
See [[CICD_GUIDE]] for:
- Build failures
- Deployment issues
- Firestore index creation delays
- Cloud Run cold starts

## Related Documentation

- **[[TERRAFORM_SETUP|../Getting%20Started/TERRAFORM_SETUP.md]]** - Initial infrastructure setup
- **[[BACKEND_SETUP|../Getting%20Started/BACKEND_SETUP.md]]** - Backend runtime environment
- **[[API_SPECIFICATION|../API%20Documentation/API_SPECIFICATION.md]]** - Deployed endpoints

---

**Infrastructure questions?** Check [[CICD_GUIDE]] for deployment troubleshooting.
