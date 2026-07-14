# Backend Agent Flow: Step-by-Step Guide

## Overview

When a salesperson speaks during a training session, several things happen at once:
1. Their voice is sent to Google's Gemini AI, which plays a customer
2. The customer responds with their own objections and concerns
3. A coaching agent watches the conversation and offers hints
4. The system tracks the salesperson's progress through a sales methodology (C.O.R.E.)

This document walks through exactly what happens, turn by turn, and flags design questions we should revisit.

---

## Turn 1: User Speaks First Time

### Step 1.1: Audio Arrives at Backend
- Salesperson's phone/browser sends audio (16kHz mono) over WebSocket
- Backend receives it in the `GeminiWebSocketRelay` class
- Audio is saved to a buffer (so we can store it later)
- Audio is immediately forwarded to Google Gemini

### Step 1.2: Gemini Plays the Customer
- Gemini receives the audio and converts it to text ("I need a new couch")
- Gemini uses a system prompt to act as an AI customer with a personality/mood
- Gemini speaks back with a customer response ("Tell me more...")
- Gemini streams multiple pieces back: transcribed text, audio of the response, and its internal reasoning

**Architecture note**: Streaming transcription, audio, and reasoning separately enables real-time text display on the HUD while audio is still being generated, reducing perceived latency even though total processing time is unchanged.

### Step 1.3: Stream Data Back to Salesperson
- Backend takes Gemini's streaming data and sends it to the salesperson's screen/speakers
- Text appears on the HUD (head-up display) in real time
- Audio plays through speakers so it feels like a real conversation
- Everything is buffered temporarily (in `_pending_user_transcription`, `_pending_assistant_transcription`, etc.)

### Step 1.4: Turn Ends When Gemini Says So
- Gemini sends an `end` signal to tell us the customer's turn is done
- All temporary buffers are flushed to `_message_buffer`
- Each message gets a unique ID and timestamp
- Now we're ready to analyze what just happened

### Step 1.5: Analyze the Customer's Response & Update Mood (LangGraph State Machine)
- `CustomerAgentGraph` (a LangGraph state machine) processes the salesperson's message through a 5-node pipeline:

  1. **analyze_input** - Detects salesperson techniques in the message:
     - Looks for greetings ("hi", "hello", "nice to")
     - Detects questions (signaling discovery behavior)
     - Identifies pushy language ("buy now", "limited time")
     - Checks for acknowledgment of concerns ("I understand", "makes sense")
     - Flags disrespectful language (insulting words or phrases)
     - Returns results in runtime-only `_analysis` key

  2. **update_mood** - Behavior-driven mood update based on `_analysis`:
     - Positive actions (acknowledgment, greeting early in call) → mood improves
     - Negative actions (insults, pushiness) → mood worsens or decays
     - Disrespect triggers a 2-step mood drop (hits hardest)
     - No positive/negative action triggers probabilistic mood decay (difficulty-dependent)
     - Returns updated `mood` and `regard_level`

  3. **check_objection** - Determines whether to inject a customer objection
     - Routing logic is in `_route_objection` (conditional edge)
     - Automatic timing: turns 2-4 for medium/low/no regard personas
     - Behavior-responsive: if mood is skeptical/frustrated, difficulty-based chance to inject

  4. **inject_objection** - Selects and stages an objection
     - Picks from pool of objections not yet raised
     - Hard personas prioritize hardest objections; others pick first available
     - Stores selected objection in runtime-only `_injected_objection` key
     - Increments `objections_raised` list

  5. **generate_response** - LLM call to generate customer response
     - In voice mode: `_skip_response=True` bypasses LLM call (Gemini Live generates audio instead)
     - In text mode: builds system prompt with persona + objection instruction
     - If `_injected_objection` is set, adds: "[Naturally work this concern into your response: '...']"
     - Returns `AIMessage` with customer's reply
     - Clears runtime keys after consumption

**Runtime-Only State Keys** (LangGraph state channels, not persisted):
- `_analysis` - Behavior detection results from analyze_input node
- `_injected_objection` - Objection selected for this turn (cleared after generate_response)
- `_skip_response` - Flag for voice mode to skip LLM call (True = Gemini Live handles reply)
- `_last_usage` - Token usage from LLM completion (for analytics)

