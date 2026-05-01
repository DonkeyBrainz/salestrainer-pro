---
tags: [#api, #planning, #future]
---

# Future API Endpoints

This document outlines planned API endpoints for future phases of Luxe Sales Coach v2. These endpoints were initially designed but are not yet implemented. They are included here as reference for future development phases.

---

## Sessions Management (Phase 5)

Currently, sessions are managed entirely via WebSocket connections. Future phases may add HTTP endpoints for session lifecycle management.

### POST /api/v1/sessions

Create a new training or evaluation session.

**Request:**
```json
{
  "mode": "training",
  "persona": "executive",
  "difficulty": "intermediate"
}
```

**Response:** `201 Created`
```json
{
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "userId": "550e8400-e29b-41d4-a716-446655440001",
  "mode": "training",
  "persona": "executive",
  "difficulty": "intermediate",
  "status": "created",
  "startedAt": "2026-02-05T12:00:00Z",
  "createdAt": "2026-02-05T12:00:00Z"
}
```

**Rationale:** Allow frontend to track session state across disconnects and reconnections.

---

### GET /api/v1/sessions

List all sessions for the current user with pagination.

**Query Parameters:**
- `limit` (optional, default: 20) - Number of sessions per page
- `cursor` (optional) - Pagination cursor
- `mode` (optional) - Filter by mode (training, evaluation)
- `status` (optional) - Filter by status (created, in_progress, completed)

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "sessionId": "550e8400-e29b-41d4-a716-446655440000",
      "mode": "training",
      "persona": "executive",
      "difficulty": "intermediate",
      "status": "completed",
      "startedAt": "2026-02-05T12:00:00Z",
      "endedAt": "2026-02-05T12:45:00Z",
      "duration": 2700,
      "grade": "A-",
      "score": 88
    }
  ],
  "cursor": "next-page-cursor",
  "hasMore": false
}
```

**Rationale:** Enable session history view and analytics dashboard on frontend.

---

### GET /api/v1/sessions/{sessionId}

Retrieve details of a specific session including transcript and evaluation.

**Response:** `200 OK`
```json
{
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "userId": "550e8400-e29b-41d4-a716-446655440001",
  "mode": "training",
  "persona": "executive",
  "difficulty": "intermediate",
  "status": "completed",
  "startedAt": "2026-02-05T12:00:00Z",
  "endedAt": "2026-02-05T12:45:00Z",
  "duration": 2700,
  "transcript": [
    {
      "role": "user",
      "text": "Hi, I'd like to discuss our furniture collections",
      "timestamp": "2026-02-05T12:00:05Z"
    },
    {
      "role": "assistant",
      "text": "Great! I'm interested in learning more about your needs.",
      "timestamp": "2026-02-05T12:00:10Z"
    }
  ],
  "evaluation": {
    "grade": "A-",
    "score": 88,
    "easyChecklist": {
      "engagement": true,
      "ask": true,
      "satisfaction": true,
      "yes": false
    },
    "feedback": "Strong engagement and questioning, but didn't close the sale",
    "coachingNotes": [...]
  }
}
```

**Rationale:** Enable detailed session review and post-session analysis.

---

### PUT /api/v1/sessions/{sessionId}

Update session metadata (e.g., mark as favorite, add notes).

**Request:**
```json
{
  "notes": "Practiced handling Executive objections well",
  "isFavorited": true
}
```

**Response:** `200 OK` (same as GET)

**Rationale:** Allow users to annotate and organize sessions.

---

### DELETE /api/v1/sessions/{sessionId}

Delete a session and associated data.

**Response:** `204 No Content`

**Rationale:** Enable session cleanup and privacy compliance.

---

## Evaluations & Analytics (Phase 5)

Post-session evaluation results and user performance analytics.

### POST /api/v1/sessions/{sessionId}/evaluations

Generate evaluation report for a completed session.

**Request:**
```json
{
  "includeRecommendations": true
}
```

**Response:** `201 Created`
```json
{
  "evaluationId": "550e8400-e29b-41d4-a716-446655440000",
  "sessionId": "550e8400-e29b-41d4-a716-446655440001",
  "grade": "A-",
  "score": 88,
  "easyChecklist": {
    "engagement": {
      "passed": true,
      "feedback": "Good engagement and rapport building"
    },
    "ask": {
      "passed": true,
      "feedback": "Asked multiple qualifying questions"
    },
    "satisfaction": {
      "passed": true,
      "feedback": "Addressed customer concerns effectively"
    },
    "yes": {
      "passed": false,
      "feedback": "Didn't secure commitment or next steps"
    }
  },
  "recommendations": [
    "Practice closing techniques",
    "Use assumptive closes more often",
    "Summarize benefits before asking for commitment"
  ],
  "createdAt": "2026-02-05T12:45:00Z"
}
```

**Rationale:** Enable evaluation generation as a REST operation for flexibility.

---

### GET /api/v1/sessions/{sessionId}/evaluations

Retrieve all evaluations for a session.

**Response:** `200 OK`
```json
{
  "evaluations": [
    {
      "evaluationId": "550e8400-e29b-41d4-a716-446655440000",
      "grade": "A-",
      "score": 88,
      "createdAt": "2026-02-05T12:45:00Z"
    }
  ]
}
```

**Rationale:** Allow retrieval of historical evaluations for progress tracking.

---

### GET /api/v1/users/me/stats

Get aggregated performance statistics for the current user.

**Response:** `200 OK`
```json
{
  "userId": "550e8400-e29b-41d4-a716-446655440000",
  "totalSessions": 42,
  "completedSessions": 38,
  "averageScore": 82.5,
  "gradeDistribution": {
    "A": 8,
    "B": 15,
    "C": 12,
    "D": 3,
    "F": 0
  },
  "easyMastery": {
    "engagement": 95,
    "ask": 88,
    "satisfaction": 92,
    "yes": 71
  },
  "personaPerformance": {
    "assistant": {
      "attempts": 15,
      "averageScore": 85
    },
    "executive": {
      "attempts": 14,
      "averageScore": 78
    },
    "skeptic": {
      "attempts": 13,
      "averageScore": 83
    }
  },
  "progressTrend": [
    {
      "week": "2026-01-29",
      "averageScore": 78
    },
    {
      "week": "2026-02-05",
      "averageScore": 82
    }
  ],
  "lastSessionAt": "2026-02-05T12:45:00Z"
}
```

**Rationale:** Enable dashboard with user progress analytics and insights.

---

## Knowledge Base (Phase 5)

Expose E.A.S.Y. system content and training materials via API.

### GET /api/v1/knowledge/easy-system

Retrieve complete E.A.S.Y. selling system content.

**Response:** `200 OK`
```json
{
  "title": "E.A.S.Y. Selling System",
  "description": "A consultative selling approach for furniture retail",
  "phases": [
    {
      "phase": "Engagement",
      "description": "Build rapport and establish trust",
      "techniques": [
        "Active listening",
        "Empathetic response",
        "Personalized greeting"
      ],
      "examples": [...]
    },
    {
      "phase": "Ask",
      "description": "Uncover customer needs",
      "techniques": [
        "Open-ended questions",
        "Needs analysis",
        "Active listening"
      ],
      "examples": [...]
    },
    {
      "phase": "Satisfaction",
      "description": "Present solutions",
      "techniques": [
        "Feature-benefit mapping",
        "Product knowledge",
        "Customer-centric messaging"
      ],
      "examples": [...]
    },
    {
      "phase": "Yes",
      "description": "Secure commitment",
      "techniques": [
        "Assumptive close",
        "Trial close",
        "Urgency creation"
      ],
      "examples": [...]
    }
  ]
}
```

**Rationale:** Enable learning materials to be viewed outside of roleplay sessions.

---

### GET /api/v1/knowledge/objections

Retrieve common objections and handling strategies.

**Response:** `200 OK`
```json
{
  "objections": [
    {
      "id": "price",
      "title": "Price Objection",
      "description": "Customer balks at price",
      "handling": [
        "Acknowledge the concern",
        "Focus on value over price",
        "Offer financing options",
        "Compare to competitors"
      ]
    },
    {
      "id": "timing",
      "title": "Timing Objection",
      "description": "Not the right time to buy",
      "handling": [
        "Create urgency",
        "Highlight limited inventory",
        "Offer incentives for immediate action"
      ]
    }
  ]
}
```

**Rationale:** Make training content accessible for self-study and reference.

---

## User Preferences & Settings (Phase 6)

Manage user preferences and account settings.

### PATCH /api/v1/users/me

Update user profile and preferences.

**Request:**
```json
{
  "name": "John Doe",
  "preferences": {
    "voiceName": "Zephyr",
    "difficulty": "advanced",
    "theme": "dark",
    "notifications": true
  }
}
```

**Response:** `200 OK`
```json
{
  "userId": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "name": "John Doe",
  "preferences": {
    "voiceName": "Zephyr",
    "difficulty": "advanced",
    "theme": "dark",
    "notifications": true
  },
  "updatedAt": "2026-02-05T12:00:00Z"
}
```

**Rationale:** Allow users to customize their training experience.

---

## Implementation Priority

| Phase | Endpoints | Rationale |
|-------|-----------|-----------|
| **Phase 5** | Sessions CRUD, Evaluations, Stats, Knowledge Base | Core functionality for session history and analytics |
| **Phase 6** | User preferences/settings | User customization and account management |
| **Future** | Advanced analytics, integrations, team/admin endpoints | Enterprise features |

---

## Notes

- All future endpoints should maintain the same error handling and response format as current API
- Rate limiting should be applied consistently
- WebSocket will continue to handle real-time audio; REST endpoints are for metadata and analytics
- Session state management via HTTP would allow for better frontend state persistence across browser refreshes

---

**Last Updated:** February 5, 2026
**Status:** Planned - Not Yet Implemented
