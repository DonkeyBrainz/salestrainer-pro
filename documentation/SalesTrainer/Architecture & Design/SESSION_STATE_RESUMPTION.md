---
tags: [#architecture, #sessions, #persistence]
---

# Session State & Resumption Guide

## Overview

The backend uses a **hybrid approach**: in-memory state during active sessions, with selective persistence to Firestore. Session resumption is partially implemented but currently unused.

---

## State Storage: Memory vs. Database

### In-Memory State (During Active Session)

**LangGraph MemorySaver** (`customer_agent.py:50`):
- Uses LangGraph's built-in `MemorySaver()` for checkpointing
- Thread ID = session_id (unique identifier)
- Stores execution state of the agent graph
- Lost on application restart
- Fast access during conversation

**WebSocket Relay Instance** (`gemini_relay.py:58-67`):
```python
_agent_state: CustomerAgentState          # Current agent state
_message_buffer: list[TranscriptMessage]  # Messages for transcript
_resumption_handle: str | None            # Gemini session resumption
_should_reconnect: bool                   # Reconnection flag
```
- Lives in the `GeminiWebSocketRelay` class instance
- Scoped to single WebSocket connection
- Destroyed when client disconnects

### Persistent Storage (Firestore)

Saved at session end via `_persist_conversation()`:

**Session Document** (`sessions/{sessionId}`):
```
{
  "id": "session-123",
  "selected_persona": "persona-id",
  "status": "COMPLETED",
  "duration_seconds": 300,
  "message_count": 10,
  "agent_state_snapshot": "{...JSON...}",  # Serialized state
  "created_at": timestamp,
  "ended_at": timestamp,
  ...
}
```

**Transcript Document** (`transcripts/{transcriptId}`):
```
{
  "id": "transcript-123",
  "session_id": "session-123",
  "messages": [
    {
      "role": "user",
      "text": "I need a new couch",
      "timestamp": timestamp,
      "internal_reasoning": null
    },
    {
      "role": "assistant",
      "text": "Tell me more...",
      "timestamp": timestamp,
      "internal_reasoning": "..."
    },
    ...
  ],
  "total_words": 250,
  "duration_seconds": 300
}
```

**Evaluation Document** (`evaluations/{evaluationId}`):
```
{
  "session_id": "session-123",
  "score": 82,
  "grade": "B",
  "stage_scores": {...},
  "pbm_metrics": {...},
  "strengths": [...],
  "improvements": [...]
}
```

---

## What State is Persisted?

### Serialized to Firestore (`serialize_state()` method)

These fields are saved to `agent_state_snapshot`:

```
✓ turn_count: int
✓ mood: Mood (enum: NEUTRAL, INTERESTED, ENGAGED, SKEPTICAL)
✓ regard_level: RegardLevel (enum: NO, LOW, MEDIUM, HIGH)
✓ objections_available: list[str]        # PBMs customer COULD raise
✓ objections_raised: list[str]           # PBMs customer DID raise
✓ objections_resolved: list[str]         # PBMs customer RESOLVED
✓ stage_progress: CoreStageProgress      # Checklist completion per stage
✓ session_id: str
✓ user_id: str
```

**Example Snapshot JSON**:
```json
{
  "turn_count": 5,
  "mood": "interested",
  "regard_level": "high",
  "objections_available": ["price", "delivery"],
  "objections_raised": ["price"],
  "objections_resolved": [],
  "stage_progress": {
    "current_stage": "ASK",
    "engage": {"build_rapport": true, "discover_need": true},
    "ask": {"ask_need": true},
    "show": {},
    "yes": {},
    "pbms_expressed": ["price"],
    "pbms_acknowledged": ["price"]
  },
  "session_id": "session-123",
  "user_id": "user-456"
}
```

### NOT Persisted (Kept In-Memory or Excluded)

```
✗ messages: list[BaseMessage]              # Stored separately in transcript
✗ persona: CustomerPersona                 # Reloaded from registry
✗ LangGraph execution checkpoints          # Lost on restart
✗ _analysis: dict                          # Runtime intermediate state
✗ _injected_objection: str                 # Runtime intermediate state
✗ Gemini resumption handle                 # Not persisted (fresh on restart)
```

### Transcript (Separate from State)

Message history is stored separately in `transcripts` collection:
- Complete message history with role, text, timestamp
- Internal reasoning from Gemini (for learning)
- Reconstructable into `messages: list[BaseMessage]` on resume

---

## How Session Resumption Works

### Gemini Reconnection (Transparent)

**What**: Backend handles Gemini Live API disconnects transparently

**Flow** (`gemini_relay.py`):

1. **Resumption Handle** (lines 481-488):
   ```python
   if resp_type == "session_resumption_update":
       self._resumption_handle = response.get("new_handle")
       # Store handle for reconnection
   ```

2. **GoAway Detection** (lines 491-499):
   ```python
   if resp_type == "go_away":
       self._should_reconnect = True
       # Gemini says we need to reconnect
   ```

3. **Reconnection Retry** (lines 266-343):
   ```python
   while retry_count < 3:
       live_session = self.gemini_service.connect_live(
           resumption_handle=self._resumption_handle
       )
       # Reconnect with stored handle

       if successful:
           self._should_reconnect = False
           client_ws.send_json({"type": "session_resumed"})
           break
   ```

**Result**: Client doesn't know Gemini disconnected. Connection stays alive.

### User Session Resumption (Defined but Unused)

**What**: Feature to resume a paused/interrupted training session

**Implementation** (`customer_agent_service.py:232-290`):

```python
def resume_session(
    session: Session,
    transcript: Transcript | None = None
) -> CustomerAgentState:
    # 1. Load persona from registry
    persona = get_persona(session.selected_persona)

    # 2. Reconstruct messages from transcript
    messages = []
    if transcript:
        for msg in transcript.messages:
            if msg.role == MessageRole.USER:
                messages.append(HumanMessage(content=msg.text))
            else:
                messages.append(AIMessage(content=msg.text))

    # 3. Deserialize state snapshot
    state = deserialize_state(
        snapshot_json=session.agent_state_snapshot,
        persona=persona,
        messages=messages
    )

    # 4. Return ready-to-use state
    return state
```

**Steps to Resume**:

1. **Fetch Session** from Firestore:
   ```python
   session = session_repository.get_by_id(session_id)
   ```

2. **Fetch Transcript**:
   ```python
   transcript = transcript_repository.get_by_session_id(session_id)
   ```

3. **Rebuild Messages**:
   ```python
   messages = [
       HumanMessage(msg.text) for msg in transcript if msg.role == "user",
       AIMessage(msg.text) for msg in transcript if msg.role == "assistant"
   ]
   ```

4. **Deserialize State Snapshot**:
   ```python
   state_dict = json.loads(session.agent_state_snapshot)
   mood = Mood(state_dict["mood"])
   regard = RegardLevel(state_dict["regard_level"])
   stage = CoreStageProgress.model_validate(state_dict["stage_progress"])
   ```

5. **Merge Into Complete State**:
   ```python
   customer_state = {
       "messages": messages,
       "turn_count": len([m for m in messages if isinstance(m, HumanMessage)]),
       "persona": persona,
       "mood": mood,
       "regard_level": regard,
       "objections_available": state_dict["objections_available"],
       "objections_raised": state_dict["objections_raised"],
       "objections_resolved": state_dict["objections_resolved"],
       "stage_progress": stage,
       "session_id": session_id,
       "user_id": user_id
   }
   ```

6. **Ready for Graph Invocation**:
   ```python
   # New WebSocket connection can now call:
   result = customer_agent_graph.invoke(
       {"messages": [...], "mood": "interested", ...},
       config={"configurable": {"thread_id": session_id}}
   )
   ```

**Current Status**: ✗ No API endpoint calls this function. To enable, would need:
- New endpoint: `POST /api/v1/sessions/{sessionId}/resume`
- Validate user owns session
- Call `resume_session()` to rebuild state
- Open new WebSocket with restored state

---

## Serialization & Deserialization

### Serialize to JSON (`serialize_state()`)

```python
def serialize_state(state: CustomerAgentState) -> str:
    data = {
        "turn_count": state["turn_count"],
        "mood": state["mood"].value,              # Enum → string
        "regard_level": state["regard_level"].value,
        "objections_available": state["objections_available"],
        "objections_raised": state["objections_raised"],
        "objections_resolved": state["objections_resolved"],
        "stage_progress": state["stage_progress"].model_dump(),  # Model → dict
        "session_id": state["session_id"],
        "user_id": state["user_id"],
    }
    return json.dumps(data)
```

**Result**: All data → JSON string, safe for Firestore storage

### Deserialize from JSON (`deserialize_state()`)

```python
def deserialize_state(
    snapshot_json: str,
    persona: CustomerPersona,
    messages: list[BaseMessage]
) -> CustomerAgentState:
    data = json.loads(snapshot_json)

    return {
        "turn_count": data["turn_count"],
        "mood": Mood(data["mood"]),               # String → Enum
        "regard_level": RegardLevel(data["regard_level"]),
        "objections_available": data["objections_available"],
        "objections_raised": data["objections_raised"],
        "objections_resolved": data["objections_resolved"],
        "stage_progress": CoreStageProgress.model_validate(data["stage_progress"]),
        "session_id": data["session_id"],
        "user_id": data["user_id"],
        "persona": persona,
        "messages": messages,
    }
```

**Result**: JSON → Typed Python objects, ready for graph invocation

### LangGraph Checkpoint Serialization

**Important**: LangGraph's internal checkpoint state (graph execution state) is **NOT** serialized.

- Only the extracted `CustomerAgentState` dict is saved
- If resuming, the graph needs to rebuild execution state from messages
- This is acceptable because messages contain all conversational context

---

## Interruption Handling

### Current Behavior

1. **Client Disconnects** (any reason):
   - WebSocket `close()` event triggers

2. **Session Cleanup** (`finally` block in relay):
   ```python
   finally:
       # Even if interrupted, persist the conversation
       await self._persist_conversation()
   ```

3. **Persistence Happens**:
   - Session marked as `COMPLETED` (regardless of why it ended)
   - Messages saved to transcript
   - Agent state snapshot saved
   - Evaluation generated

4. **Result**:
   - Data is safe
   - Session treated as "finished"
   - No way to resume unless `resume_session()` endpoint is added

### What's Missing

- No `PAUSED` or `ABANDONED` status (only `IN_PROGRESS` and `COMPLETED`)
- No resume endpoint to restart from checkpoint
- No client-side signal that session is resumable
- All sessions treated as one-shot

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│              Session Lifecycle                          │
└─────────────────────────────────────────────────────────┘

START:
  ┌────────────────┐
  │ User connects  │
  │ WebSocket      │
  └────────┬───────┘
           │
           ▼
  ┌────────────────────────┐
  │ Create session         │
  │ in Firestore           │
  │ status = IN_PROGRESS   │
  └────────┬───────────────┘
           │
           ▼
  ┌─────────────────────────────────────────┐
  │  GeminiWebSocketRelay Instance          │
  │  ├─ _agent_state (in-memory)            │
  │  ├─ _message_buffer (in-memory)         │
  │  └─ _resumption_handle (in-memory)      │
  └────────┬────────────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────────────┐
  │  LangGraph Agent                        │
  │  ├─ MemorySaver (in-memory checkpoints) │
  │  └─ thread_id = session_id              │
  └────────┬────────────────────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
 Audio In   Coaching Analysis (async)
    │             │
    ▼             ▼
 State Update   Suggestions
    │             │
    └──────┬──────┘
           │
        [Active Session Continues]
           │
           ▼
  ┌─────────────────────┐
  │ Client disconnects  │
  │ or says "end"       │
  └────────┬────────────┘
           │
           ▼
  ┌──────────────────────────────────────────┐
  │ _persist_conversation() [finally block]  │
  └────────┬─────────────────────────────────┘
           │
           ├─→ Serialize _agent_state
           │   (mood, regard, objections, stage_progress)
           │
           ├─→ Save session document
           │   + agent_state_snapshot (JSON)
           │
           ├─→ Save transcript document
           │   + full message history
           │
           └─→ Generate & save evaluation
               (score, grade, strengths, improvements)
           │
           ▼
  ┌──────────────────────────────────────────┐
  │ Firestore Collections Updated:           │
  │ ├─ sessions/{sessionId}                  │
  │ ├─ transcripts/{transcriptId}            │
  │ └─ evaluations/{evaluationId}            │
  └──────────────────────────────────────────┘

[OPTIONAL] SESSION RESUMPTION (NOT CURRENTLY IMPLEMENTED):
           │
           ▼
  ┌──────────────────────────────────────────┐
  │ User clicks "Resume Session" (new UI)    │
  └────────┬─────────────────────────────────┘
           │
           ▼
  ┌──────────────────────────────────────────┐
  │ POST /api/v1/sessions/{sessionId}/resume │
  └────────┬─────────────────────────────────┘
           │
           ├─→ Fetch session from Firestore
           │
           ├─→ Fetch transcript from Firestore
           │
           ├─→ Load persona from registry
           │
           ├─→ Reconstruct messages from transcript
           │
           ├─→ Deserialize agent_state_snapshot
           │
           └─→ Return state for new WebSocket connection
           │
           ▼
  ┌──────────────────────────────────────────┐
  │ New WebSocket connects with restored     │
  │ state, continues conversation            │
  └──────────────────────────────────────────┘
```

---

## Summary Table

| Aspect | Status | Details |
|--------|--------|---------|
| **In-Memory State** | ✓ Active | LangGraph MemorySaver + WebSocket relay vars |
| **Firestore Persistence** | ✓ Active | Session, transcript, evaluation documents |
| **State Serialization** | ✓ Implemented | JSON serialization of key fields |
| **Gemini Reconnection** | ✓ Transparent | Handles disconnects, restores Gemini session |
| **User Session Resume** | ✗ Missing | Code exists but no endpoint integration |
| **Interruption Handling** | ✓ Safe | Data always saved, never lost |
| **Message History** | ✓ Complete | Stored in transcript with metadata |
| **Persona Reload** | ✓ Works | Loaded from registry on resume |
| **LangGraph State Recovery** | ✗ Partial | Data restored but graph rebuilt from messages |

---

## Files Reference

- `backend/app/agents/customer_agent.py` - LangGraph agent with MemorySaver
- `backend/app/services/customer_agent_service.py` - Serialization, deserialization, resume logic
- `backend/app/services/session_service.py` - Session lifecycle management
- `backend/app/api/ws/gemini_relay.py` - WebSocket relay with persistence
- `backend/app/repositories/session_repository.py` - Session CRUD
- `backend/app/repositories/transcript_repository.py` - Transcript CRUD
- `backend/app/repositories/evaluation_repository.py` - Evaluation storage
