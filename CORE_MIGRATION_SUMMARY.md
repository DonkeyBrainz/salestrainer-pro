C.O.R.E. Migration - Quick Reference
====================================

What Changed?
=============

BEFORE: E.A.S.Y. (Ashley Furniture specific)
- ENGAGE → Build rapport
- ASK → Discover needs
- SHOW → Present solutions  
- YES → Close

AFTER: C.O.R.E. (Universal, industry-agnostic)
- CONNECT → Build rapport and trust
- OBSERVE → Discover needs and motivators
- RECOMMEND → Present tailored solutions
- EXECUTE → Secure commitment

Why?
====

Rebranding as universal sales training platform, not tied to Ashley Furniture. Supports any industry: real estate, SaaS, automotive, insurance, furniture, etc.

What's Done?
============

✓ backend/app/data/core_system.py
  - Full C.O.R.E. system definition
  - Stage content, requirements, key phrases
  - Customer Motivators mapping
  - Helper functions

What's Pending?
===============

12 Backend Code Files:
  Priority 1 (5 files): state.py, scorer.py, prompts.py, analyzer.py, hints.py
  Priority 2 (4 files): customer_agent.py, coach.py, evaluation.py, coach_agent_service.py
  Priority 3 (3 files): customer_agent_service.py, __init__.py, data/__init__.py

20+ Documentation Files:
  Critical (8): PRODUCT_REQUIREMENTS, AGENT_FLOW, AshleyFurnitureEASYSellingSystem, API_SPECIFICATION, DATABASE_SCHEMA, BACKEND_SETUP, PROJECT_README, SESSION_STATE_RESUMPTION
  Medium (5): INDEX, Architecture/index, Features/index, FRONTEND_SETUP, FUTURE_API_ENDPOINTS
  Cleanup (10+): Various docs in Cleanup folder

Files to Update - By Category
=============================

BACKEND CODE (Edit these files):

1. backend/app/agents/state.py
   - Rename: EASYStageProgress → CoreStageProgress
   - Update: SalesStage enum (ENGAGE→CONNECT, ASK→OBSERVE, SHOW→RECOMMEND, YES→EXECUTE)

2. backend/app/agents/coach/scorer.py
   - Update: STAGE_WEIGHTS keys
   - Update: calculate_stage_score(), calculate_penalty(), calculate_grade()

3. backend/app/agents/coach/prompts.py
   - Replace: COACH_ANALYSIS_PROMPT
   - Update: Technique definitions
   - Update: Example phrases

4. backend/app/agents/coach/analyzer.py
   - Update: analyze_turn() logic
   - Update: CoachAnalysis references
   - Update: Stage progression

5. backend/app/agents/coach/hints.py
   - Update: Hint templates for C.O.R.E. stages

6. backend/app/agents/customer_agent.py
   - Update: Stage validation
   - Update: Stage progression rules

7. backend/app/models/coach.py
   - Replace: EASYStageProgress
   - Update: Stage field types

8. backend/app/models/evaluation.py
   - Update: stage_progress field
   - Update: Examples

9. backend/app/services/coach_agent_service.py
   - Replace: EASYStageProgress usage
   - Update: generate_evaluation()

10. backend/app/services/customer_agent_service.py
    - Update: Stage validation logic

11. backend/app/agents/__init__.py
    - Update: Imports

12. backend/app/data/__init__.py
    - Update: easy_system → core_system import

DOCUMENTATION (Update these files):

Critical:
- documentation/SalesTrainer/Architecture & Design/PRODUCT_REQUIREMENTS.md
- documentation/SalesTrainer/Architecture & Design/AGENT_FLOW.md
- documentation/SalesTrainer/Features/AshleyFurnitureEASYSellingSystem.md (RENAME to UniversalCORESellingSystem.md)
- documentation/SalesTrainer/API Documentation/API_SPECIFICATION.md

Important:
- documentation/SalesTrainer/Architecture & Design/DATABASE_SCHEMA.md
- documentation/SalesTrainer/Getting Started/BACKEND_SETUP.md
- documentation/SalesTrainer/Getting Started/PROJECT_README.md
- documentation/SalesTrainer/Architecture & Design/SESSION_STATE_RESUMPTION.md

Also update (minor):
- documentation/SalesTrainer/INDEX.md
- documentation/SalesTrainer/Architecture & Design/index.md
- documentation/SalesTrainer/Features/index.md
- documentation/SalesTrainer/Getting Started/FRONTEND_SETUP.md
- documentation/SalesTrainer/Architecture & Design/FUTURE_API_ENDPOINTS.md

Find & Replace Patterns
=======================

Code:
EASYStageProgress → CoreStageProgress
SalesStage.ENGAGE → SalesStage.CONNECT
SalesStage.ASK → SalesStage.OBSERVE
SalesStage.SHOW → SalesStage.RECOMMEND
SalesStage.YES → SalesStage.EXECUTE

Docs:
E.A.S.Y. → C.O.R.E.
EASY → CORE
ENGAGE → CONNECT
ASK → OBSERVE
SHOW → RECOMMEND
YES → EXECUTE
Engage → Connect
Ask → Observe
Show → Recommend

Remove/Update:
- "Ashley Furniture" references → Make industry-neutral
- "Ashley" → Remove or use [Industry]
- Ashley-specific examples → Use generic examples

Effort Estimate
===============

Backend Code: 20-30 hours
  - state.py: 2-3h
  - scorer.py: 2-3h
  - prompts.py: 4-6h
  - analyzer.py: 3-4h
  - hints.py: 2-3h
  - Supporting files: 7-11h
  - Testing: 2-3h

Documentation: 10-15 hours
  - Critical docs: 6-9h
  - Medium docs: 2-3h
  - Cleanup docs: 1-2h
  - Minor updates: 1-1.5h

Total: 35-55 hours

Key Files to Start With
=======================

1. backend/app/agents/state.py (FIRST - blocks all others)
2. backend/app/agents/coach/scorer.py (uses state.py)
3. backend/app/agents/coach/prompts.py (uses scorer.py)
4. Then update remaining code files
5. Finally update documentation

Testing Checklist
=================

Before Deployment:
- Coach analysis returns correct stage (CONNECT/OBSERVE/RECOMMEND/EXECUTE)
- Scoring works with new stage weights
- Stage progression validation works
- Evaluation generation completes successfully
- All existing tests pass with new stage names
- Example API responses show new stage names
- Database queries work with new field names

Rollback Plan
=============

If issues discovered:
1. Revert commits to last working state
2. Keep core_system.py as reference
3. Restart with more careful testing
4. Consider hybrid approach (support both systems)

References
==========

- CORE_MIGRATION_PLAN.md - Detailed step-by-step plan
- CORE_MIGRATION_STATUS.md - Detailed status and breakdown
- backend/app/data/core_system.py - C.O.R.E. definition

Contact/Questions
=================

For questions on:
- System definition: See core_system.py and CORE_MIGRATION_PLAN.md
- Current status: See CORE_MIGRATION_STATUS.md
- File locations: See file-by-file breakdown above
- Testing strategy: See CORE_MIGRATION_PLAN.md

Last Updated: 2026-04-30
