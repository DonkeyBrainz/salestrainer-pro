E.A.S.Y. to C.O.R.E. Sales System Migration Plan
=================================================

Status: IN PROGRESS
Date Started: 2026-04-29
Target Completion: TBD

Overview
========

This document tracks the migration from Ashley Furniture's E.A.S.Y. Selling System (Engage, Ask, Show, Yes) to a universal C.O.R.E. Selling System (Connect, Observe, Recommend, Execute).

Goal: Rebrand platform as universal sales training tool, not specific to Ashley Furniture.

C.O.R.E. System Definition
==========================

Connect → Observe → Recommend → Execute

- CONNECT: Build rapport and trust through genuine conversation
- OBSERVE: Discover customer needs, challenges, motivators
- RECOMMEND: Present tailored solutions addressing discovered needs
- EXECUTE: Secure commitment and establish implementation plan

See: backend/app/data/core_system.py

Migration Status
================

COMPLETED
---------

1. core_system.py (CREATED Apr 29)
   - Full C.O.R.E. system definition with all stages
   - Customer Motivators mapping
   - Helper functions for stage lookups
   - System prompt context

IN PROGRESS - BACKEND CODE (12 files)
------------------------------------

Files using EASYStageProgress, EASY stage references, or ENGAGE/ASK/SHOW/YES:

CRITICAL (Coach scoring and analysis):
  [ ] backend/app/agents/state.py
      - Replace: SalesStage.ENGAGE, ASK, SHOW, YES
      - Replace: EASYStageProgress class
      - With: CoreStageProgress class
      - Stages: CONNECT, OBSERVE, RECOMMEND, EXECUTE

  [ ] backend/app/agents/coach/scorer.py
      - Replace: STAGE_WEIGHTS for ENGAGE/ASK/SHOW/YES
      - With: STAGE_WEIGHTS for CONNECT/OBSERVE/RECOMMEND/EXECUTE
      - Update: calculate_stage_score() logic
      - Update: calculate_penalty() for E.A.S.Y. deviations → C.O.R.E. deviations

  [ ] backend/app/agents/coach/prompts.py
      - Replace: COACH_ANALYSIS_PROMPT (all E.A.S.Y. references)
      - Replace: Example techniques (ENGAGE → CONNECT, ASK → OBSERVE, etc.)
      - Replace: Intervention level guidelines (reference C.O.R.E. stages)
      - Source: Use core_system.py content for stage descriptions

  [ ] backend/app/agents/coach/analyzer.py
      - Replace: Stage progression logic (EASY → CORE)
      - Replace: detect_easy_techniques() → detect_core_techniques()
      - Replace: All technique IDs (non_business_greet, established_rapport, etc. stay same, just remap to stages)

  [ ] backend/app/agents/coach/hints.py
      - Replace: Stage-based hint generation
      - Replace: Example phrases (ENGAGE → CONNECT, etc.)
      - Update: Logic using SalesStage references

IMPORTANT (Customer agent and state):
  [ ] backend/app/agents/customer_agent.py
      - Replace: Stage validation using SalesStage enum
      - Replace: stage_progression_logic for EASY → CORE
      - Update: PBM (Pain/Budget/Motivator) references (still apply but in CORE context)

  [ ] backend/app/agents/__init__.py
      - Update: Imports and references to coach modules
      - Check: Any exported classes using EASY naming

  [ ] backend/app/agents/state.py (MAIN FOCUS)
      - Rename: EASYStageProgress → CoreStageProgress
      - Update: Field names to CORE stages
      - Create: Migration helper if needed for old data

MODELS (Data structures):
  [ ] backend/app/models/coach.py
      - Replace: EASYStageProgress references
      - Replace: Stage field types and enums
      - Update: Any validation logic

  [ ] backend/app/models/evaluation.py
      - Replace: E.A.S.Y. references in evaluation schema
      - Update: Grade calculation references to stages

