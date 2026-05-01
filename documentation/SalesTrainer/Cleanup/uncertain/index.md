# Uncertain - Review for Relevance

**Status:** These documents contain valuable context but may be outdated. Review before archiving or deleting.

**Tags:** #deprecated #feedback #context #maybe-useful

## Why These Are Here

These files contain **user/stakeholder feedback, architectural context, or product decisions** that are not directly superseded by current code, but also may not be critical for future development. They're useful for **historical context** but require human judgment on whether to keep or archive.

## Contents

### User Testing & Feedback

- **LRIGGS_TESTING_ANALYSIS.md**
  - **What it is:** Analysis of one user's (Leah Riggs) testing sessions
  - **Key findings:** 
    - 134 total sessions, 28 transcripts captured
    - 100% session abandonment (all transcripts marked "abandoned")
    - 0 customer messages recorded (only user messages)
    - Consistent testing pattern on E.A.S.Y. ENGAGE/ASK stages
  - **Relevance:** 
    - ✅ Shows test coverage and testing patterns
    - ✅ Identifies potential technical issues (session abandonment, message recording)
    - ❌ Specific to one user from Feb 17, 2026
  - **Keep if:** You need to understand historical testing behavior or reproduce the session abandonment issue
  - **Delete if:** This was a known testing phase that's concluded and issues were resolved

---

### Architectural Feedback & Context

- **STAKEHOLDER_FEEDBACK_ANALYSIS.md**
  - **What it is:** Comparison of old system vs. current Gemini 2.5 Flash architecture
  - **Key content:**
    - Addresses feedback on transcript accuracy (now dual-stream transcription)
    - Documents session reliability improvements
    - Explains E.A.S.Y. system tracking implementation
    - Compares old vs. new approach across 4+ domains
  - **Relevance:** 
    - ✅ Documents **WHY** architectural choices were made
    - ✅ Shows what problems were solved in migration
    - ✅ Useful for understanding system evolution
    - ❌ References old system that no longer exists
  - **Keep if:** You need to understand architectural decisions or compare old vs. new approaches
  - **Delete if:** The old system is completely forgotten and comparisons are no longer useful

---

### Product Decisions & Cut Features

- **cutfeatures.md**
  - **What it is:** Archive of intentionally cut features from the product scope
  - **Features documented:**
    - **Safe Space** - Judgment-free debrief environment (Mentor/Manager persona)
    - **General AI Chat** - Unrestricted voice conversations
    - **The Luxe Lounge** - Asynchronous learning via AI-generated podcasts
  - **Relevance:** 
    - ✅ Documents product **boundaries** and scope decisions
    - ✅ Shows what was considered but intentionally rejected
    - ✅ Prevents "reinventing the wheel" if similar ideas proposed
    - ❌ Features are no longer in scope
  - **Keep if:** You need to remember why certain features were cut, or similar ideas come up again
  - **Delete if:** The feature ideas have zero chance of being reconsidered

---

## Decision Framework

**Keep these files if:**
- Team regularly references architectural context from the old system
- User testing insights drive current bug fixes or improvements
- Product scope needs to be defended against feature creep
- Historical context helps onboarding or understanding decisions

**Consider consolidating if:**
- Move key insights into architecture docs ([[PRODUCT_REQUIREMENTS|../../Architecture%20&%20Design/PRODUCT_REQUIREMENTS.md]], [[STAKEHOLDER_FEEDBACK_ANALYSIS|STAKEHOLDER_FEEDBACK_ANALYSIS.md]])
- Extract testing insights into testing strategy docs
- Summarize cut features in product spec for quick reference

**Delete if:**
- Old system is completely deprecated and no longer referenced
- Testing cycle is closed and issues resolved
- Feature scope is locked and unlikely to change

---

## Recommended Actions

### Option A: Keep as-is (safest)
- Leave in `uncertain/` for future reference
- Update parent index to clarify their status
- No immediate action needed

### Option B: Consolidate
- Extract key insights into main documentation
- Delete original files once consolidated
- Add cross-references in relevant docs

### Option C: Full Delete
- Remove files if team confirms they're no longer useful
- Archive to external storage if needed for compliance

---

**Questions before deciding?** Discuss with team:
- Do we still compare to the old architecture?
- Are Leah's testing patterns relevant to current issues?
- Do product boundaries need historical context?

Back to [[Cleanup/index.md|../index.md]]
