# Cleanup - Archived & Legacy Docs

**Tags:** #deprecated #archived #legacy

This folder preserves documentation that is not part of active development but may still hold reference value.

## Quick Navigation

### [[archived/index.md | Archived Content]]
**1 file** - Domain-specific or legacy examples
- `AshleyFurnitureEASYSellingSystem.md` - Legacy E.A.S.Y. system example (archived 2026-07-13)

**Reason for archival:** SalesTrainer Pro has moved to universal C.O.R.E. Selling System and domain-agnostic framework.

### [[uncertain/index.md | Uncertain - Needs Review]]
**3 files** - Potentially useful, requires human judgment
- `LRIGGS_TESTING_ANALYSIS.md` - User testing insights from Feb 2026
- `STAKEHOLDER_FEEDBACK_ANALYSIS.md` - Architectural improvements documented
- `cutfeatures.md` - Intentionally cut features (product boundaries)

**Action:** Keep, consolidate, or delete based on team decision.

---

## When to Review Cleanup

**Review if:**
- You need historical context for a feature or architecture decision
- You're investigating why something was cut or changed
- You need to understand product scope boundaries

**Don't review if:**
- You're looking for current architecture → [[Architecture|../Architecture%20&%20Design/index.md]]
- You're implementing a new feature → [[Features|../Features/index.md]]
- You need setup instructions → [[Getting Started|../Getting%20Started/index.md]]

---

## Summary of What's Here

| Category | Count | Recommendation |
|----------|-------|-----------------|
| **Archived** | 1 file | Reference only |
| **Uncertain** | 3 files | Review & decide per-file |

**2026-07-13 cleanup (agent-hardening sync):**
- Moved Ashley Furniture EASY Selling System doc to `archived/` folder (legacy domain-specific content, superseded by universal C.O.R.E. system)
- Removed references to furniture-specific examples from active docs
- Updated all index files with Python 3.13+ requirement, multi-provider voice notes, and current timestamps
- Verified RAG docs previously deleted (2026-07-02) remain removed

**2026-07-02 cleanup:** The former "Marked for Deletion" folder (RAG phase 1-3 implementation docs, RAG integration plan, RAG infrastructure setup, the 429 error incident report, and an old PR planning doc) was removed. All of it was superseded by shipped code and git history — nothing was lost.

---

**Last updated:** 2026-07-13

Back to [[INDEX|../INDEX.md]]