**Why separate Gemini + LangGraph?**
Gemini generates the *customer's voice* (realistic audio/conversation). LangGraph generates the *customer's internal state* (mood, objections). This separation allows:
- Mood to evolve realistically based on salesperson behavior (not just Gemini's whim)
- Objections to be injected at strategic times (e.g., when customer is skeptical)
- Analytics to track customer state independent of conversation content
- Testing/evals to swap out Gemini for other LLM providers while keeping state logic intact

### Step 1.6: Coach Analyzes Salesperson Technique (Runs in Background)
- The `CoachAgentService` analyzes the salesperson's message asynchronously (non-blocking)
- Analysis checks salesperson usage of C.O.R.E. techniques:
  - **CONNECT**: Warm greeting, establish credibility, create comfort
  - **OBSERVE**: Needs discovery, goal identification, motivator mapping
  - **RECOMMEND**: Solution presentation, value connection, risk mitigation
  - **EXECUTE**: Commitment request, objection handling, finalize agreement
- Analyzer produces structured output:
  - `techniques_detected` - List of C.O.R.E. techniques observed
  - `stage_items_completed` - Checklist items the salesperson checked off
  - `pbms_acknowledged` - Personal Buying Motivators the salesperson recognized
  - `intervention_level` - Severity of any detected issues (NONE, SUGGESTION, WARNING, CRITICAL)
- For **training mode** only: generates coaching hint if intervention_level != NONE
- For **evaluation mode**: silent (no hints shown to trainee)
- Hint is added to WebSocket queue and sent to client (throttled to max 1 hint/10 seconds)

### Step 1.7: Scores Don't Get Calculated Yet
- We track mood and state, but we don't calculate a final score until the session ends
- This makes sense because a salesperson can recover from a mistake later in the conversation
- But it also means the salesperson doesn't get real-time feedback on their overall performance

---

## Turn 2: Salesperson Responds

### Step 2.1: Salesperson Speaks Again
- Same as Turn 1: audio is sent, Gemini transcribes and responds
- Example: Salesperson says "Your concern about price is valid. We offer financing..." → Gemini responds "Interesting, tell me about that..."

### Step 2.2: Customer State Updates
- The customer's mood, regard, and resolved objections are updated based on the new exchange
- Turn counter goes to 2
- All messages added to history

**Design note**: By this point, the salesperson has had one chance to respond. If they did well, the customer's mood improves. If they fumbled, mood drops.

### Step 2.3: Coach Analyzes Round 2
- Checks whether the salesperson addressed the objection directly
- Looks for C.O.R.E. technique usage (RECOMMEND stage: presenting a solution)
- Tracks which customer concerns were acknowledged vs. resolved
- Generates another coaching hint if needed

### Step 2.4: Session Continues or Ends
- If the salesperson says "I'm done" or the customer says "yes, I'll buy," session ends
- Otherwise, back to Step 2.1 for Turn 3, Turn 4, etc.

---

## End of Session: Save Everything & Calculate Score

### Step 3.1: Session Ends
- Salesperson clicks "End Session" or disconnects
- The backend calls `_persist_conversation()` to save all data

### Step 3.2: Save Raw Data to Database
- **Session record**: Status = COMPLETED, duration, message count, final customer state
- **Transcript**: All messages, internal reasoning, word count, timestamps

**Design question**: We store internal reasoning from Gemini's thinking process, but we never show it to the salesperson. Is this useful for analytics? Or is it just bloat?

### Step 3.3: Generate Final Coaching Score
- The coach agent scores the entire conversation based on C.O.R.E. framework completion:
- **Scoring breakdown:**
  - CONNECT: 15% (did they build initial rapport?)
  - OBSERVE: 30% (did they uncover customer needs and motivations?)
  - RECOMMEND: 30% (did they present a relevant solution?)
  - EXECUTE: 25% (did they close/get agreement?)
  - **Bonus points** (+5-10%): acknowledged customer concerns, recovered from objections, matched customer motivators
  - **Penalty points** (-5-10%): missed key discovery questions, mismatched recommendations, gave up on objections
  - **Final grade:** A (90+), B (80-89), C (70-79), D (60-69), F (<60)

**Scoring philosophy:** C.O.R.E. provides structure without being rigid. Sales calls vary (some customers disqualify early, some have only objections), but the framework still guides learning. Salespeople learn that skipping OBSERVE (needs discovery) leads to weak RECOMMEND stages, even if they technically "made a sale."

### Step 3.4: Save Evaluation Report
- Store: Final score, grade, breakdown by stage, which customer concerns were addressed, which objections were resolved
- This is what the salesperson sees after the call

---

## What Changes Each Turn

| What | Turn 1 | Turn 2 | After Session |
|-----|--------|--------|----------------|
| Customer mood | Starts neutral, shifts based on salesperson | Can improve or drop | Frozen in report |
| Customer regard | Low → Medium | Medium → High (if sales rep does well) | Frozen in report |
| Sales technique progress | CONNECT stage started | CONNECT done, OBSERVE started | All stages scored |
| Customer objections | None yet | "Price too high" stated | How many were resolved? |
| Coaching score | Not calculated | Not calculated | A/B/C/D/F |

---

## How the System is Wired

### What Happens When

| Timing | What | Who |
|--------|------|-----|
| **During conversation** | Customer mood, objections, real-time hints | Gemini + LangGraph + Coach |
| **After each turn (async)** | Coaching feedback | Coach agent in background |
| **When session ends** | Final score and grade | Coach agent |

### The Data Pipeline

```
Salesperson speaks (audio)
  ↓
Gemini transcribes & plays customer
  ↓
Show text & audio to salesperson
  ↓
Customer state updated (mood, objections)
  ↓
Coach analyzes salesperson's technique (background)
  ↓
Repeat → New turn
  ↓
Session ends → Final score calculated
```

### Safety & Fallbacks

- If coach analysis breaks: session continues, salesperson doesn't get hints but roleplay works fine
- If WebSocket drops: can reconnect up to 3 times
- If database save fails: messages are still in memory, can retry

---

## RAG Integration: Adding Product Knowledge to Hints

If enabled, the system can pull in product/industry info to make hints more specific.

### How It Works

1. Coach detects something: "Customer is worried about price"
2. Coach asks the database: "Find me content about financing options"
3. Database does a vector search: finds relevant product docs
4. Filters by category (real estate, SaaS, etc.)
5. Returns top 3 results
6. Coach includes these in the hint: "The 30-year fixed option with no points might address their concern"

### Settings

- `RAG_ENABLED`: Turn this on/off
- `RAG_USE_HYBRID_SEARCH`: Mix vector + keyword search (slower but more accurate)
- `RAG_USE_RERANKING`: Have the LLM rank results again (adds latency)
- `RAG_USE_CONVERSATION_CONTEXT`: Look at full conversation history when searching (more context, slower)
- `RAG_TOP_K`: How many results to grab (default 3)

**Design question**: RAG adds latency (searching, ranking, integrating results). Do hints need to be this sophisticated? Or would generic hints work just as well? We should measure if RAG actually changes salesperson performance vs. simple rule-based hints.

---

## Limiting Hint Spam

Coaches don't give feedback constantly—it would be annoying. The system throttles hints so salespeople aren't overwhelmed:

### Rules

- Max 1 hint per 10 seconds
- High-priority hints (CRITICAL, WARNING) skip the queue and send immediately
- Lower-priority hints (SUGGESTION, INFO) wait
- When the 10-second window resets, queued hints get sent

### Example Timeline

```
0s:   Coach says "You should ask about their budget" → Send immediately
3s:   Coach says "Try mirroring their language" → Queued (only 3s passed)
12s:  10 seconds are up → Send the queued hint
15s:  Coach says "Acknowledge the objection" → Send immediately (10s elapsed)
```

**Design question**: Is 10 seconds the right interval? Are we throttling based on time, or should we throttle based on turns? What if a turn takes 30 seconds? The salesperson would sit waiting for a hint they need now.

---

## What Happens if Someone Abandons a Session

If a salesperson closes the browser, their connection drops, or they walk away without clicking "End Session":

### Detection

- WebSocket disconnects without a proper goodbye message
- No reconnect attempt within a grace period
- System marks session as "abandoned"

### What Gets Saved

- Any transcript that was already stored (turns 1-3, etc.)
- But NO final evaluation or score
- The session is excluded from their history by default

### Why This Matters

- High abandonment rate might mean the app is frustrating
- Or the difficulty is too high
- Or there are connection issues

### What Users See Next Time

- "Your previous session was abandoned. Start a new one?"
- The old session's transcript is kept for you to review, but it wasn't scored

---

## Summary in 5 Steps

1. **Salesperson speaks** → Gemini transcribes and plays customer
2. **Turn ends** → State updates: customer mood, objections, technique progress
3. **Coach analyzes** → Looks for C.O.R.E. techniques, sends a hint (background)
4. **Repeat for next turn** → Same flow, state gets richer
5. **Session done** → Score calculated, report shown, data saved

The goal: real-time coaching feedback + a final performance report.

---

## Design Critique & Philosophy Questions

### The Core Issue: Is This Architecture Right for Sales Training?

This system was designed to simulate a sales call and score performance. But we should question some fundamental choices:

#### Problem 1: Too Many Agents, Unclear Responsibilities

**Current state**: We have 3 AI agents doing different things:
1. **Gemini Live** - Plays the customer (roleplay)
2. **LangGraph Customer Agent** - Tracks customer state (mood, objections)
3. **Coach Agent** - Analyzes salesperson technique

**The issue**: Why track customer state *after* Gemini already generated it? Gemini decides the customer is "skeptical" by writing a skeptical response. Then LangGraph re-analyzes the same text and says "mood = skeptical." This is redundant.

**Better approach**: Either:
- Let Gemini play the customer AND track its own state (no LangGraph needed)
- OR have LangGraph play the entire customer (roleplay + state), and don't use Gemini for roleplay
- Trying to do both is complexity with no benefit

#### Problem 2: Asynchronous Coaching Feels Slow

**Current state**: Coach analyzes Turn 1 while Turn 2 is happening. Hints are queued and throttled. So feedback is always 1-2 turns behind.

**The issue**: Real sales coaches give immediate feedback ("You just missed an objection handling opportunity"). Our salesperson doesn't get the hint until after they've already moved on. This reduces learning effectiveness.

**Better approach**:
- Make coach analysis synchronous and block on it (accept the latency cost)
- OR only show hints at natural pause points (when customer goes silent)
- OR give hints *before* the salesperson speaks (predictive hints: "This customer seems price-sensitive, so prepare a financing angle")

#### Problem 3: Scoring System Assumes Linear Flow

**Current state**: We score CONNECT → OBSERVE → RECOMMEND → EXECUTE as fixed stages with weights.

**The issue**: Real sales don't always follow this order. A customer might jump straight to "what's the price?" (EXECUTE) before OBSERVE is complete. A salesperson might circle back to CONNECT after an objection. Our scoring penalizes non-linear sales flows even when they're appropriate.

**Better approach**:
- Score based on outcome (did you make the sale?) not adherence to a framework
- Let C.O.R.E. be suggestions, not mandatory stages
- Weight scores differently by industry (real estate closing rates are different from SaaS)
- Or admit that scoring is too subjective for an LLM and just give feedback instead of grades

#### Problem 4: Customer Mood Drives Everything But Salesperson Can't See It

**Current state**: The customer's mood changes throughout the conversation. If mood drops, objections emerge. But the salesperson doesn't see the mood meter—only the coach hints hint at it.

**The issue**: Sales is about reading the room. If we're tracking mood, why hide it? A real coach would say "they're getting frustrated." Our app says nothing.

**Better approach**:
- Show mood/sentiment explicitly on the HUD (customer seems [INTERESTED] or [SKEPTICAL])
- Let the salesperson learn to recognize these signals themselves
- OR hide mood entirely and force the salesperson to infer it from customer responses (more realistic)

#### Problem 5: RAG Adds Complexity Without Proving Value

**Current state**: We search a knowledge base, re-rank results, and inject them into coach hints.

**The issue**: Does this help? We have no data. A simple rule ("customer mentioned price → suggest financing") might work as well. RAG adds latency and failure points (broken vector index, bad embeddings, wrong results ranked high).

**Better approach**:
- Measure: Do sessions with RAG-enabled hints outperform sessions with simple hints?
- If not, delete RAG and save the complexity
- If yes, investigate whether the cost is worth it

### Alternative Design Philosophies

#### Philosophy 1: "Coach is Passive, Let Salesperson Learn by Doing"

**Idea**: Remove all real-time coaching. Let salesperson roleplay without interruptions. At the end, show a transcript with annotations (where they did well, where they missed opportunities).

**Pros**:
- Fewer agents to maintain
- No hint throttling problems
- Salesperson learns to self-regulate, not rely on external feedback
- Simpler architecture (Gemini for roleplay, that's it)

**Cons**:
- Less immediate feedback = slower learning
- No guidance during the session for struggling users

#### Philosophy 2: "Coach is Predictive, Not Reactive"

**Idea**: Before each turn, the coach previews what might happen ("The customer seems price-sensitive. You should address financing."). Salesperson then speaks and proves whether they used the advice.

**Pros**:
- Hints come exactly when needed
- Salesperson can prepare, not just react
- More like real coaching (coach sets up expectations first)

**Cons**:
- Requires dual Gemini calls (one to predict, one to roleplay)
- Slower conversation flow
- May over-constrain the roleplay

#### Philosophy 3: "Score by Outcome, Not Technique"

**Idea**: Abandon C.O.R.E. scoring. Instead: Did the salesperson close the deal? Yes/No. If no, why not? (Customer said no, customer got confused, salesperson gave up, etc.)

**Pros**:
- Objectively measurable
- Teaches real sales skill (closing, not technique memorization)
- Simpler evaluation (no stage weighting debates)

**Cons**:
- Removes learning scaffolding (C.O.R.E. is a structured path)
- May demoralize users who are "good at technique but can't close"
- Loses granular feedback

#### Philosophy 4: "Build for Different Personas"

**Idea**: Not all salespeople need the same training. A junior rep needs scaffolding and techniques. An experienced rep needs to practice edge cases. A closer needs objection handling. Design different flows:

- **Novice mode**: Structured guidance, break down each stage, lots of hints
- **Advanced mode**: Minimal coaching, focus on close rate
- **Specialist mode**: Industry-specific scenarios (real estate pricing, SaaS contract negotiation, etc.)

**Pros**:
- Targets actual learning needs
- May improve engagement (people see themselves in the flow)
- Allows A/B testing ("does novice mode help new reps?")

**Cons**:
- More development complexity
- Requires understanding learner skill levels (pre-test needed)

### Questions to Answer Before Major Refactors

1. **Do salespeople actually improve from practicing with this system?** (Measure: pre/post real-world sales metrics)
2. **Which feature drives improvement?** (A/B test: Gemini roleplay alone vs. + coaching vs. + scoring)
3. **Is C.O.R.E. framework teaching working, or is it just noise?** (Measure: do users apply techniques in real calls?)
4. **What do users hate most about the experience?** (User research: exit surveys, session abandonment analysis)
5. **Is RAG worth the complexity?** (Compare: generic hints vs. RAG-enriched hints on user performance)
6. **How do we measure a "good" sales call?** (Talk to sales managers: what would they coach for?)

### Recommended Actions

**Short term** (next sprint):
- Add telemetry: when do users abandon? When do they find hints helpful?
- Run a survey: "What part of training felt most valuable?"
- Simplify the code by either removing LangGraph OR removing direct Gemini roleplay (pick one)

**Medium term** (next quarter):
- A/B test: Coach-enabled vs. coach-disabled on new users
- Measure: Do coached users outperform uncoached users in real sales?
- If not, pivot to outcome-based scoring (Philosophy 3)

**Long term** (next year):
- Redesign for learner personas (Philosophy 4)
- Integrate with real CRM data (what deals did users close after training?)
- Consider whether an LLM coaching system is even the right approach, or if human coaches are better
