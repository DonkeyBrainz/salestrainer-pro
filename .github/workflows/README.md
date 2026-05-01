# GitHub Actions CI/CD

This directory contains GitHub Actions workflows for continuous integration and deployment to Google Cloud Run using Workload Identity Federation (keyless authentication).

## Workflows

### CI Workflows (Run on PRs)

- **backend-ci.yml**: Runs on PRs to `main` or `development` with backend changes
  - Lints with ruff
  - Type checks with mypy
  - Runs tests with pytest

- **frontend-ci.yml**: Runs on PRs to `main` or `development` with frontend changes
  - Type checks with TypeScript
  - Runs tests with Vitest

### CD Workflows (Deploy on merge to main)

- **backend-deploy.yml**: Deploys backend when merging to `main`
  - Runs all CI checks
  - Builds and pushes Docker image to Artifact Registry
  - Deploys to Cloud Run (`salescoach-backend`)

- **frontend-deploy.yml**: Deploys frontend when merging to `main`
  - Fetches backend URL first
  - Runs all CI checks
  - Builds and pushes Docker image with backend URL
  - Deploys to Cloud Run (`salescoach-frontend`)

### Test Workflow

- **test-gcp-auth.yml**: Manual workflow to test GCP authentication
  - Validates Workload Identity Federation setup
  - Can be run manually from Actions tab

## Branching Strategy

- **Development**: Work happens on `development` branch
- **Production**: Merge `development` → `main` via PR to deploy
- **CI checks**: Run on PRs to both `main` and `development`
- **Deployments**: Only trigger when code is merged to `main`

## Testing the Workflows

### Test CI Workflows

1. Create a test PR to `development`:
   ```bash
   git checkout development
   git checkout -b test/ci-check
   echo "# Test" >> backend/README.md
   git add backend/README.md
   git commit -m "test: Verify backend CI workflow"
   git push -u origin test/ci-check
   ```

2. Create PR in GitHub UI
3. Verify `backend-ci.yml` runs successfully

### Test Deploy Workflows

**Option 1: Manual trigger** (safest for first test)
1. Go to Actions tab
2. Select "Backend Deploy" workflow
3. Click "Run workflow" → Select `development` branch
4. Monitor progress

**Option 2: Merge to main**
1. Create PR from `development` to `main`
2. Merge PR
3. Workflows will trigger automatically

## Rollback Plan

Rollback Cloud Run deployment if needed:

```bash
# List revisions
gcloud run revisions list --service=salescoach-backend --region=us-central1

# Rollback to previous
gcloud run services update-traffic salescoach-backend \
  --region=us-central1 \
  --to-revisions=<previous-revision>=100
```

## Monitoring

- **GitHub Actions**: https://github.com/afi-internal/ai-ml-sales-coach/actions
- **Cloud Run Console**: https://console.cloud.google.com/run?project=ashley-ai
- **Logs**: Click on workflow runs to see detailed logs
