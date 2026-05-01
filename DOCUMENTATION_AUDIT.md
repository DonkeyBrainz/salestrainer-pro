Documentation Audit Report
===========================

Date: April 30, 2026
Status: INCOMPLETE - Documentation is 2+ months out of date

Major Gaps Identified
====================

CRITICAL - API Documentation
-----------------------------
Last Updated: February 5, 2026 (85 days old)
Missing Endpoints:
- POST /admin/personas/metrics - Persona performance metrics
- GET /admin/users/metrics - User-level analytics
- GET /admin/users/{user_id}/sessions - Admin session list
- GET /admin/sessions/{session_id} - Admin session details
- GET /products - Product catalog endpoint
- GET /products/categories - Product category filtering
- Sessions API needs RAG-related endpoint documentation

CRITICAL - Database Schema
---------------------------
Missing Collections:
- knowledge_chunks - Firestore vector search collection for RAG
  Fields: embedding (768-dim vector), text, metadata (category, product_type, etc)
  Used by: RAG service, coach hint generation, product context retrieval

IMPORTANT - Backend Configuration
----------------------------------
RAG Service Configuration (Feb 19 commit):
- rag_enabled: Boolean feature flag
- rag_collection_name: Firestore collection name
- rag_embedding_model: "gemini-embedding-001"
- rag_top_k: Number of results to return (default: 3)
- rag_use_hybrid_search: Boolean (advanced retrieval Phase 3)
- rag_use_reranking: Boolean (re-ranking feature)
- rag_use_conversation_context: Boolean (context-aware retrieval)
- rag_use_objection_lookup: Boolean (objection handling)
- rag_reranking_model: "gemini-2.0-flash"
- rag_reranking_initial_k: Initial candidates (default: 10)
- rag_reranking_final_k: Final results (default: 3)

Not documented in BACKEND_SETUP.md

IMPORTANT - Authentication
---------------------------
Microsoft OAuth/Entra ID Support (Feb 19 commit):
- Azure/Entra ID configured in auth_service.py
- Requires additional secrets in Secret Manager:
  - azure-oauth-client-id
  - azure-oauth-client-secret
  - azure-oauth-tenant-id
  - (possibly others)
- Not documented in backend setup or CICD guide

IMPORTANT - Features Without Documentation
-------------------------------------------
Coach Hint Throttling/Quota Handling (Feb 15 commit):
- Graceful quota handling for Gemini API
- Coach hint throttling implemented
- No documentation of rate limits, throttling behavior, or quotas

Email Domain Allowlist (Jan 29 commit):
- Feature to restrict OAuth login by email domain
- Configuration: EMAIL_DOMAIN_ALLOWLIST environment variable
- No documentation in setup or security sections

Session Abandonment Handling (Feb 12 commit):
- Sessions marked as "abandoned" when disconnected without evaluation
- Affects analytics and metrics
- Not mentioned in AGENT_FLOW or session documentation

Product Selection & RAG Metadata (Feb 19 commit):
- Product categories linked to personas
- RAG queries filtered by product metadata
- Mentioned in code but missing from AGENT_FLOW documentation

MINOR - Documentation Freshness
-------------------------------
PRODUCT_REQUIREMENTS.md: Last updated Feb 19 (acceptable)
TERRAFORM_INFRASTRUCTURE.md: Age unknown (should be current)
CICD_GUIDE.md: Missing Microsoft OAuth secret setup
AGENT_FLOW.md: Needs RAG integration details
ADMIN_DASHBOARD.md: Needs endpoint documentation

Files to Update (Priority Order)
================================

1. API_SPECIFICATION.md - Add missing admin/products/RAG endpoints
2. DATABASE_SCHEMA.md - Add knowledge_chunks collection
3. BACKEND_SETUP.md - Add RAG configuration, Microsoft OAuth setup, email allowlist
4. CICD_GUIDE.md - Add Microsoft OAuth secrets setup
5. AGENT_FLOW.md - Add RAG retrieval flow, session abandonment handling
6. Getting Started/index.md - Link to new RAG documentation

Validation Checklist
====================

After updates, verify:
- API spec includes all 8+ routers from main.py
- All environment variables in config.py are documented
- All Firestore collections mentioned in code are in DATABASE_SCHEMA
- All authentication methods (Google + Microsoft) documented
- All features from commits in past 3 months documented
