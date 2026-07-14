# SalesTrainer Pro - Documentation Hub

Welcome to the SalesTrainer Pro documentation vault! This is your central hub for exploring the codebase, architecture, and operations.

## Quick Navigation

### 🚀 [Getting Started](Getting%20Started/index.md)
Setup guides for backend, frontend, and infrastructure. Start here if you're new to the project.

**Key docs:**
- [[SETUP_CHECKLIST|Getting Started/SETUP_CHECKLIST.md]] - Initial setup checklist
- [[BACKEND_SETUP|Getting Started/BACKEND_SETUP.md]] - Python/FastAPI environment
- [[FRONTEND_SETUP|Getting Started/FRONTEND_SETUP.md]] - React/TypeScript environment
- [[TERRAFORM_SETUP|Getting Started/TERRAFORM_SETUP.md]] - GCP infrastructure

### 🏗️ [Architecture & Design](Architecture%20&%20Design/index.md)
System design, data models, and component interactions.

**Key docs:**
- [[PRODUCT_REQUIREMENTS|Architecture & Design/PRODUCT_REQUIREMENTS.md]] - Project vision and goals
- [[AGENT_FLOW|Architecture & Design/AGENT_FLOW.md]] - Conversation flow and agent architecture
- [[AGENTIC_ENGINEERING|Architecture & Design/AGENTIC_ENGINEERING.md]] - AI-engineering deep dive: models, memory, RAG, design defenses + practice questions
- [[DATABASE_SCHEMA|Architecture & Design/DATABASE_SCHEMA.md]] - Firestore collections and relationships
- [[SESSION_STATE_RESUMPTION|Architecture & Design/SESSION_STATE_RESUMPTION.md]] - Session persistence patterns

### 📡 [API Documentation](API%20Documentation/index.md)
REST and WebSocket endpoint specifications.

**Key docs:**
- [[API_SPECIFICATION|API Documentation/API_SPECIFICATION.md]] - Complete API reference

### ⚙️ [Features](Features/index.md)
Feature-specific documentation and troubleshooting guides.

**Key docs:**
- [[ADMIN_DASHBOARD|Features/ADMIN_DASHBOARD.md]] - Admin features and management
- [[ADMIN_TROUBLESHOOTING|Features/ADMIN_TROUBLESHOOTING.md]] - Common issues and solutions
- [[ASHLEY_FURNITURE_EASY|Features/AshleyFurnitureEASYSellingSystem.md]] - Industry example: Furniture sales

### 🔧 [Infrastructure](Infrastructure/index.md)
Deployment, CI/CD, and operational guides.

**Key docs:**
- [[TERRAFORM_INFRASTRUCTURE|Infrastructure/TERRAFORM_INFRASTRUCTURE.md]] - GCP resource definitions
- [[CICD_GUIDE|Infrastructure/CICD_GUIDE.md]] - GitHub Actions and deployment pipeline

### 🗂️ [Cleanup](Cleanup/index.md)
Archived docs and past iterations. Review for context but not active development.

**Legacy content:**
- User testing and stakeholder-feedback analysis (needs human review before archiving further)
- Deprecated feature specs (cut features)

---

## Search Tips

**By tag:**
- `#setup` - Getting started and configuration
- `#architecture` - Design and system decisions
- `#api` - API endpoints and contracts
- `#features` - Feature implementations
- `#infrastructure` - Deployment and ops
- `#deprecated` - Archived content

**Browse by folder:**
Use your file explorer or backlinks to navigate hierarchically.

---

## Contributing

When updating docs:
1. Keep sections focused and linked
2. Add relevant tags (see above)
3. Use wikilinks `[[name|path]]` to reference other docs
4. Update this INDEX when adding new sections

---

**Last updated:** 2026-07-13
**Vault:** SalesTrainer Pro

**Recent changes:** Agent-hardening hardened (agent-hardening branch) - multi-provider voice support, C.O.R.E. system coaching framework, Python 3.13+
