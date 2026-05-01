# Testing Analysis: Leah Riggs (LRiggs@ashley.com)

**Analysis Date:** February 17, 2026
**User ID:** 423c48b5-9be9-4c05-a262-73795453e0b4

---

## Executive Summary

Leah Riggs is an active tester with **134 total sessions** and **28 transcripts** captured. Analysis reveals consistent testing patterns focused on **rapport building** and **discovery questions**, but highlights **critical technical issues** with session abandonment and message recording.

### Key Findings
- ✅ **Active tester**: 20 sessions on Feb 16 alone
- ❌ **100% session abandonment**: All 28 transcripts show "abandoned" status
- ❌ **Zero customer responses**: 224 user messages, 0 customer messages recorded
- ✅ **Consistent testing approach**: Clear focus on E.A.S.Y. system ENGAGE and ASK stages
- ✅ **Persona preference**: Favors easier personas (eager_newlywed, busy_parent)

---

## Quantitative Analysis

### Session Statistics
| Metric | Value |
|--------|-------|
| Total Sessions | 134 |
| Transcripts Captured | 28 (20.9%) |
| Total Messages | 443 |
| User Messages | 224 |
| **Customer Messages** | **0 ⚠️** |
| Avg Messages/Session | 15.8 |
| Avg Session Duration | 3.2 minutes |

### Session Breakdown
| Type | Count |
|------|-------|
| Training | 28 |
| Evaluation | 0 |

### Status Distribution
| Status | Count | Percentage |
|--------|-------|------------|
| Abandoned | 28 | **100%** ⚠️ |
| Completed | 0 | 0% |
| Active | 0 | 0% |

### Persona Usage
| Persona | Sessions | Percentage |
|---------|----------|------------|
| eager_newlywed | 12 | 42.9% |
| busy_parent | 8 | 28.6% |
| skeptical_shopper | 5 | 17.9% |
| price_resistant | 3 | 10.7% |

**Insight:** Strong preference for high/medium regard personas (eager_newlywed, busy_parent = 71.5% of sessions)

### Difficulty Distribution
| Difficulty | Count | Notes |
|------------|-------|-------|
| medium | 7 | Old value |
| easy | 7 | Old value |
| medium_regard | 6 | New value |
| high_regard | 5 | New value |
| hard | 3 | Old value |

**Insight:** Mix of old and new difficulty values suggests testing occurred during the migration period.

### Testing Timeline
| Date | Sessions |
|------|----------|
| 2026-02-13 | 8 |
| 2026-02-16 | 20 |

**Insight:** Intense testing burst on Feb 16 (20 sessions in one day).

---

## Qualitative Analysis

### Testing Strategy

#### 1. **Rapport Building (ENGAGE Stage)**
Leah consistently opens with non-business conversation:
- "Hello, it's wonderful weather we're having today"
- "I like your jacket. Did you go to Missouri State?"
- "Nice weather we're having today"

**Finding:** Strong focus on establishing rapport before product discussion. This aligns with E.A.S.Y. system best practices.

#### 2. **Discovery Questions (ASK Stage)**
Common phrase patterns reveal systematic discovery approach:

| Phrase | Frequency | Purpose |
|--------|-----------|---------|
| "Can you tell" | 21x | Open-ended discovery |
| "What kind of" | 12x | Product preference |
| "What do you" | 11x | Lifestyle questions |
| "Tell me a little" | 10x | Building context |
| "Are you looking" | 9x | Needs assessment |

**Finding:** Focused on ASK stage questioning. Strong use of open-ended questions.

#### 3. **Session Length**
- Average 15.8 messages per session
- Average 3.2 minutes duration
- Most sessions have 4-6 messages

**Finding:** Sessions are short, suggesting quick tests of specific interactions rather than full role-play scenarios.

---

## Critical Issues Identified

### 🚨 Issue 1: 100% Session Abandonment

**Problem:**
All 28 transcripts show `status: abandoned`. This suggests:
1. Sessions are not being properly completed via UI
2. Auto-abandonment logic may be too aggressive
3. Testing workflow doesn't include proper session closure

**Impact:**
- Cannot track true session completion rates
- Evaluation metrics will be skewed
- Session history looks worse than reality

**Recommendations:**
1. Add "End Session" button in UI with clear visual prominence
2. Increase auto-abandonment timeout (currently may be too short)
3. Add session status indicator to UI (active/paused/completed)
4. Track "intentional abandonment" vs "timeout abandonment" separately

