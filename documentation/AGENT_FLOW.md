# Backend Agent Flow: Step-by-Step Guide

## Overview
When a user speaks during a training session, the backend orchestrates a complex flow involving real-time audio streaming, AI coaching analysis, state tracking, and mood/scoring updates. Below is a detailed walkthrough of what happens across 2 conversation turns.

---

## Turn 1: User Speaks First Time

### Step 1.1: Audio Input Received
- **Client sends**: PCM audio (16kHz mono) via WebSocket binary frame
- **Backend receives** in `GeminiWebSocketRelay._relay_client_to_gemini()`
- **Buffering**: Audio buffered locally for later persistence
- **Forward to Gemini**: Sent to Gemini Live API via `live_session.send_audio()`

### Step 1.2: Gemini Processes & Responds
- Gemini receives audio, transcribes user speech, generates customer persona response
- Streams back multiple message types:
  - `input_transcription`: "I need a new couch" (user speech)
  - `output_transcription`: "Tell me more..." (customer response, streamed word-by-word)
  - `internal_reasoning`: Model's thinking (not shown to user)
  - `audio`: Binary audio of customer response

### Step 1.3: Relay Back to Client
- Backend in `_relay_gemini_to_client()` streams:
  - Transcriptions → HUD for real-time display
  - Audio → Speaker for roleplay immersion
- **Buffering**: User/assistant transcriptions stored in `_pending_user_transcription` and `_pending_assistant_transcription`
- **Internal reasoning**: Stored separately in `_pending_reasoning`

### Step 1.4: Turn Completes (Signal: `end` message)
- Gemini signals turn is complete
- Pending buffers flushed:
  - Create `TranscriptMessage` with UUID, role, text, timestamp
  - Add to `_message_buffer` for end-of-session persistence

### Step 1.5: Customer Agent State Updated
- **Service**: `CustomerAgentService.process_message()`
- **Action**: Invokes `CustomerAgentGraph` (LangGraph) with user message
- **State changes**:
  - `mood`: Updated based on customer's perceived sentiment (e.g., INTERESTED → SKEPTICAL if objection raised)
  - `regard_level`: Adjusted based on customer's receptiveness
  - `objections_available`: List of PBMs customer *could* raise (pre-defined)
  - `objections_raised`: Customer actually stated an objection?
  - `stage_progress`: No updates yet (coach determines this)
  - `turn_count`: Incremented to 1
  - `messages`: User message added to LangChain message history

### Step 1.6: Coach Analysis (Async, Non-Blocking)
- **Service**: `CoachAgentService.analyze_turn()` runs in background
- **Input**: User message + current customer state
- **Analysis via Gemini 2.0 Flash**:
  - Detects E.A.S.Y. techniques used (ENGAGE, ASK, SHOW, YES checklist items)
  - Scores confidence (0-1)
  - Assigns intervention level (NONE, INFO, SUGGESTION, WARNING, CRITICAL)
- **Updates**:
  - `stage_progress`: Marks completed checklist items
  - `pbms_acknowledged`: Were PBMs recognized by salesperson?
  - Example: If user said "I see you mentioned price concerns," system marks PBM as acknowledged
- **Coaching hint**: If training mode and `intervention_level > NONE`, sends hint back to client (e.g., "Consider acknowledging the objection directly")

### Step 1.7: No Mood/Score Update Yet
- Mood updated in Step 1.5 based on customer response
- **Coaching score**: Only calculated at session end (not turn-by-turn)

---

## Turn 2: Salesperson Responds