SERVICES:
  [ ] backend/app/services/coach_agent_service.py
      - Replace: EASYStageProgress usage
      - Replace: Stage-based logic
      - Update: generate_evaluation() to use C.O.R.E. scoring

  [ ] backend/app/services/customer_agent_service.py
      - Replace: Stage progression validation
      - Update: Any E.A.S.Y. references

DATABASE/DATA:
  [ ] backend/app/data/__init__.py
      - Update: Imports to use core_system instead of easy_system
      - Remove: Any easy_system references

NOT NEEDED:
  - backend/app/data/easy_system.py (DELETE when ready - already deleted based on audit)

DOCUMENTATION (20+ files)
-------------------------

PRODUCT & REQUIREMENTS:
  [ ] documentation/SalesTrainer/Architecture & Design/PRODUCT_REQUIREMENTS.md
      - Update: All E.A.S.Y. references to C.O.R.E.
      - Update: Examples and use cases (industry-neutral)
      - Remove: Ashley Furniture-specific language
      - Update: Target Markets section (make it universal)

ARCHITECTURE:
  [ ] documentation/SalesTrainer/Architecture & Design/AGENT_FLOW.md
      - Replace: E.A.S.Y. with C.O.R.E. throughout
      - Update: Stage descriptions (ENGAGE→CONNECT, ASK→OBSERVE, SHOW→RECOMMEND, YES→EXECUTE)
      - Update: Coach analysis techniques
      - Update: Session scoring references

  [ ] documentation/SalesTrainer/Architecture & Design/DATABASE_SCHEMA.md
      - Update: evaluations table stage_progress field definition
      - Update: Any E.A.S.Y. methodology references
      - Update: Examples showing stage breakdown

  [ ] documentation/SalesTrainer/Architecture & Design/index.md
      - Update: Architecture highlights section
      - Update: Design decision table

  [ ] documentation/SalesTrainer/Architecture & Design/SESSION_STATE_RESUMPTION.md
      - Update: Stage and progress references
      - Update: Examples

  [ ] documentation/SalesTrainer/Architecture & Design/FUTURE_API_ENDPOINTS.md
      - Update: References to stage progress tracking

API & FEATURES:
  [ ] documentation/SalesTrainer/API Documentation/API_SPECIFICATION.md
      - Update: Evaluation response examples (show stage_progress with CONNECT/OBSERVE/RECOMMEND/EXECUTE)
      - Update: Coach analysis examples
      - Update: Any E.A.S.Y. references in descriptions

  [ ] documentation/SalesTrainer/Features/AshleyFurnitureEASYSellingSystem.md
      - RENAME TO: UniversalCORESellingSystem.md (or similar)
      - Update: All content to reference C.O.R.E.
      - Remove: Ashley Furniture specific examples
      - Add: Industry-neutral examples
      - Update: Principles section (E.A.S.Y. → C.O.R.E.)

  [ ] documentation/SalesTrainer/Features/index.md
      - Update: References to EASY system
      - Link to renamed C.O.R.E. system doc

GETTING STARTED:
  [ ] documentation/SalesTrainer/Getting Started/BACKEND_SETUP.md
      - Update: Any E.A.S.Y. methodology references
      - Update: Coach agent description

  [ ] documentation/SalesTrainer/Getting Started/FRONTEND_SETUP.md
      - Update: References to E.A.S.Y. checklist
      - Update: To C.O.R.E. stages

  [ ] documentation/SalesTrainer/Getting Started/PROJECT_README.md
      - Update: All E.A.S.Y. references
      - Update: System description to be universal

VAULT INDEX:
  [ ] documentation/SalesTrainer/INDEX.md
      - Update: Welcome message (remove Ashley reference)
      - Update: Any system methodology references