---

### 🚨 Issue 2: Zero Customer Messages Recorded

**Problem:**
224 user messages but **0 customer responses** in transcripts. This indicates:
1. Customer agent responses not being captured in transcripts
2. WebSocket message flow not recording model responses
3. Transcript creation may be missing customer messages

**Impact:**
- Cannot analyze conversation flow
- Cannot evaluate customer agent quality
- Cannot train or improve persona responses
- Severely limits transcript usefulness

**Recommendations:**
1. **URGENT:** Review `transcript_repository.py` message capture logic
2. Check WebSocket message handling in `gemini_relay.py`
3. Verify `role: "model"` messages are being saved to Firestore
4. Add logging to confirm customer messages are captured
5. Test end-to-end: Send message → Customer responds → Verify in Firestore

**Code to check:**
```python
# In gemini_relay.py - verify this is saving customer messages
async def _handle_customer_message(self, message):
    # Should save to transcript with role="model"
    pass
```

---

### 🚨 Issue 3: Missing Transcripts (106 sessions without transcripts)

**Problem:**
134 sessions created, but only 28 have transcripts (20.9% capture rate).

**Possible causes:**
1. Sessions created but never started (user abandoned at persona selection)
2. WebSocket connection failures before any messages sent
3. Transcript creation only happens after first message exchange
4. Sessions from before transcript feature was implemented

**Recommendations:**
1. Add session lifecycle tracking:
   - `created` → `started` → `active` → `completed`/`abandoned`
2. Only create session after first successful message exchange
3. Add "session_started_at" separate from "created_at"
4. Clean up orphaned sessions (created but never started)

---

## Positive Findings

### ✅ 1. Consistent Testing Approach
Leah follows a systematic testing approach:
1. Rapport building with non-business conversation
2. Transition to discovery questions
3. Tests specific interaction patterns

This indicates she understands the E.A.S.Y. selling system and is testing it methodically.

### ✅ 2. Active User Engagement
20 sessions in a single day shows:
- High motivation to test
- Comfort with the platform
- Willingness to provide implicit feedback through repeated testing

### ✅ 3. Persona Diversity
Testing across 4 different personas (eager_newlywed, busy_parent, skeptical_shopper, price_resistant) shows:
- Understanding of different customer types
- Interest in varied scenarios
- Good test coverage across difficulty levels

### ✅ 4. Focus on Early-Stage Skills
Heavy use of "can you tell", "what kind of", "what do you" shows focus on:
- Building rapport (ENGAGE)
- Discovery questions (ASK)
- Open-ended questioning techniques

This aligns with foundational sales skills training.

---

## Recommendations for Platform Improvements

### Immediate (This Week)

1. **Fix Customer Message Recording**
   - Priority: P0 (Critical)
   - Investigate why customer responses aren't in transcripts
   - Add logging to track message flow
   - Verify WebSocket → Firestore message persistence

2. **Fix Session Status Tracking**
   - Priority: P0 (Critical)
   - Review auto-abandonment logic
   - Add manual "End Session" button
   - Distinguish timeout vs intentional abandonment

3. **Add Session Status Indicator**
   - Priority: P1 (High)
   - Show "Active", "Paused", "Completed" status in UI
   - Visual feedback when session is recording
   - Clear call-to-action to end session properly

### Short-term (Next 2 Weeks)

4. **Improve Session Lifecycle**
   - Priority: P1 (High)
   - Don't create session until first message sent
   - Add `session_started_at` timestamp
   - Clean up orphaned sessions periodically

5. **Add Testing Analytics Dashboard**
   - Priority: P2 (Medium)
   - Show user testing patterns
   - Track persona usage over time
   - Highlight incomplete sessions
   - Surface common questions/phrases

6. **Enhance Transcript Capture**
   - Priority: P1 (High)
   - Ensure all message types are captured (user, model, system)
   - Add message metadata (timestamp, confidence, audio length)
   - Verify transcript completeness on session end

### Medium-term (Next Month)

7. **Add Guided Testing Paths**
   - Priority: P2 (Medium)
   - "Test Rapport Building" → Pre-select eager_newlywed
   - "Test Objection Handling" → Pre-select price_resistant
   - "Full E.A.S.Y. Practice" → Encourage completing all stages

8. **Session Summary on Completion**
   - Priority: P2 (Medium)
   - Show message count
   - Show stage progression
   - Quick feedback: "You asked 8 discovery questions!"
   - Encourage next session

