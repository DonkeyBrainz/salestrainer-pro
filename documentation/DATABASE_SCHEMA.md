# Database Schema: Luxe Sales Coach v2

> **Version:** 1.0.0
> **Last Updated:** 2026-02-05
> **Status:** Current
> **Database:** Firestore (current) / PostgreSQL (future migration)

---

## Overview

This document defines the complete database schema for the Luxe Sales Coach v2 backend. The POC uses Firestore for rapid development; production will migrate to PostgreSQL.

### Design Principles

- **Soft Deletes:** All entities use `isDeleted` flag for audit trail
- **Timestamps:** All entities track `createdAt` and `updatedAt`
- **UUIDs:** All primary keys use UUID v4 format
- **Denormalization:** Strategic denormalization for read performance in Firestore

---

## Table of Contents

1. [Entity Relationship Diagram](#entity-relationship-diagram)
2. [Collections/Tables](#collectionstables)
3. [Indexes](#indexes)
4. [Relationships](#relationships)
5. [Migration Strategy](#migration-strategy)

---

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     users       │       │    sessions     │       │   evaluations   │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ userId (PK)     │──────<│ userId (FK)     │       │ evaluationId(PK)│
│ email           │       │ sessionId (PK)  │>──────│ sessionId (FK)  │
│ name            │       │ sessionType     │       │ userId (FK)     │
│ googleId        │       │ status          │       │ grade           │
│ preferences     │       │ selectedPersona │       │ score           │
│ createdAt       │       │ startedAt       │       │ scorecard       │
│ updatedAt       │       │ endedAt         │       │ feedback        │
└─────────────────┘       │ grade           │       │ createdAt       │
        │                 │ createdAt       │       └─────────────────┘
        │                 └─────────────────┘
        │                         │
        │                         │
        │                 ┌───────┴───────┐
        │                 │               │
        │         ┌───────┴─────┐ ┌───────┴───────┐
        │         │ transcripts │ │   messages    │
        │         ├─────────────┤ ├───────────────┤
        │         │transcriptId │ │ messageId(PK) │
        │         │sessionId(FK)│ │transcriptId(FK)│
        │         │ totalMsgs   │ │ role          │
        │         │ createdAt   │ │ text          │
        │         └─────────────┘ │ timestamp     │
        │                         └───────────────┘
        │
┌───────┴─────────┐
│ refresh_tokens  │
├─────────────────┤
│ tokenId (PK)    │
│ userId (FK)     │
│ tokenHash       │
│ expiresAt       │
│ isRevoked       │
└─────────────────┘
```

---

## Collections/Tables

### 1. users

Stores user accounts and preferences.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| userId | string (UUID) | PRIMARY KEY | Unique user identifier |
| email | string | UNIQUE, NOT NULL, INDEX | User email address |
| name | string | NOT NULL | Display name from Google |
| googleId | string | UNIQUE, INDEX | Google OAuth subject ID |
| avatarUrl | string | NULLABLE | Profile picture URL |
| createdAt | timestamp | NOT NULL, INDEX | Account creation time |
| updatedAt | timestamp | NOT NULL | Last update time |
| lastLoginAt | timestamp | NULLABLE | Last successful login |
| preferences | object | NOT NULL | User settings (see below) |
| isActive | boolean | DEFAULT true | Account active status |
| isDeleted | boolean | DEFAULT false | Soft delete flag |
| deletedAt | timestamp | NULLABLE | Deletion timestamp |

**preferences object:**
```json
{
  "voiceName": "Zephyr",
  "difficulty": "intermediate",
  "theme": "light",
  "notificationsEnabled": true
}
```

| Field | Type | Default | Options |
|-------|------|---------|---------|
| voiceName | string | "Zephyr" | Zephyr, Kore, Charon, etc. |
| difficulty | enum | "intermediate" | beginner, intermediate, advanced |
| theme | enum | "light" | light, dark |
| notificationsEnabled | boolean | true | - |

**Firestore Path:** `/users/{userId}`

---

### 2. sessions

Stores training and evaluation sessions.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| sessionId | string (UUID) | PRIMARY KEY | Unique session identifier |
| userId | string (UUID) | FOREIGN KEY, INDEX | Owner user ID |
| sessionType | enum | NOT NULL, INDEX | "training" or "evaluation" |
| status | enum | NOT NULL, INDEX | Session status |
| selectedPersona | string | NULLABLE | Customer persona ID |
| difficulty | enum | NOT NULL | Difficulty level |
| systemInstruction | text | NULLABLE | Custom system prompt |
| startedAt | timestamp | NOT NULL, INDEX | Session start time |
| endedAt | timestamp | NULLABLE | Session end time |
| duration | integer | NULLABLE | Duration in seconds |
| grade | enum | NULLABLE | Final grade (A-F) |
| score | integer | NULLABLE | Score 0-100 |
| messageCount | integer | DEFAULT 0 | Total messages |
| createdAt | timestamp | NOT NULL | Record creation time |
| updatedAt | timestamp | NOT NULL | Last update time |
| isDeleted | boolean | DEFAULT false | Soft delete flag |
| deletedAt | timestamp | NULLABLE | Deletion timestamp |

**status enum values:**
- `active` - Session in progress
- `paused` - Session paused by user
- `completed` - Session finished normally
- `abandoned` - Session ended without completion

**Firestore Path:** `/sessions/{sessionId}`

---

### 3. transcripts

Stores conversation transcripts for sessions.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| transcriptId | string (UUID) | PRIMARY KEY | Unique transcript identifier |
| sessionId | string (UUID) | FOREIGN KEY, UNIQUE, INDEX | Associated session |
| userId | string (UUID) | INDEX | Denormalized for queries |
| messages | array | NOT NULL | Array of message objects |
| totalMessages | integer | NOT NULL | Message count |
| totalWords | integer | DEFAULT 0 | Word count |
| startedAt | timestamp | NOT NULL | First message time |
| endedAt | timestamp | NULLABLE | Last message time |
| createdAt | timestamp | NOT NULL | Record creation time |
| updatedAt | timestamp | NOT NULL | Last update time |

**messages array item:**
```json
{
  "messageId": "msg-uuid",
  "role": "user",
  "text": "Hello, welcome!",
  "timestamp": "2026-01-27T12:00:05Z",
  "isFinal": true,
  "audioLengthMs": 2500,
  "confidence": 0.95
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| messageId | string (UUID) | Yes | Unique message ID |
| role | enum | Yes | "user" or "assistant" |
| text | string | Yes | Message content |
| timestamp | timestamp | Yes | Message time |
| isFinal | boolean | Yes | Transcription finalized |
| audioLengthMs | integer | No | Audio duration |
| confidence | float | No | Transcription confidence |

**Firestore Path:** `/transcripts/{transcriptId}`

**Alternative (Subcollection):** `/sessions/{sessionId}/messages/{messageId}`

---

### 4. evaluations

Stores evaluation results and scorecards.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| evaluationId | string (UUID) | PRIMARY KEY | Unique evaluation identifier |
| sessionId | string (UUID) | FOREIGN KEY, UNIQUE, INDEX | Associated session |
| userId | string (UUID) | FOREIGN KEY, INDEX | Owner user ID |
| grade | enum | NOT NULL | A, B, C, D, or F |
| score | integer | NOT NULL | Score 0-100 |
| scorecard | object | NOT NULL | E.A.S.Y. checklist results |
| feedback | text | NULLABLE | Generated feedback text |
| keyStrengths | array | NULLABLE | List of strengths |
| areasForImprovement | array | NULLABLE | List of improvements |
| suggestedActions | array | NULLABLE | Recommended next steps |
| persona | string | NULLABLE | Customer persona used |
| difficulty | enum | NULLABLE | Difficulty level |
| evaluatedAt | timestamp | NOT NULL | Evaluation time |
| createdAt | timestamp | NOT NULL | Record creation time |
| updatedAt | timestamp | NOT NULL | Last update time |

**scorecard object:**
```json
{
  "engage": {
    "nonBusinessGreet": true,
    "establishedRapport": true,
    "managerMention": false,
    "score": 67
  },
  "ask": {
    "criticalQuestions": 4,
    "layer2Discovery": 3,
    "pbmsIdentified": 2,
    "score": 75
  },
  "show": {
    "powerDemo": true,
    "featureBenefitPbm": true,
    "protectionPlan": false,
    "score": 67
  },
  "yes": {
    "payYourWay": true,
    "clearConstraint": true,
    "closedSale": false,
    "score": 67
  },
  "totalScore": 82
}
```

**Firestore Path:** `/evaluations/{evaluationId}`

---

### 5. refresh_tokens

Stores refresh tokens for session management.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| tokenId | string (UUID) | PRIMARY KEY | Unique token identifier |
| userId | string (UUID) | FOREIGN KEY, INDEX | Token owner |
| tokenHash | string | NOT NULL | SHA-256 hash of token |
| createdAt | timestamp | NOT NULL | Token creation time |
| expiresAt | timestamp | NOT NULL, INDEX | Token expiration time |
| lastUsedAt | timestamp | NULLABLE | Last refresh time |
| isRevoked | boolean | DEFAULT false | Revocation status |
| revokedAt | timestamp | NULLABLE | Revocation time |
| ipAddress | string | NULLABLE | Client IP at creation |
| userAgent | string | NULLABLE | Client user agent |
| deviceName | string | NULLABLE | Device identifier |

**Firestore Path:** `/refresh_tokens/{tokenId}`

---

### 6. knowledge_items (Optional - for cached knowledge base)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| itemId | string | PRIMARY KEY | Knowledge item ID |
| title | string | NOT NULL, INDEX | Item title |
| collection | string | NOT NULL, INDEX | Collection name (BRACKEN, MODERO, etc.) |
| category | string | NOT NULL | Category (product, technique, etc.) |
| content | text | NOT NULL | Full content text |
| keywords | array | NOT NULL | Search keywords |
| relatedItems | array | NULLABLE | Related item IDs |
| createdAt | timestamp | NOT NULL | Creation time |
| updatedAt | timestamp | NOT NULL | Last update time |

**Firestore Path:** `/knowledge_items/{itemId}`

---

## Indexes

### Firestore Composite Indexes

```yaml
# sessions by user and date
- collectionGroup: sessions
  fields:
    - fieldPath: userId
      order: ASCENDING
    - fieldPath: startedAt
      order: DESCENDING

# sessions by user and status
- collectionGroup: sessions
  fields:
    - fieldPath: userId
      order: ASCENDING
    - fieldPath: status
      order: ASCENDING

# evaluations by user and date
- collectionGroup: evaluations
  fields:
    - fieldPath: userId
      order: ASCENDING
    - fieldPath: evaluatedAt
      order: DESCENDING

# refresh_tokens cleanup
- collectionGroup: refresh_tokens
  fields:
    - fieldPath: expiresAt
      order: ASCENDING
    - fieldPath: isRevoked
      order: ASCENDING
```

### PostgreSQL Indexes (Future)

```sql
-- users
CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_created_at ON users(created_at);

-- sessions
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_user_started ON sessions(user_id, started_at DESC);
CREATE INDEX idx_sessions_user_status ON sessions(user_id, status);
CREATE INDEX idx_sessions_status ON sessions(status);

-- transcripts
CREATE UNIQUE INDEX idx_transcripts_session ON transcripts(session_id);
CREATE INDEX idx_transcripts_user ON transcripts(user_id);

-- evaluations
CREATE UNIQUE INDEX idx_evaluations_session ON evaluations(session_id);
CREATE INDEX idx_evaluations_user_date ON evaluations(user_id, evaluated_at DESC);
CREATE INDEX idx_evaluations_grade ON evaluations(grade);

-- refresh_tokens
CREATE INDEX idx_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_tokens_expires ON refresh_tokens(expires_at);
```

---

## Relationships

### Cardinality

| Relationship | Cardinality | Description |
|--------------|-------------|-------------|
| users → sessions | 1:N | User has many sessions |
| sessions → transcripts | 1:1 | Session has one transcript |
| sessions → evaluations | 1:1 | Session has one evaluation |
| users → refresh_tokens | 1:N | User has many tokens |
| users → evaluations | 1:N | User has many evaluations |

### Foreign Key Constraints (PostgreSQL)

```sql
ALTER TABLE sessions
  ADD CONSTRAINT fk_sessions_user
  FOREIGN KEY (user_id) REFERENCES users(user_id)
  ON DELETE CASCADE;

ALTER TABLE transcripts
  ADD CONSTRAINT fk_transcripts_session
  FOREIGN KEY (session_id) REFERENCES sessions(session_id)
  ON DELETE CASCADE;

ALTER TABLE evaluations
  ADD CONSTRAINT fk_evaluations_session
  FOREIGN KEY (session_id) REFERENCES sessions(session_id)
  ON DELETE SET NULL;

ALTER TABLE evaluations
  ADD CONSTRAINT fk_evaluations_user
  FOREIGN KEY (user_id) REFERENCES users(user_id)
  ON DELETE CASCADE;

ALTER TABLE refresh_tokens
  ADD CONSTRAINT fk_tokens_user
  FOREIGN KEY (user_id) REFERENCES users(user_id)
  ON DELETE CASCADE;
```

### Cascade Behavior

| Action | sessions | transcripts | evaluations | refresh_tokens |
|--------|----------|-------------|-------------|----------------|
| Delete User | Cascade | Cascade | Cascade | Cascade |
| Delete Session | - | Cascade | Set NULL | - |
| Soft Delete Session | Preserve | Preserve | Preserve | - |

---

## Query Patterns

### Common Queries

**Get user's recent sessions:**
```python
# Firestore
db.collection('sessions')
  .where('userId', '==', user_id)
  .where('isDeleted', '==', False)
  .order_by('startedAt', 'DESCENDING')
  .limit(20)
```

**Get session with evaluation:**
```python
# Firestore - requires two queries
session = db.collection('sessions').document(session_id).get()
evaluation = db.collection('evaluations')
  .where('sessionId', '==', session_id)
  .limit(1)
  .get()
```

**Get user performance stats:**
```python
# Firestore
evaluations = db.collection('evaluations')
  .where('userId', '==', user_id)
  .where('evaluatedAt', '>=', start_date)
  .get()

# Calculate aggregates in application code
avg_score = sum(e.score for e in evaluations) / len(evaluations)
```

**Cleanup expired tokens:**
```python
# Firestore
expired = db.collection('refresh_tokens')
  .where('expiresAt', '<', now)
  .where('isRevoked', '==', False)
  .get()

for token in expired:
    token.reference.update({'isRevoked': True, 'revokedAt': now})
```

---

## Migration Strategy

### Phase 1: Firestore (POC)

- Use Firestore for rapid development
- Simple document-based structure
- No complex joins required
- Built-in real-time updates

### Phase 2: PostgreSQL (Production)

**Migration Path:**

1. **Create PostgreSQL schema:**
   ```bash
   alembic init migrations
   alembic revision --autogenerate -m "Initial schema"
   alembic upgrade head
   ```

2. **Export Firestore data:**
   ```python
   # Export script
   for doc in db.collection('users').stream():
       export_to_json(doc.to_dict())
   ```

3. **Transform and load:**
   ```python
   # ETL script
   for user in json_users:
       pg_session.add(User(**transform(user)))
   pg_session.commit()
   ```

4. **Validate data:**
   ```python
   assert pg_count('users') == firestore_count('users')
   assert pg_count('sessions') == firestore_count('sessions')
   ```

5. **Switch connection:**
   ```python
   # config.py
   DATABASE_URL = os.getenv('DATABASE_URL')  # PostgreSQL
   ```

### PostgreSQL Schema (Alembic)

```python
# models.py
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

class User(Base):
    __tablename__ = 'users'

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    google_id = Column(String(255), unique=True, index=True)
    avatar_url = Column(String(512))
    preferences = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_login_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)

    sessions = relationship('Session', back_populates='user')
    evaluations = relationship('Evaluation', back_populates='user')

class Session(Base):
    __tablename__ = 'sessions'

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False, index=True)
    session_type = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    selected_persona = Column(String(50))
    difficulty = Column(String(20), nullable=False)
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime)
    duration = Column(Integer)
    grade = Column(String(1))
    score = Column(Integer)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)

    user = relationship('User', back_populates='sessions')
    transcript = relationship('Transcript', back_populates='session', uselist=False)
    evaluation = relationship('Evaluation', back_populates='session', uselist=False)
```

---

## Data Validation Rules

### users

| Field | Validation |
|-------|------------|
| email | Valid email format, max 255 chars |
| name | Min 1 char, max 255 chars |
| preferences.voiceName | One of: Zephyr, Kore, Charon, Puck, Aoede |
| preferences.difficulty | One of: beginner, intermediate, advanced |
| preferences.theme | One of: light, dark |

### sessions

| Field | Validation |
|-------|------------|
| sessionType | One of: training, evaluation |
| status | One of: active, paused, completed, abandoned |
| difficulty | One of: beginner, intermediate, advanced |
| grade | One of: A, B, C, D, F (nullable) |
| score | Integer 0-100 (nullable) |
| duration | Positive integer (nullable) |

### evaluations

| Field | Validation |
|-------|------------|
| grade | One of: A, B, C, D, F |
| score | Integer 0-100 |
| scorecard | Valid E.A.S.Y. structure |
| scorecard.*.score | Integer 0-100 |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-27 | Engineering | Initial schema design |

---

*This schema is the data contract for backend implementation. Changes require approval from technical leads.*