CLEANUP DOCS (secondary):
  [ ] documentation/SalesTrainer/Cleanup/uncertain/STAKEHOLDER_FEEDBACK_ANALYSIS.md
      - Update: References to old system
      - Update: Context for architectural decisions

  [ ] Other cleanup docs (RAG phases, etc.) - lower priority

Migration Approach
==================

Phase 1: Backend Code (Classes and Enums)
-----------------------------------------

1. Create CoreStageProgress model
   - Copy EASYStageProgress
   - Rename stage fields to CONNECT, OBSERVE, RECOMMEND, EXECUTE
   - Add migration notes

2. Update SalesStage enum
   - Add CONNECT, OBSERVE, RECOMMEND, EXECUTE
   - Keep ENGAGE, ASK, SHOW, YES temporarily as aliases (for DB compatibility)

3. Update scoring logic
   - Rename STAGE_WEIGHTS keys
   - Update calculate_score() to use new stages
   - Update penalties for new stage order

4. Update coach prompts
   - Replace COACH_ANALYSIS_PROMPT with C.O.R.E. version
   - Keep technique IDs but remap to new stages
   - Update example phrases

Phase 2: Services and Integration
---------------------------------

1. Update coach_agent_service
   - Use CoreStageProgress instead of EASYStageProgress
   - Update evaluate() to use new scoring

2. Update customer_agent_service
   - Update stage progression logic

3. Update all imports
   - Replace easy_system imports with core_system
   - Update DI and dependencies

Phase 3: Database Compatibility
-------------------------------

Consider:
- Existing evaluations with EASY stage_progress
- Migration strategy (backfill? Keep both? Deprecate old?)
- API response versioning if needed

Phase 4: Documentation
---------------------

Update all markdown files with systematic find-and-replace:
- "E.A.S.Y." → "C.O.R.E."
- "ENGAGE" → "CONNECT"
- "ASK" → "OBSERVE"
- "SHOW" → "RECOMMEND"
- "YES" → "EXECUTE"
- "Ashley Furniture" references → Remove or make generic
- "easy" (lowercase) → "core"

Phase 5: Testing
---------------

- Update all test files that reference EASY stages
- Verify scoring still works with new weights
- Test coach analysis with new prompts
- Integration tests with new stage progression

Phase 6: Database Migration (if needed)
--------------------------------------

- Plan for existing sessions with EASY stage_progress
- Decide: Update in-place, create new field, or keep both?
- Update Firestore documents if needed

Search and Replace Patterns
===========================

Backend Code (case-sensitive):
- "EASYStageProgress" → "CoreStageProgress"
- "SalesStage.ENGAGE" → "SalesStage.CONNECT"
- "SalesStage.ASK" → "SalesStage.OBSERVE"
- "SalesStage.SHOW" → "SalesStage.RECOMMEND"
- "SalesStage.YES" → "SalesStage.EXECUTE"

Documentation:
- "E.A.S.Y." → "C.O.R.E."
- "E.A.S.Y" → "C.O.R.E"
- "EASY" → "CORE"
- "Engage" → "Connect"
- "Ask" → "Observe"
- "Show" → "Recommend"
- "Yes" → "Execute"

Notes
=====

- Do NOT delete old EASY references until all code is migrated
- Consider backward compatibility with existing evaluations
- Update database schema documentation
- Update API response examples
- Consider API versioning if breaking changes

File Count Summary
==================

Backend Code Files: 12
Documentation Files: 20+
Total Files to Update: 30+

Risk Areas
==========

CRITICAL:
- Coach scoring logic (stage weights, penalties)
- Stage progression validation
- Prompt templates for coach analysis

HIGH:
- Database queries expecting stage_progress fields
- API responses with stage data
- Frontend evaluation display (if it references stages)

MEDIUM:
- Documentation references (non-breaking)
- Setup guides and examples

Rollback Plan
=============

If migration fails:
1. Revert all code changes to last working commit
2. Keep core_system.py as reference
3. Restart with phased approach
4. Consider hybrid approach (support both systems temporarily)