9. **Persona Recommendations**
   - Priority: P3 (Low)
   - "You've practiced with eager_newlywed 12 times. Try skeptical_shopper for a challenge!"
   - Track skill progression by persona difficulty

---

## Insights for Training Content

### 1. **Leah's Testing Focus Areas**
Based on question patterns, Leah is practicing:
- **Rapport building**: Personal questions, weather, life events
- **Open-ended discovery**: "Tell me", "What kind of", "Can you tell"
- **Lifestyle questions**: Living room, seasons, preferences

**Recommendation:** Create specific training modules for:
- Rapport → Discovery transitions
- Deepening discovery questions (PBM identification)
- Moving to SHOW stage (product demonstrations)

### 2. **Gaps in Testing Coverage**
Leah's sessions show limited practice of:
- SHOW stage (product demonstrations)
- YES stage (closing techniques)
- Objection handling (only 3 price_resistant sessions)

**Recommendation:**
- Encourage testing later stages
- Add guided scenarios that force SHOW/YES practice
- Create "Objection Handling Challenge Week"

### 3. **Short Session Pattern**
Average 15.8 messages = ~4-8 back-and-forth exchanges before abandonment.

**Possible reasons:**
- Testing specific interactions, not full scenarios
- Getting stuck and restarting
- Technical issues forcing restarts
- Unclear how to progress to next stage

**Recommendation:**
- Add stage progression hints in UI
- "Ready to move to SHOW stage?" prompt
- Visual indicator of E.A.S.Y. stage progress
- Celebrate stage completions

---

## Testing Quality Assessment

### Strengths
✅ Consistent testing schedule
✅ Systematic approach to rapport/discovery
✅ Multiple persona testing
✅ High volume of attempts (shows engagement)

### Areas for Improvement
❌ Sessions not being completed properly (100% abandonment)
❌ Limited objection handling practice
❌ Limited SHOW/YES stage practice
❌ Sessions too short to complete full scenarios

### Overall Grade: **B-**
- **Engagement:** A+ (very active tester)
- **Breadth:** B (good persona coverage, but limited stage coverage)
- **Depth:** C (sessions too short, incomplete scenarios)
- **Technical:** D (100% abandonment, missing data)

---

## Action Items for Product Team

### Critical (Fix This Week)
- [ ] Investigate why customer messages not captured in transcripts
- [ ] Review session abandonment logic
- [ ] Add "End Session" button to UI
- [ ] Add logging for message capture flow

### High Priority (Next 2 Weeks)
- [ ] Add session status indicator to UI
- [ ] Improve session lifecycle (don't create until started)
- [ ] Add session summary on completion
- [ ] Test transcript capture end-to-end

### Medium Priority (Next Month)
- [ ] Create testing analytics dashboard
- [ ] Add guided testing paths
- [ ] Create objection handling training content
- [ ] Add stage progression hints

---

## Conclusion

Leah Riggs demonstrates **strong engagement** and a **systematic testing approach** focused on rapport building and discovery questions. However, **critical technical issues** with transcript capture and session status tracking are limiting the platform's ability to:

1. Track true training progress
2. Provide meaningful feedback
3. Analyze conversation quality
4. Improve AI persona responses

**Priority 1:** Fix customer message recording
**Priority 2:** Fix session abandonment tracking
**Priority 3:** Improve session completion UX

Once technical issues are resolved, Leah's testing patterns suggest she would benefit from:
- Guided scenarios that encourage full E.A.S.Y. system practice
- More objection handling scenarios
- Stage progression feedback
- Session completion encouragement

---

## Appendix: Sample Session Analysis

### Session: de952963 (Feb 16, 22:54)
**Persona:** eager_newlywed (high_regard)
**Messages:** 6
**Status:** abandoned

**User messages:**
1. "I like your jacket. Did you go to Missouri State?" → Rapport building
2. "I noticed your jacket said Missouri State, if you didn't go there, do you have any family that did?" → Follow-up rapport
3. "Did you get the chat from a thrift store?" → Continued personal questions

**Analysis:**
- Strong rapport building attempt
- 3 consecutive personal questions
- No transition to product discussion
- Abandoned after 6 messages
- **Missing customer responses** - Cannot analyze interaction quality

**What we can't see (due to missing customer messages):**
- How customer responded to rapport attempts
- Whether customer was receptive or dismissive
- If conversation naturally flowed or felt forced
- Why session ended (stuck? frustrated? completed goal?)

This exemplifies the critical need for customer message capture.
