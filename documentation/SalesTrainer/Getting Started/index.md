# Getting Started

Welcome! This section covers all setup and initial configuration needed to develop on SalesTrainer Pro.

**Tags:** #setup #onboarding

## Start Here

New to the project? Follow this order:

1. **[[SETUP_CHECKLIST]]** - Your main onboarding checklist
2. **[[PROJECT_README]]** - Project overview and goals
3. Choose your path:
   - Backend dev → **[[BACKEND_SETUP]]**
   - Frontend dev → **[[FRONTEND_SETUP]]**
   - DevOps/Infrastructure → **[[TERRAFORM_SETUP]]**

## Quick Commands

### Backend (Python 3.11+)
```bash
cd backend
uv sync              # Install dependencies
uv run uvicorn app.main:app --reload --port 8000  # Start dev server
uv run pytest        # Run tests
uv run ruff check .  # Lint
```

### Frontend (Node 18+)
```bash
npm install
npm run dev          # Start dev server (port 3000)
npm run build        # Production build
npm run test         # Run tests
```

### Terraform
```bash
terraform init
terraform plan
terraform apply
```

## Key Resources

- **[[DATABASE_SCHEMA|../Architecture%20&%20Design/DATABASE_SCHEMA.md]]** - Firestore structure (needed for backend)
- **[[API_SPECIFICATION|../API%20Documentation/API_SPECIFICATION.md]]** - API contracts
- **[[CICD_GUIDE|../Infrastructure/CICD_GUIDE.md]]** - Deployment pipeline

## Next Steps

Once setup is complete:
- Explore **[[AGENT_FLOW|../Architecture%20&%20Design/AGENT_FLOW.md]]** to understand conversations
- Check **[[PRODUCT_REQUIREMENTS|../Architecture%20&%20Design/PRODUCT_REQUIREMENTS.md]]** for feature context
- Read feature-specific docs in **[[Features|../Features/index.md]]**

---

**Stuck?** See [[ADMIN_TROUBLESHOOTING|../Features/ADMIN_TROUBLESHOOTING.md]] for common issues.
