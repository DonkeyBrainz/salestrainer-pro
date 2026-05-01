#!/bin/bash
set -e

# Set project details
export PROJECT_ID="ashley-ai"
export GITHUB_ORG="afi-internal"
export GITHUB_REPO="ai-ml-sales-coach"

echo "=== Phase 1.1: Create Workload Identity Pool and Provider ==="

# Get project number
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
echo "Project Number: $PROJECT_NUMBER"

# Create pool
echo "Creating Workload Identity Pool..."
gcloud iam workload-identity-pools create github-actions-pool \
  --project=$PROJECT_ID \
  --location=global \
  --display-name="GitHub Actions Pool" 2>/dev/null || echo "Pool already exists"

# Create provider with correct attribute mapping
echo "Creating GitHub OIDC Provider..."
gcloud iam workload-identity-pools providers create-oidc github-actions-provider \
  --project=$PROJECT_ID \
  --location=global \
  --workload-identity-pool=github-actions-pool \
  --display-name="GitHub Actions Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${GITHUB_ORG}/${GITHUB_REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com" 2>/dev/null || echo "Provider already exists"

echo ""
echo "=== Phase 1.2: Create Service Account ==="

# Create SA
echo "Creating Service Account..."
gcloud iam service-accounts create github-actions-sa \
  --project=$PROJECT_ID \
  --display-name="GitHub Actions Service Account" 2>/dev/null || echo "SA already exists"

# Grant permissions
echo "Granting Cloud Run admin role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.admin" --condition=None > /dev/null

echo "Granting Artifact Registry writer role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer" --condition=None > /dev/null

echo "Granting Secret Manager accessor role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" --condition=None > /dev/null

# Check if backend SA exists
if gcloud iam service-accounts describe salescoach-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com --project=$PROJECT_ID > /dev/null 2>&1; then
  echo "Allowing impersonation of backend SA..."
  gcloud iam service-accounts add-iam-policy-binding \
    salescoach-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --project=$PROJECT_ID \
    --member="serviceAccount:github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser" --condition=None > /dev/null
else
  echo "WARNING: salescoach-backend-sa does not exist yet. Will need to grant serviceAccountUser role later."
fi

echo ""
echo "=== Phase 1.3: Configure WIF Binding ==="

# Allow GitHub repo to impersonate SA
export WORKLOAD_IDENTITY_POOL_ID="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions-pool"

echo "Binding GitHub repo to service account..."
gcloud iam service-accounts add-iam-policy-binding \
  github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --project=$PROJECT_ID \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${GITHUB_ORG}/${GITHUB_REPO}" \
  --condition=None > /dev/null

echo ""
echo "=== Phase 1.4: Configuration Values ==="

# Get values for GitHub
export WORKLOAD_IDENTITY_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider"
export SERVICE_ACCOUNT="github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo ""
echo "=========================================="
echo "Add these as GitHub repository VARIABLES:"
echo "=========================================="
echo ""
echo "GCP_PROJECT_ID: $PROJECT_ID"
echo ""
echo "GCP_WORKLOAD_IDENTITY_PROVIDER: $WORKLOAD_IDENTITY_PROVIDER"
echo ""
echo "GCP_SERVICE_ACCOUNT: $SERVICE_ACCOUNT"
echo ""
echo "=========================================="
echo ""
echo "Setup complete! Next steps:"
echo "1. Go to: https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/settings/variables/actions"
echo "2. Add the three variables above as repository variables (NOT secrets)"
echo "3. Then create the GitHub Actions workflow files"
echo ""