### Step 2.1: User Speaks Again
- **Client sends**: Another audio message (salesperson's response)
- Same flow as Turn 1.1-1.2:
  - Transcribed: "Your concern about price is valid. We offer financing..."
  - Customer responds: "Interesting, tell me about that..."

### Step 2.2: Turn Completes & State Updates
- Turn ends → Buffers flushed
- **CustomerAgentState updated**:
  - `mood`: May shift (e.g., SKEPTICAL → INTERESTED if salesperson addressed objection well)
  - `regard_level`: Might improve
  - `objections_raised` / `objections_resolved`: Tracks whether financing objection is now "resolved"
  - `turn_count`: Incremented to 2
  - `messages`: Salesperson + customer messages added to history

### Step 2.3: Coach Analysis Round 2
- Analyzes the salesperson's response (financing explanation)
- Detects techniques:
  - Did they use SHOW stage (demonstrate value)?
  - Did they directly address the objection?
  - Technique score + confidence
- **Stage progress updates**:
  - Marks "Address Objection" as complete in ASK stage
  - Suggests transition to SHOW stage
- **PBM tracking**:
  - Acknowledges: "Price concern" → marked as `pbms_acknowledged`
  - Resolved: If financed option accepted → mark as `pbms_resolved`

### Step 2.4: Session Continues or Ends
- If user says "That works for me," session may end
- Otherwise, flow repeats for Turn 3, 4, etc.

---

## End of Session: Persistence & Scoring

### Step 3.1: Session Termination
- User disconnects or says "end"
- **Service**: `_persist_conversation()` triggered

### Step 3.2: Save Raw Data
- **Session**: `SessionRepository.create()` stores:
  - Status: COMPLETED
  - Duration: Calculated from timestamps
  - Message count: From `_message_buffer`
  - Final agent state snapshot (serialized JSON)
- **Transcript**: `TranscriptRepository.create()` stores:
  - All messages from `_message_buffer`
  - Internal reasoning for each assistant message
  - Total words + duration

### Step 3.3: Final Coach Evaluation
- **Service**: `CoachAgentService.generate_evaluation()`
- **Scoring**: `calculate_score()` computes:

  ```
  Base Score = (Stage Completion %) × 100
    - ENGAGE: 25% weight
    - ASK: 25% weight
    - SHOW: 25% weight
    - YES: 25% weight

  Bonuses:
    + PBM Handling: Acknowledged + resolved
    + Objection Recovery: Handled > 80%

  Penalties:
    - Missed Techniques: Didn't use key E.A.S.Y. steps
    - Deviations: Off-topic or irrelevant comments

  Grade: A (90+), B (80-89), C (70-79), D (60-69), F (<60)
  ```

### Step 3.4: Save Evaluation
- **Evaluation Repository** stores:
  - Stage scores (ENGAGE, ASK, SHOW, YES)
  - PBM metrics: expressed, acknowledged, resolved, match rate
  - Objection metrics: raised, resolved, recovery rate
  - Final score & grade
  - Strengths & improvements (text summary)
- **Mood history**: Not explicitly saved, but tracked in transcript
- **Coaching feedback**: Stored in evaluation summary

---

## Key State Changes Across 2 Turns

| Component | Turn 1 | Turn 2 | End of Session |
|-----------|--------|--------|----------------|
| **Mood** | NEUTRAL → INTERESTED | INTERESTED → ENGAGED | Frozen in evaluation |
| **Regard Level** | LOW → MEDIUM | MEDIUM → HIGH | Frozen in evaluation |
| **Stage Progress** | ENGAGE started | ENGAGE complete, ASK started | Final breakdown by stage |
| **Objections** | None raised yet | "Price concern" raised | "Price concern" resolved |
| **Turn Count** | 1 | 2 | Included in transcript |
| **Coaching Score** | Not calculated | Not calculated | A/B/C/D/F assigned |
| **Transcript** | Turn 1 messages | Turn 1+2 messages | All saved to Firestore |

---

## Architecture Highlights

### Real-Time vs. Post-Session

| When | What | Service |
|------|------|---------|
| **During (Each Turn)** | Mood, objections, stage hints | `CustomerAgentService`, `CoachAgentService` |
| **During (Non-blocking)** | Coaching suggestions | `CoachAgentService.analyze_turn()` async |
| **End of Session** | Final score, grade, summary | `CoachAgentService.generate_evaluation()` |

### Data Flow

```
Audio Input (Turn 1)
  ↓
Gemini Live API (stream responses)
  ↓
Relay to Client (HUD + audio)
  ↓
Customer Agent State (mood, objections, stage)
  ↓
Coach Analysis (techniques, interventions)
  ↓
Repeat for Turn 2
  ↓
Session End: Persist all → Evaluate → Grade
```

### Error Handling

- Coach analysis failures don't crash the session
- WebSocket reconnects transparently up to 3 times
- All messages logged even if persistence fails

---

## Summary

1. **User speaks** → Audio sent to Gemini, transcribed, customer responds
2. **Turn ends** → State updated (mood, objections, stage progress)
3. **Coach analyzes** → Detects techniques, marks stage items, sends hints (async)
4. **Repeat** → Each turn increments counter, updates state, triggers analysis
5. **Session ends** → All data persisted, final score calculated, grade assigned

The system balances **real-time responsiveness** (streaming HUD updates, instant feedback) with **comprehensive tracking** (transcript, reasoning, scoring) for post-session review and improvement.
