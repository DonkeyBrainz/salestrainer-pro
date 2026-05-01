# Product Requirements Document: Luxe Sales Coach v2

> **Version:** 1.0.0
> **Last Updated:** 2026-02-19
> **Status:** Current
> **Document Type:** Product Requirements (Functional & Technical Specifications)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Overview](#2-product-overview)
3. [User Personas & Workflows](#3-user-personas--workflows)
4. [Functional Requirements](#4-functional-requirements)
5. [Technical Specifications](#5-technical-specifications)
6. [Integration Points](#6-integration-points)
7. [Testing & Validation Requirements](#7-testing--validation-requirements)
8. [Constraints & Dependencies](#8-constraints--dependencies)
9. [Open Questions & Risks](#9-open-questions--risks)
10. [Reference Documentation](#10-reference-documentation)

---

## 1. Executive Summary

### 1.1 Product Vision

Luxe Sales Coach v2 is an AI-native sales training platform that enables Ashley Furniture sales representatives to master the E.A.S.Y. Selling System through immersive, voice-based roleplay with realistic AI customer personas. The platform replaces traditional static training materials with real-time, adaptive conversations that simulate authentic customer interactions.

### 1.2 Value Proposition

**For Sales Representatives:**
- Practice challenging sales scenarios in a safe, judgment-free environment
- Receive real-time coaching hints aligned with Ashley's proven E.A.S.Y. methodology
- Build muscle memory for techniques that drive $1.25M+ annual sales performance
- Track progress over time with detailed performance scorecards

**For Sales Managers:**
- Scalable training solution available 24/7 without instructor overhead
- Objective performance metrics to identify coaching opportunities
- Standardized evaluation criteria across all team members
- Detailed conversation transcripts for post-session review

### 1.3 Key Objectives

1. **Skill Development**: Enable sales reps to master all four stages of E.A.S.Y. (Engage, Ask, Show, Yes) through deliberate practice
2. **Realistic Simulation**: Provide customer personas with authentic objections, buying motivations, and conversation dynamics
3. **Immediate Feedback**: Deliver contextual coaching hints within 2.5 seconds of identifying technique opportunities
4. **Measurable Progress**: Quantify performance across 12 E.A.S.Y. checklist items with scores and letter grades
5. **Voice-First Experience**: Leverage natural speech for immersive roleplay that mirrors real showroom interactions

### 1.4 Target Users

**Primary Users:**
- **Sales Representatives** (Ashley Furniture): Frontline salespeople seeking to improve technique, confidence, and sales outcomes
- **Experience Levels**: New hires (onboarding), intermediate (skill refinement), advanced (objection handling mastery)

**Secondary Users:**
- **Sales Managers**: Leaders responsible for team training, performance evaluation, and coaching
- **Training Administrators**: Personnel managing training programs and tracking org-wide metrics

### 1.5 Success Criteria

**Technical:**
- WebSocket audio streaming latency <400ms (P95)
- Coach hint generation latency <2.5s (P95)
- Session completion rate >85% (no crashes/disconnects)
- Transcription accuracy >90% for common vocabulary
- System uptime >99.5% during business hours

**User Experience:**
- Training session completion time: 15-20 minutes average
- Evaluation mode completion rate >75%
- User satisfaction score >4/5 (post-session survey)
- Perceived persona realism >4/5 (qualitative feedback)

**Business:**
- 100+ concurrent sessions supported
- Training cost per session <$0.20 (Gemini API + infrastructure)
- Historical session retrieval <2s
- Admin dashboard load time <3s

---

## 2. Product Overview

### 2.1 Problem Statement

Traditional sales training at Ashley Furniture faces critical limitations:

**Static Learning Materials:**
- Video modules and printed scripts cannot adapt to learner needs
- No opportunity to practice techniques in realistic conversations
- Feedback delayed until live customer interactions (high stakes)

**Inconsistent Coaching:**
- Quality depends on manager availability and coaching skill
- No standardized evaluation criteria
- Difficult to scale across geographies and store locations

**Limited Practice Opportunities:**
- Role-play with colleagues lacks authenticity (predictable responses)
- Real customer interactions carry risk of lost sales during learning
- No safe environment for practicing difficult objections

**Measurement Gaps:**
- Subjective assessments lack concrete metrics
- No longitudinal tracking of individual progress
- Difficulty identifying specific skill gaps for targeted coaching

These limitations result in longer ramp-up times for new hires, inconsistent technique application, and missed sales opportunities due to inadequate objection handling skills.

### 2.2 Solution Summary

Luxe Sales Coach v2 delivers AI-powered voice roleplay training with:

**Realistic AI Customer Personas:**
- 11 distinct personas representing common customer archetypes (eager newlyweds, skeptical shoppers, demanding professionals, price-resistant buyers)
- Authentic backstories, buying motivations, objections, and conversation dynamics
- Difficulty levels (Easy, Medium, Hard) with progressively challenging behaviors

**Real-Time Coaching System:**
- Dual-agent architecture: Customer Agent (roleplay) + Coach Agent (analysis)
- Live technique detection during conversation (E.A.S.Y. stage completion)
- Contextual hints delivered within 2.5 seconds of identifying opportunities
- Silent evaluation mode for performance testing without assistance

**Comprehensive Evaluation:**
- Post-session scorecard tracking 12 E.A.S.Y. checklist items
- Letter grades (A-F) based on stage completion and technique quality
- Detailed feedback with strengths, improvement areas, and actionable recommendations
- Full conversation transcript with coach reasoning preserved

**Voice-First Experience:**
- Natural speech input via WebRTC microphone
- Gemini 2.5 Flash Live API for bidirectional audio streaming
- Distinct AI voices per persona (11 voices from Google TTS)
- Real-time transcription displayed in HUD for visual learners

### 2.3 Core Capabilities

1. **Voice Roleplay Sessions** (Training Mode)
   - Select customer persona and difficulty level
   - Speak naturally to AI customer via microphone
   - See live E.A.S.Y. checklist progress in HUD
   - Receive coaching hints after each conversational turn
   - End session and request detailed evaluation

2. **Silent Evaluation** (Assessment Mode)
   - Practice with no coaching hints (test environment)
   - Complete full sales conversation independently
   - Receive comprehensive scorecard at session end
   - Review transcript with coach analysis annotations

3. **Session History & Progress Tracking**
   - Browse past sessions with date, persona, score
   - Review full transcripts with user/assistant messages
   - Track score trends over time
   - Identify recurring skill gaps across sessions

4. **Admin Dashboard** (Manager View)
   - View org-wide persona usage metrics
   - Monitor user activity and session completion rates
   - Track average scores by E.A.S.Y. stage
   - Identify high/low performing personas for training optimization

---

## 3. User Personas & Workflows

### 3.1 Primary User: Sales Representative

**Profile:**
- **Experience Levels**:
  - New Hires (0-3 months): Focus on E.A.S.Y. fundamentals
  - Intermediate (3-12 months): Refining technique quality
  - Advanced (12+ months): Mastering objection handling
- **Goals**:
  - Achieve $1.25M annual sales target
  - Build confidence in difficult customer scenarios
  - Improve close rates and average ticket size
  - Reduce time to competency (new hires)
- **Pain Points**:
  - Limited practice opportunities before real customer interactions
  - Fear of judgment when making mistakes during training
  - Difficulty remembering all 12 E.A.S.Y. checklist items in real-time
  - Uncertainty about which techniques work for which customer types

### 3.2 Secondary User: Sales Manager

**Profile:**
- **Responsibilities**: Team training, performance coaching, sales target accountability
- **Goals**:
  - Standardize training quality across team members
  - Identify coachable moments through objective data
  - Scale training without increasing instructor hours
  - Track team progress toward skill benchmarks
- **Pain Points**:
  - Inconsistent skill levels across team
  - Time-consuming manual role-play and evaluation
  - Lack of objective performance data for coaching conversations
  - Difficulty identifying specific skill gaps for each rep

### 3.3 Workflow 1: Training Session Flow

**Objective**: Practice E.A.S.Y. selling techniques with real-time coaching

**Steps:**

1. **Login & Authentication**
   - User navigates to application URL
   - Clicks "Sign in with Google" button
   - OAuth flow redirects to Google → back to app with JWT token
   - Dashboard loads with user profile and session history

2. **Persona Selection**
   - User clicks "Start New Training Session"
   - Views list of 5 training personas (Eager Newlywed, Busy Parent, Skeptical Shopper, Demanding Professional, Price-Resistant)
   - Reviews persona card: name, backstory, looking for, difficulty level
   - Selects persona → clicks "Begin Session"

3. **Voice Setup & Connection**
   - Browser requests microphone permission (WebRTC)
   - WebSocket connects to `/ws/gemini/live` with JWT token, persona ID, difficulty level
   - Audio visualizer displays to confirm mic input
   - Customer persona greets user (voice audio plays): "Hi, I'm looking for a new sofa for my living room"

4. **Roleplay Conversation**
   - **User speaks**: "Welcome to Ashley! How has your day been?"
   - **HUD updates**: Transcription appears in real-time
   - **Customer responds** (voice + text): "Good, thanks. We just moved into a new place."
   - **Coach analyzes**: Background analysis runs (2s latency)
   - **Hint appears** (if training mode): "Great non-business greeting! Now transition to building rapport by asking about their move."
   - **E.A.S.Y. checklist updates**: "Non-Business Greet" item checked
   - **Repeat**: User continues conversation through stages (Engage → Ask → Show → Yes)

5. **End Session**
   - User clicks "Evaluate" button (or after 30-minute timeout)
   - System flushes pending transcriptions
   - Coach generates final evaluation (5-10s processing)
   - Session status set to COMPLETED

6. **Review Scorecard**
   - Scorecard displays:
     - Overall grade (A-F) and score (0-100)
     - Breakdown by E.A.S.Y. stage (Engage: 67%, Ask: 75%, Show: 67%, Yes: 67%)
     - Strengths: "Effective use of Layer 2 discovery questions"
     - Improvements: "Missed opportunity to present Protection Plan"
     - Suggested Actions: "Practice connecting features to PBMs in next session"
   - Full transcript available for review with coach reasoning annotations

7. **Session Saved**
   - Session persisted to Firestore with metadata (persona, duration, score)
   - Appears in session history for future reference

### 3.4 Workflow 2: Evaluation Session Flow

**Objective**: Assess skill level without coaching assistance

**Steps:**

1. **Select Evaluation Mode**
   - User clicks "Start Evaluation"
   - Views 6 evaluation-only personas (Medium/Hard difficulty)
   - Cannot see persona details in advance (blind assessment)
   - Selects persona → clicks "Begin Evaluation"

2. **Silent Roleplay**
   - Same voice connection flow as training mode
   - **No coaching hints displayed** during conversation
   - E.A.S.Y. checklist hidden from view
   - User must self-direct through stages based on training

3. **Complete Conversation**
   - User completes full sales conversation independently
   - Clicks "Evaluate" when finished

4. **Receive Comprehensive Grading**
   - Scorecard generated with same structure as training mode
   - Detailed feedback on what was done well and what was missed
   - Letter grade assigned
   - Full transcript with coach annotations (visible only after session ends)

5. **Post-Evaluation Review**
   - User can review transcript to see where techniques were detected/missed
   - Compare evaluation score to recent training scores
   - Identify areas for focused practice in next training session

### 3.5 Workflow 3: History Review Flow

**Objective**: Track progress and review past performance

**Steps:**

1. **Access Session History**
   - User clicks "My Sessions" in navigation
   - Table displays:
     - Session date/time
     - Persona name + difficulty
     - Session type (Training / Evaluation)
     - Final score
     - Grade
     - Duration

2. **Filter/Sort Sessions**
   - Filter by: Persona, Date range, Score range, Session type
   - Sort by: Date (newest first), Score (highest/lowest)

3. **Review Individual Session**
   - Click session row → Detail view opens
   - View scorecard summary
   - Read full transcript with timestamps
   - See coaching hints that were delivered (training sessions)
   - Review coach reasoning for technique detections

4. **Track Trends**
   - (Future: Score trend chart over time)
   - (Future: Stage-specific performance trends)
   - (Future: Persona difficulty progression)

---

## 4. Functional Requirements

### 4.1 FR-AUTH: Authentication & User Management

#### FR-AUTH-001: Multi-Provider OAuth
**Description**: Support Google and Microsoft OAuth for single sign-on
**Acceptance Criteria**:
- User can click "Sign in with Google" button
- OAuth flow redirects to provider → back to app with authorization code
- Backend exchanges code for access token and refresh token
- JWT access token issued with 1-hour expiration
- Refresh token stored in Firestore with SHA-256 hash
- User profile created in Firestore users collection (email, name, googleId)

**Priority**: P0 (Must Have)
**Reference**: `/documentation/API_SPECIFICATION.md` lines 86-239

---

#### FR-AUTH-002: Session Management
**Description**: Persistent user sessions with token refresh
**Acceptance Criteria**:
- Access token includes userId, email, name in JWT claims
- Token validated on every authenticated API request
- Refresh token endpoint allows token renewal without re-authentication
- Logout revokes refresh token and invalidates session
- User profile endpoint returns current user info

**Priority**: P0 (Must Have)

---

#### FR-AUTH-003: Admin Role Management
**Description**: Distinguish admin users with elevated permissions
**Acceptance Criteria**:
- User document includes `role` field (user | admin)
- Admin users can access `/admin` dashboard endpoint
- Admin users can view all user sessions and metrics
- Non-admin users receive 403 Forbidden on admin endpoints

**Priority**: P1 (Should Have)
**Reference**: `/backend/app/api/admin.py`

---

### 4.2 FR-TRAIN: Training Mode Features

#### FR-TRAIN-001: Voice Input
**Description**: Capture user speech via WebRTC microphone
**Acceptance Criteria**:
- Frontend requests microphone permission via browser API
- PCM audio streamed at 16kHz mono via WebSocket
- Audio visualizer displays real-time input levels
- No audio recorded or stored (only transcripts saved)

**Priority**: P0 (Must Have)

---

#### FR-TRAIN-002: Real-Time Transcription
**Description**: Display user and AI speech as text in HUD
**Acceptance Criteria**:
- User speech transcribed via Gemini Live API input transcription
- AI customer speech transcribed via output transcription
- Transcriptions appear in HUD within 400ms of speech completion
- Streaming transcription (chunks displayed as words arrive)
- Final consolidated message saved to transcript

**Priority**: P0 (Must Have)
**Reference**: `/documentation/STAKEHOLDER_FEEDBACK_ANALYSIS.md` lines 11-40

---

#### FR-TRAIN-003: E.A.S.Y. Checklist HUD
**Description**: Display 4-stage checklist with real-time progress
**Acceptance Criteria**:
- HUD shows 4 collapsible sections: ENGAGE, ASK, SHOW, YES
- Each section lists stage-specific requirements (see FR-EASY-*)
- Items marked with checkmark as coach detects completion
- Current stage highlighted
- Checklist visible throughout training session

**Priority**: P0 (Must Have)

---

#### FR-TRAIN-004: Coach Hints
**Description**: Provide real-time coaching feedback after user speech
**Acceptance Criteria**:
- Coach analyzes user message within 2.5s of turn completion
- Hint displayed in sidebar with intervention level (INFO, SUGGESTION, WARNING, CRITICAL)
- Hint includes: detected technique, quality assessment, suggested next step
- Hints appear only in training mode (hidden in evaluation mode)
- Hints logged to Firestore for post-session review

**Priority**: P0 (Must Have)
**Reference**: `/backend/app/agents/coach/analyzer.py`

---

#### FR-TRAIN-005: Persona Audio Responses
**Description**: Customer persona responds with natural voice audio
**Acceptance Criteria**:
- Gemini Live API streams audio response (24kHz PCM)
- Audio played via browser WebRTC
- Distinct voice per persona (11 voices: aoede, kore, charon, puck, etc.)
- Response transcription displayed alongside audio
- Audio latency <400ms from user speech end to AI response start

**Priority**: P0 (Must Have)

---

#### FR-TRAIN-006: Session Controls
**Description**: User can pause, resume, or end session
**Acceptance Criteria**:
- "Evaluate" button ends session and requests grading
- 30-minute idle timeout auto-ends session
- Session status tracked (ACTIVE, COMPLETED, ABANDONED)
- Session duration calculated from startedAt to endedAt

**Priority**: P0 (Must Have)

---

### 4.3 FR-EVAL: Evaluation Mode Features

#### FR-EVAL-001: Silent Coaching
**Description**: Hide coaching hints during evaluation sessions
**Acceptance Criteria**:
- Coach analyzer still runs but hints not sent to frontend
- E.A.S.Y. checklist hidden from view
- User must self-direct through conversation stages
- Session metadata marked as `sessionType: evaluation`

**Priority**: P0 (Must Have)

---

#### FR-EVAL-002: Post-Session Grading
**Description**: Generate comprehensive scorecard after session ends
**Acceptance Criteria**:
- Scorecard includes: Overall score (0-100), Grade (A-F)
- Stage-specific scores (Engage, Ask, Show, Yes)
- PBM metrics (expressed, acknowledged, resolved, match rate)
- Objection metrics (raised, resolved, recovery rate)
- Qualitative feedback: strengths, improvements, suggested actions

**Priority**: P0 (Must Have)
**Reference**: `/backend/app/agents/coach/scorer.py`

---

#### FR-EVAL-003: Transcript Review
**Description**: Display full conversation with coach annotations
**Acceptance Criteria**:
- Transcript shows user and assistant messages with timestamps
- Coach reasoning displayed per turn (which techniques detected, confidence scores)
- Techniques highlighted in transcript (color-coded by E.A.S.Y. stage)
- Transcript downloadable as JSON or readable in browser

**Priority**: P1 (Should Have)

---

### 4.4 FR-PERSONA: Customer Personas

#### FR-PERSONA-001: 11 Distinct Personas
**Description**: Provide varied customer archetypes for roleplay
**Acceptance Criteria**:
- 5 training personas: Eager Newlywed, Busy Parent, Skeptical Shopper, Demanding Professional, Price-Resistant
- 6 evaluation-only personas: Tech-Savvy Millennial, Empty Nester, First-Time Buyer, Luxury Renovator, Small Space Dweller, Indecisive Couple
- Each persona includes: name, backstory, product interest, budget range, timeline, PBMs, objections

**Priority**: P0 (Must Have)
**Reference**: `/backend/app/agents/personas.py`

---

#### FR-PERSONA-002: Difficulty Levels
**Description**: Three difficulty tiers for progressive skill development
**Acceptance Criteria**:
- **Easy (High Regard)**: Friendly, volunteers information, easy to build rapport
- **Medium (Medium Regard)**: Reserved initially, warms up after 2-3 exchanges, raises moderate objections
- **Hard (Low Regard)**: Guarded, requires multiple rapport-building attempts, raises firm objections
- Difficulty level filters persona selection in UI

**Priority**: P0 (Must Have)

---

#### FR-PERSONA-003: Unique Voices
**Description**: Distinct AI voice per persona for immersion
**Acceptance Criteria**:
- 11 Google TTS voices assigned (aoede, kore, charon, puck, fenrir, vindemiatrix, leda, zephyr, etc.)
- Voice name passed to Gemini Live API `voiceName` parameter
- Voice consistent throughout session
- Voice matches persona demographics (age, gender, persona)

**Priority**: P1 (Should Have)

---

#### FR-PERSONA-004: Personal Buying Motivators (PBMs)
**Description**: Each persona has 1-2 core PBMs driving behavior
**Acceptance Criteria**:
- Primary PBM: style, durability, budget, quality, convenience, modern design
- Secondary PBM (optional): comfort, easy maintenance, status, value
- PBMs influence persona responses and objections
- Coach detects if salesperson identifies and addresses PBMs

**Priority**: P0 (Must Have)

---

#### FR-PERSONA-005: Objections Library
**Description**: 30+ realistic objections across 6 categories
**Acceptance Criteria**:
- Objection categories: Price, Timing, Authority, Competition, Trust, Logistics
- Each objection has: text, difficulty (soft/firm/immovable), resolution hint
- Persona raises objections contextually during conversation
- Coach tracks if salesperson uses ADS (Acknowledge, Discover, Solve) model

**Priority**: P0 (Must Have)
**Reference**: `/backend/app/data/objections.py`

---

### 4.5 FR-EASY: E.A.S.Y. System Requirements

#### FR-EASY-001: ENGAGE Stage
**Description**: First stage of E.A.S.Y. selling system - building rapport
**Acceptance Criteria**:
- 3 requirements tracked:
  1. **Non-Business Greet**: Uses conversational greeting (weather, compliment, day going)
  2. **Established Rapport**: Demonstrates QAS Conversational Selling (Question-Answer-Share balance)
  3. **Manager Mention**: Introduces store manager during engagement
- Coach detects completion via LLM analysis of conversation
- Stage score: 0-100 based on completion percentage

**Priority**: P0 (Must Have)
**Reference**: `/documentation/AshleyFurnitureEASYSellingSystem.md` lines 36-173

---

#### FR-EASY-002: ASK Stage
**Description**: Second stage - discovering customer needs and PBMs
**Acceptance Criteria**:
- 4 requirements tracked:
  1. **Critical Questions**: Asks 4+ of 5 critical questions (What brings you in? Tell me about your space? Who will use this? Timeline? Shopping around?)
  2. **Layer 2 Discovery**: Asks follow-up "why" questions to deepen understanding
  3. **PBMs Identified**: Discovers minimum 2 Personal Buying Motivators
  4. **Ashley Story Shared**: Tells brand story and community partnerships
- Stage score: 0-100 based on completion percentage

**Priority**: P0 (Must Have)
**Reference**: `/documentation/AshleyFurnitureEASYSellingSystem.md` lines 174-361

---

#### FR-EASY-003: SHOW Stage
**Description**: Third stage - demonstrating solutions and value
**Acceptance Criteria**:
- 3 requirements tracked:
  1. **Power Demonstration**: Shows 3 products across Good/Better/Best tiers, invites physical interaction
  2. **Feature → Benefit → PBM**: Connects every feature to benefit tied to customer's stated PBM
  3. **Protection Plan Presented**: Offers No Use, No Lose protection plan with lifestyle connection
- Stage score: 0-100 based on completion percentage

**Priority**: P0 (Must Have)
**Reference**: `/documentation/AshleyFurnitureEASYSellingSystem.md` lines 362-536

---

#### FR-EASY-004: YES Stage
**Description**: Fourth stage - closing the sale
**Acceptance Criteria**:
- 3 requirements tracked:
  1. **Pay Your Way Presented**: Shows 3 payment options (Lowest Monthly, Lowest Total Price, Best of Both)
  2. **Clear the Constraint Used**: Applies Confirm → Clarify → Commit framework to objections
  3. **Closed Sale**: Gains commitment or schedules follow-up appointment
- Stage score: 0-100 based on completion percentage

**Priority**: P0 (Must Have)
**Reference**: `/documentation/AshleyFurnitureEASYSellingSystem.md` lines 638-916

---

### 4.6 FR-SESSION: Session Management

#### FR-SESSION-001: Session Creation
**Description**: Initialize training or evaluation session
**Acceptance Criteria**:
- Frontend sends WebSocket connection with: JWT token, mode (training/evaluation), persona ID, difficulty
- Backend creates Session document in Firestore: sessionId (UUID), userId, sessionType, status (ACTIVE), selectedPersona, difficulty, startedAt
- Customer agent initialized with persona state
- Coach agent initialized with E.A.S.Y. stage progress

**Priority**: P0 (Must Have)
**Reference**: `/backend/app/models/session.py`

---

#### FR-SESSION-002: Session Persistence
**Description**: Save all session data to Firestore
**Acceptance Criteria**:
- Session metadata: sessionId, userId, sessionType, status, selectedPersona, difficulty, startedAt, endedAt, duration, grade, score, messageCount
- Transcript: Full conversation with user/assistant messages, timestamps, audioLengthMs, confidence scores
- Evaluation: Scorecard with stage scores, PBM metrics, objection metrics, feedback text
- Internal reasoning: Coach's LLM reasoning preserved for post-session review

**Priority**: P0 (Must Have)
**Reference**: `/documentation/DATABASE_SCHEMA.md` lines 120-252

---

#### FR-SESSION-003: Session History API
**Description**: Retrieve past sessions for user
**Acceptance Criteria**:
- Endpoint: `GET /api/v1/sessions?userId={userId}&limit=20&offset=0`
- Returns: List of sessions sorted by startedAt descending
- Includes: sessionId, sessionType, selectedPersona, startedAt, duration, grade, score
- Supports pagination and filtering

**Priority**: P1 (Should Have)

---

#### FR-SESSION-004: Session Detail API
**Description**: Retrieve full session with transcript and evaluation
**Acceptance Criteria**:
- Endpoint: `GET /api/v1/sessions/{sessionId}`
- Returns: Session metadata + full transcript + evaluation scorecard
- Includes coach reasoning for each analyzed turn
- Transcript messages include: messageId, role, text, timestamp, isFinal, audioLengthMs, confidence

**Priority**: P1 (Should Have)

---

#### FR-SESSION-005: Session Status Tracking
**Description**: Track session lifecycle states
**Acceptance Criteria**:
- Status values: ACTIVE, COMPLETED, ABANDONED, PAUSED (reserved)
- ACTIVE: Session in progress
- COMPLETED: User requested evaluation and session ended normally
- ABANDONED: WebSocket disconnected without evaluation
- Status transitions logged with timestamps

**Priority**: P0 (Must Have)

---

### 4.7 FR-ADMIN: Admin Dashboard

#### FR-ADMIN-001: Persona Usage Metrics
**Description**: Track which personas are used most frequently
**Acceptance Criteria**:
- Display persona usage count over date range
- Show average score per persona
- Identify personas with highest/lowest success rates
- Filter by user or org-wide

**Priority**: P2 (Nice to Have)
**Reference**: `/backend/app/api/admin.py`

---

#### FR-ADMIN-002: User Activity Monitoring
**Description**: View user session completion rates and trends
**Acceptance Criteria**:
- List all users with: total sessions, avg score, last session date
- Filter users by activity level (active, inactive)
- View individual user's session history
- Export user metrics as CSV

**Priority**: P2 (Nice to Have)

---

#### FR-ADMIN-003: Volunteer Behavior Scoring
**Description**: Track coach hint quality and user engagement
**Acceptance Criteria**:
- Display coach hint delivery frequency
- Show hint intervention level distribution (INFO, SUGGESTION, WARNING, CRITICAL)
- Track user response to hints (did they adjust technique?)
- Identify coaching blind spots (techniques rarely detected)

**Priority**: P2 (Nice to Have)

---

### 4.8 FR-RAG: Product Knowledge Integration

#### FR-RAG-001: PDF Document Ingestion
**Description**: Process product catalogs into vector database
**Acceptance Criteria**:
- 8 PDF documents uploaded to Google Cloud Storage
- Documents chunked (800 chars, 200 overlap)
- Chunks embedded via Gemini text-embedding-004 (768 dimensions)
- Stored in Firestore `knowledge_chunks` collection with metadata

**Priority**: P1 (Should Have)
**Reference**: `/documentation/RAG_INTEGRATION_PLAN.md` lines 32-175

---

#### FR-RAG-002: Vector Search Retrieval
**Description**: Query product knowledge for coaching hints
**Acceptance Criteria**:
- Coach analyzer queries Firestore vector search before generating hint
- Retrieves top 3 relevant chunks via COSINE similarity
- Query latency <200ms
- Product context injected into coach prompt

**Priority**: P1 (Should Have)

---

#### FR-RAG-003: Product-Aware Hints
**Description**: Coaching hints reference specific product features
**Acceptance Criteria**:
- Hint includes: Product name, feature details, pricing (if available)
- Example: "This SECTIONAL features stain-resistant performance fabric - perfect for families with kids. Mention it's easy to clean."
- Hints more specific than generic "Ask about durability"

**Priority**: P1 (Should Have)

---

#### FR-RAG-004: Metadata Filtering
**Description**: Filter product knowledge by persona context
**Acceptance Criteria**:
- Personas include product_category field (living_room, bedroom, mattress, dining, home_office)
- Vector search filtered by category before retrieval
- Only relevant product chunks returned for persona's stated need

**Priority**: P2 (Nice to Have)
**Reference**: `/documentation/RAG_PHASE_2_IMPLEMENTATION.md`

---

## 5. Technical Specifications

### 5.1 System Architecture

#### 5.1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React 19)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Voice UI     │  │ E.A.S.Y. HUD │  │ Scorecard    │         │
│  │ (WebRTC)     │  │ (Checklist)  │  │ (Report)     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                   │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          │ WebSocket       │ REST API        │ REST API
          │ (Audio)         │ (Session)       │ (Evaluation)
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ WebSocket    │  │ Session      │  │ Auth         │         │
│  │ Relay        │  │ Service      │  │ Service      │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                   │
│  ┌──────┴───────┬─────────┴─────────┬───────┴───────┐         │
│  │ Customer     │ Coach             │ RAG           │         │
│  │ Agent        │ Agent             │ Service       │         │
│  │ (LangGraph)  │ (Analyzer)        │ (Firestore)   │         │
│  └──────┬───────┴─────────┬─────────┴───────┬───────┘         │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   External Services (GCP)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Gemini 2.5   │  │ Firestore    │  │ Secret       │         │
│  │ Flash        │  │ (Native)     │  │ Manager      │         │
│  │ Live API     │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.1.2 Component Diagram

**Frontend:**
- **React 19** + TypeScript
- **WebRTC**: Browser audio input/output
- **WebSocket Client**: Bidirectional audio/text streaming
- **State Management**: React hooks (useState, useEffect, useContext)
- **UI Components**: Voice interface, E.A.S.Y. HUD, Report card, Admin dashboard

**Backend:**
- **FastAPI** (Python 3.11+)
- **WebSocket Relay**: Manages Gemini Live API connections
- **Dual-Agent System**:
  - **Customer Agent** (LangGraph): Stateful customer persona behavior
  - **Coach Agent** (Gemini 2.0 Flash): Real-time technique analysis
- **REST API**: Authentication, session CRUD, evaluation retrieval
- **RAG Service**: Firestore vector search for product knowledge

**External Integrations:**
- **Gemini 2.5 Flash Live API**: Voice conversation
- **Gemini 2.0 Flash**: Coach analysis and RAG embeddings
- **Firestore**: Users, sessions, transcripts, evaluations, knowledge chunks
- **Google Cloud Storage**: PDF product catalogs
- **Secret Manager**: API keys and credentials

---

### 5.2 Backend Specifications

#### 5.2.1 REST API Endpoints

**Authentication:**
- `GET /auth/login` - Initiate OAuth flow
- `POST /auth/callback` - Handle OAuth callback
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user profile
- `POST /auth/logout` - Revoke session

**Sessions:**
- `GET /api/v1/sessions` - List user sessions (paginated)
- `GET /api/v1/sessions/{sessionId}` - Get session detail + transcript + evaluation
- `DELETE /api/v1/sessions/{sessionId}` - Soft delete session

**Personas:**
- `GET /personas` - List training personas
- `GET /personas/evaluation` - List evaluation personas
- `GET /personas/filter?category={category}` - Filter by product category

**Admin:**
- `GET /admin/metrics/personas` - Persona usage stats
- `GET /admin/metrics/users` - User activity stats
- `GET /admin/sessions` - All sessions across org

**Health:**
- `GET /health` - Basic health check
- `GET /ready` - Readiness check with dependency status

**Full API Specification**: See `/documentation/API_SPECIFICATION.md`

---

#### 5.2.2 Dual-Agent System

**Customer Agent (LangGraph Stateful Agent):**

**Purpose**: Simulate realistic customer persona behavior

**State Management**:
```python
class CustomerAgentState(TypedDict):
    messages: list[BaseMessage]  # Conversation history
    persona: CustomerPersona  # Selected persona
    mood: str  # NEUTRAL, INTERESTED, SKEPTICAL, ENGAGED, FRUSTRATED
    regard_level: RegardLevel  # HIGH, LOW, NO
    objections_raised: list[str]  # Objections mentioned
    objections_resolved: list[str]  # Objections successfully handled
    pbms_expressed: list[str]  # PBMs customer revealed
    pbms_acknowledged: list[str]  # PBMs salesperson recognized
    stage_progress: EASYStageProgress  # Current E.A.S.Y. stage + checklist
    turn_count: int  # Number of conversational turns
```

**Behavioral Logic**:
- Responds to salesperson based on persona difficulty level
- Raises objections contextually (e.g., price objection if budget exceeded)
- Adjusts mood based on salesperson technique quality
- Provides buying signals when rapport established and needs addressed
- Ends conversation naturally if close attempted successfully

**LangGraph Flow**:
```
User Message → Process → Update State → Generate Response
                ↓
          Check Mood/Regard
                ↓
     Select Objection (if applicable)
                ↓
      Format Response with Persona Voice
```

**Reference**: `/backend/app/agents/customer_agent.py`

---

**Coach Agent (Gemini 2.0 Flash Analysis):**

**Purpose**: Analyze salesperson technique and generate coaching hints

**Analysis Process**:
1. Receives: Salesperson message, conversation history, persona context, current stage progress
2. Queries: Firestore vector search for product context (RAG)
3. Calls: Gemini 2.0 Flash with structured prompt
4. Returns: JSON with detected techniques, confidence scores, intervention level, hint text

**Coach Analysis Response Schema**:
```json
{
  "stage_items_completed": ["non_business_greet", "established_rapport"],
  "pbms_detected": ["durability", "easy_maintenance"],
  "techniques_used": ["layer_2_discovery", "feature_benefit_pbm"],
  "technique_quality": 0.85,
  "intervention_level": "SUGGESTION",
  "hint": "Great job asking about their concerns! Now connect this to a specific product feature.",
  "reasoning": "Salesperson asked Layer 2 question but didn't tie answer to product recommendation"
}
```

**Intervention Levels**:
- **NONE**: No hint needed, on track
- **INFO**: Informational nudge (e.g., "You're in ASK stage")
- **SUGGESTION**: Technique improvement opportunity
- **WARNING**: Missing critical step
- **CRITICAL**: Major deviation from E.A.S.Y. system

**Reference**: `/backend/app/agents/coach/analyzer.py`

---

#### 5.2.3 LangGraph State Management

**Why LangGraph**:
- Maintains conversational state across turns
- Prevents role confusion (customer vs salesperson)
- Enables complex multi-turn behaviors
- Supports state persistence to Firestore

**State Persistence**:
- Agent state serialized to JSON
- Stored in Session document `agent_state` field
- Restored on reconnection (session resumption)

**State Transitions**:
```
NEUTRAL mood → INTERESTED (if good rapport)
            → SKEPTICAL (if objection raised)
            → FRUSTRATED (if objection mishandled)

LOW regard → MEDIUM (after 2-3 positive exchanges)
          → HIGH (after strong PBM connection)

Stage: ENGAGE → ASK → SHOW → YES (coach drives progression)
```

**Reference**: `/documentation/AGENT_FLOW.md`

---

#### 5.2.4 Database Schema

**Collections (Firestore)**:

1. **users**
   - userId (PK), email, name, googleId, preferences, createdAt, updatedAt
   - Preferences: voiceName, difficulty, theme, notificationsEnabled

2. **sessions**
   - sessionId (PK), userId (FK), sessionType, status, selectedPersona, difficulty
   - startedAt, endedAt, duration, grade, score, messageCount

3. **transcripts**
   - transcriptId (PK), sessionId (FK), userId, messages[], totalMessages, totalWords
   - Messages: messageId, role, text, timestamp, isFinal, audioLengthMs, confidence

4. **evaluations**
   - evaluationId (PK), sessionId (FK), userId (FK), grade, score
   - scorecard: {engage, ask, show, yes, totalScore}
   - feedback, keyStrengths[], areasForImprovement[], suggestedActions[]

5. **refresh_tokens**
   - tokenId (PK), userId (FK), tokenHash, expiresAt, isRevoked

6. **knowledge_chunks** (RAG)
   - chunk_id (PK), content, embedding (Vector 768D), metadata

**Full Schema**: See `/documentation/DATABASE_SCHEMA.md`

---

### 5.3 Frontend Specifications

#### 5.3.1 UI Components

**VoiceInterface Component**:
- **Purpose**: Capture user speech and play AI responses
- **Features**: Microphone permission, audio visualizer, mute/unmute, volume control
- **State**: isConnected, isSpeaking, audioLevel, transcriptBuffer

**EASYChecklist Component**:
- **Purpose**: Display 4-stage checklist with real-time progress
- **Features**: Collapsible stages, checkmark animations, current stage highlight
- **State**: stageProgress (from WebSocket updates)

**ReportCard Component**:
- **Purpose**: Display post-session evaluation scorecard
- **Features**: Grade badge, score chart, stage breakdown, strengths/improvements list
- **State**: evaluation (from API response)

**SessionHistory Component**:
- **Purpose**: Browse past sessions
- **Features**: Table with filters, pagination, detail modal
- **State**: sessions[] (from API), currentPage, filters

**AdminDashboard Component**:
- **Purpose**: Org-wide metrics (admin users only)
- **Features**: Persona usage chart, user activity table, avg scores by stage
- **State**: metrics (from admin API)

---

#### 5.3.2 State Management

**React Context Providers**:
- **AuthContext**: userId, accessToken, refreshToken, isAuthenticated
- **SessionContext**: currentSession, persona, difficulty, sessionType
- **WebSocketContext**: ws connection, connectionStatus, sendAudio, sendControl

**WebSocket Message Handling**:
```typescript
interface WSMessage {
  type: 'hint' | 'transcription' | 'stage_update' | 'error' | 'evaluation';
  data: any;
}

// Example: Coach hint
{
  type: 'hint',
  data: {
    hint: "Ask about their timeline to move conversation forward",
    interventionLevel: "SUGGESTION"
  }
}

// Example: Stage update
{
  type: 'stage_update',
  data: {
    currentStage: "ASK",
    itemsCompleted: ["non_business_greet", "established_rapport"]
  }
}
```

---

### 5.4 Integration Specifications

#### 5.4.1 Gemini Live API

**Connection**:
- Protocol: WebSocket
- Endpoint: `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent`
- Authentication: API key in query parameter

**Audio Formats**:
- **Input**: PCM 16-bit, 16kHz mono
- **Output**: PCM 16-bit, 24kHz mono
- **Encoding**: Raw bytes (binary WebSocket frames)

**Configuration**:
```python
config = types.LiveConnectConfig(
    response_modalities=[Modality.AUDIO],
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),
    voice_name="aoede",  # Persona-specific voice
    system_instruction=persona_system_prompt,
)
```

**Message Types**:
- `client_content` (audio input)
- `server_content` (audio output + transcription)
- `input_transcription` (user speech text)
- `output_transcription` (AI speech text)
- `internal_reasoning` (model thinking, not shown to user)
- `end` (turn completion signal)

**Error Handling**:
- Automatic reconnection up to 3 attempts
- Exponential backoff (1s, 2s, 4s)
- Session state preserved for 5 minutes after disconnect

**Reference**: `/backend/app/services/gemini_service.py`

---

#### 5.4.2 Firestore Vector Search

**Index Configuration**:
```hcl
resource "google_firestore_index" "knowledge_chunks_vector" {
  collection = "knowledge_chunks"

  fields {
    field_path = "embedding"
    vector_config {
      dimension = 768
      flat {}
    }
  }

  fields {
    field_path = "metadata.category"
    order = "ASCENDING"
  }
}
```

**Query Example**:
```python
results = await db.collection("knowledge_chunks").find_nearest(
    vector_field="embedding",
    query_vector=query_embedding,  # From Gemini text-embedding-004
    distance_measure=DistanceMeasure.COSINE,
    limit=3
).get()
```

**Performance**:
- Query latency: <200ms (P95)
- Index build time: 30-60 minutes (one-time)
- Storage: ~2KB per chunk (content + embedding + metadata)

**Reference**: `/documentation/RAG_PHASE_1_IMPLEMENTATION.md`

---

### 5.5 Data Models

#### 5.5.1 Core Entities

**User**:
```typescript
interface User {
  userId: string;  // UUID
  email: string;
  name: string;
  googleId: string;
  avatarUrl?: string;
  preferences: UserPreferences;
  createdAt: Date;
  updatedAt: Date;
}

interface UserPreferences {
  voiceName: string;  // Default: "Zephyr"
  difficulty: "beginner" | "intermediate" | "advanced";
  theme: "light" | "dark";
  notificationsEnabled: boolean;
}
```

**Session**:
```typescript
interface Session {
  sessionId: string;  // UUID
  userId: string;  // FK to users
  sessionType: "training" | "evaluation";
  status: "ACTIVE" | "COMPLETED" | "ABANDONED" | "PAUSED";
  selectedPersona: string;  // Persona ID
  difficulty: "beginner" | "intermediate" | "advanced";
  startedAt: Date;
  endedAt?: Date;
  duration?: number;  // seconds
  grade?: "A" | "B" | "C" | "D" | "F";
  score?: number;  // 0-100
  messageCount: number;
  createdAt: Date;
  updatedAt: Date;
}
```

**Transcript**:
```typescript
interface Transcript {
  transcriptId: string;  // UUID
  sessionId: string;  // FK to sessions
  userId: string;  // Denormalized for queries
  messages: TranscriptMessage[];
  totalMessages: number;
  totalWords: number;
  startedAt: Date;
  endedAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}

interface TranscriptMessage {
  messageId: string;  // UUID
  role: "user" | "assistant";
  text: string;
  timestamp: Date;
  isFinal: boolean;
  audioLengthMs?: number;
  confidence?: number;  // 0-1
}
```

**Evaluation**:
```typescript
interface Evaluation {
  evaluationId: string;  // UUID
  sessionId: string;  // FK to sessions
  userId: string;  // FK to users
  grade: "A" | "B" | "C" | "D" | "F";
  score: number;  // 0-100
  scorecard: Scorecard;
  feedback?: string;
  keyStrengths?: string[];
  areasForImprovement?: string[];
  suggestedActions?: string[];
  evaluatedAt: Date;
  createdAt: Date;
}

interface Scorecard {
  engage: StageScore;
  ask: StageScore;
  show: StageScore;
  yes: StageScore;
  totalScore: number;
}

interface StageScore {
  itemsCompleted: string[];
  totalItems: number;
  score: number;  // 0-100
}
```

---

#### 5.5.2 E.A.S.Y. System Data

**Stages**:
- **ENGAGE**: 3 items (non_business_greet, established_rapport, manager_mention)
- **ASK**: 4 items (critical_questions, layer_2_discovery, pbms_identified, ashley_story)
- **SHOW**: 3 items (power_demonstration, feature_benefit_pbm, protection_plan)
- **YES**: 3 items (pay_your_way, clear_constraint, closed_sale)

**Total**: 13 checklist items (12 stage items + overall close)

**Reference**: `/backend/app/data/easy_system.py`

---

#### 5.5.3 Persona Data

**CustomerPersona**:
```python
@dataclass
class CustomerPersona:
    id: str  # "eager_newlywed"
    name: str  # "Maria"
    backstory: str
    looking_for: str  # "Living room set - sofa and coffee table"
    budget_range: tuple[int, int]  # (2000, 4000)
    timeline: Timeline  # URGENT, FLEXIBLE, BROWSING
    difficulty: Difficulty  # HIGH_REGARD, MEDIUM_REGARD, LOW_REGARD
    initial_regard: RegardLevel  # HIGH, LOW, NO
    primary_pbm: str  # "style"
    secondary_pbm: str | None  # "comfort"
    objections: list[str]  # ["need to measure the space"]
    objection_difficulty: ObjectionDifficulty  # SOFT, FIRM, IMMOVABLE
    voice_name: str  # "aoede"
    is_evaluation_only: bool
    product_category: str  # "living_room"
    product_type: str  # "sectional"
    product_keywords: list[str]  # ["modern", "affordable", "quality"]
```

**11 Personas**:
1. Eager Newlywed (Maria) - High Regard, Living Room
2. Busy Parent (Sarah) - Medium Regard, Sectional
3. Skeptical Shopper (Robert) - Medium Regard, Recliner
4. Demanding Professional (Dr. Chen) - Low Regard, Bedroom Set
5. Price-Resistant (Mike) - Low Regard, Mattress
6. Tech-Savvy Millennial (James) - Evaluation, Home Office
7. Empty Nester (Linda) - Evaluation, Dining
8. First-Time Buyer (Alex) - Evaluation, Living Room
9. Luxury Renovator (Patricia) - Evaluation, Bedroom
10. Small Space Dweller (Kenji) - Evaluation, Compact Furniture
11. Indecisive Couple (Taylor & Jordan) - Evaluation, Living Room

**Reference**: `/backend/app/agents/personas.py`

---

#### 5.5.4 Objections Data

**Categories**:
1. **Price** (6 objections): "That's more than I wanted to spend", "Can't afford monthly payments"
2. **Timing** (5 objections): "Just browsing today", "Need time to think"
3. **Authority** (4 objections): "Need to talk to my spouse", "Need family input"
4. **Competition** (4 objections): "Saw it cheaper elsewhere", "Comparing stores"
5. **Trust** (5 objections): "Not sure about quality", "Want to see reviews"
6. **Logistics** (6 objections): "Need to measure", "Delivery concerns"

**Objection Structure**:
```python
{
    "text": "That's more than I wanted to spend.",
    "difficulty": "soft",  # soft, firm, immovable
    "resolution_hint": "Present monthly payment option, focus on value per day"
}
```

**Reference**: `/backend/app/data/objections.py`

---

### 5.6 Non-Functional Requirements

#### 5.6.1 Performance

**NFR-PERF-001: WebSocket Latency**
- **Requirement**: Audio streaming latency <400ms (P95)
- **Measurement**: Time from user speech end to AI response start
- **Target**: 95% of turns complete within 400ms

**NFR-PERF-002: Coach Hint Generation**
- **Requirement**: Coach hint latency <2.5s (P95)
- **Measurement**: Time from user message to hint displayed in UI
- **Target**: 95% of hints delivered within 2.5s

**NFR-PERF-003: API Response Time**
- **Requirement**: REST API response time <1s (P95)
- **Measurement**: Server processing time excluding network
- **Endpoints**: /sessions, /evaluations, /personas

**NFR-PERF-004: Session History Load**
- **Requirement**: Session history page load <2s
- **Measurement**: Time from API request to UI render
- **Includes**: Query 20 sessions + metadata

---

#### 5.6.2 Reliability

**NFR-REL-001: Session Completion Rate**
- **Requirement**: >85% of sessions complete without crash/disconnect
- **Measurement**: COMPLETED sessions / (COMPLETED + ABANDONED)
- **Excludes**: User-initiated abandonment

**NFR-REL-002: WebSocket Reconnection**
- **Requirement**: Automatic reconnection within 10s of disconnect
- **Attempts**: Up to 3 reconnection attempts with exponential backoff
- **State Preservation**: Session state maintained for 5 minutes

**NFR-REL-003: Data Persistence**
- **Requirement**: 100% of session data persisted to Firestore
- **Data**: Session metadata, transcript, evaluation, agent state
- **Failure Handling**: Retry logic with 3 attempts

**NFR-REL-004: System Uptime**
- **Requirement**: 99.5% uptime during business hours (8am-8pm ET)
- **Measurement**: Cloud Run health check success rate
- **Excludes**: Planned maintenance windows

---

#### 5.6.3 Scalability

**NFR-SCALE-001: Concurrent Sessions**
- **Requirement**: Support 100+ concurrent sessions
- **Resources**: Cloud Run auto-scaling, Firestore connection pooling
- **Bottleneck**: Gemini Live API rate limits (unknown)

**NFR-SCALE-002: User Base**
- **Requirement**: Support 1,000+ registered users
- **Data Volume**: ~20 sessions per user per month average
- **Storage**: Firestore handles 24,000 sessions/month

**NFR-SCALE-003: Historical Data**
- **Requirement**: Maintain 2 years of session history
- **Query Performance**: Session list query <2s with 100,000+ sessions
- **Indexes**: Composite indexes on userId + startedAt

---

#### 5.6.4 Security

**NFR-SEC-001: Authentication**
- **Requirement**: OAuth 2.0 with Google/Microsoft providers
- **Token Security**: JWT access tokens with 1-hour expiration
- **Refresh Tokens**: SHA-256 hashed, stored in Firestore, revocable

**NFR-SEC-002: Data Encryption**
- **Requirement**: TLS 1.2+ for all data in transit
- **Firestore**: Data encrypted at rest (Google-managed keys)
- **WebSocket**: Secure WebSocket (WSS) required

**NFR-SEC-003: Audio Privacy**
- **Requirement**: No audio recordings stored
- **Storage**: Only text transcripts saved to Firestore
- **Compliance**: GDPR right to deletion (delete user + all sessions)

**NFR-SEC-004: Access Control**
- **Requirement**: Users can only access own sessions
- **Admin Role**: Admin users can access all sessions (org-wide)
- **API Validation**: userId checked against JWT claims on every request

---

#### 5.6.5 Usability

**NFR-USE-001: Browser Compatibility**
- **Requirement**: Support Chrome 90+, Edge 90+, Safari 14+, Firefox 88+
- **WebRTC**: Browser must support getUserMedia and WebSocket
- **Fallback**: Display error if WebRTC not supported

**NFR-USE-002: Responsive Design**
- **Requirement**: UI works on desktop (1920x1080), tablet (768x1024), mobile (375x667)
- **Priority**: Desktop-first (primary use case)
- **Mobile**: Read-only access to session history (no voice training)

**NFR-USE-003: Accessibility**
- **Requirement**: WCAG 2.1 AA compliance
- **Features**: Keyboard navigation, screen reader support, color contrast
- **Transcription**: Visual transcription for hearing-impaired users

**NFR-USE-004: Session Duration**
- **Requirement**: Average training session 15-20 minutes
- **Timeout**: 30-minute idle timeout (configurable)
- **Progress**: Auto-save every 5 minutes (future)

---

## 6. Integration Points

### 6.1 External Systems

#### 6.1.1 Google OAuth
- **Purpose**: Single sign-on authentication
- **API**: Google OAuth 2.0 API
- **Scopes**: `openid`, `email`, `profile`
- **Integration**: Backend OAuth callback endpoint (`/auth/callback`)
- **Credentials**: OAuth client ID/secret stored in Secret Manager

---

#### 6.1.2 Microsoft OAuth
- **Purpose**: Alternative SSO for enterprise users
- **API**: Microsoft Identity Platform (Azure AD)
- **Scopes**: `openid`, `email`, `profile`
- **Integration**: Same callback endpoint as Google
- **Status**: Planned (not yet implemented)

---

#### 6.1.3 Gemini API
- **Purpose**: Voice conversation and coach analysis
- **Models**:
  - Gemini 2.5 Flash (Live API) - Customer persona
  - Gemini 2.0 Flash - Coach analyzer
  - text-embedding-004 - RAG embeddings
- **API Key**: Stored in Secret Manager
- **Rate Limits**: Unknown for Live API (preview product)
- **Cost**: ~$0.05-0.15 per 20-minute session (estimated)

---

#### 6.1.4 Google Cloud Storage
- **Purpose**: Store product knowledge PDFs
- **Bucket**: `gs://ashley-ai-sales-coach-knowledge/`
- **Access**: Backend service account has `storage.objectViewer` role
- **Files**: 8 PDF catalogs (bedroom, living room, mattresses, etc.)

---

#### 6.1.5 Secret Manager
- **Purpose**: Secure credential storage
- **Secrets**:
  - `gemini-api-key`
  - `oauth-client-secret`
  - `jwt-secret-key`
- **Access**: Backend service account has `secretmanager.secretAccessor` role

---

### 6.2 Internal APIs

#### 6.2.1 REST API
- **Base URL**: `https://api.luxe-sales-coach.run.app` (production)
- **Authentication**: Bearer token (JWT) in `Authorization` header
- **Endpoints**: Auth, Sessions, Personas, Admin, Health
- **Documentation**: OpenAPI spec generated by FastAPI (`/docs`)

---

#### 6.2.2 WebSocket API
- **Endpoint**: `/ws/gemini/live`
- **Authentication**: JWT token in query parameter (`?token={accessToken}`)
- **Protocol**: Binary audio frames + JSON text messages
- **Lifecycle**: Connect → Stream audio → Receive hints → Disconnect

---

#### 6.2.3 Admin API
- **Purpose**: Org-wide metrics for managers
- **Access**: Restricted to admin users (role check)
- **Endpoints**:
  - `GET /admin/metrics/personas`
  - `GET /admin/metrics/users`
  - `GET /admin/sessions`

---

### 6.3 Future Integration Opportunities

**Learning Management Systems (LMS)**:
- Export session data to LMS for compliance tracking
- SSO integration with corporate identity providers
- Grade sync to HR systems

**CRM Integration**:
- Link training sessions to real sales performance data
- Identify correlation between training scores and sales outcomes

**Webhooks**:
- Notify external systems on session completion
- Trigger follow-up actions (e.g., manager review for low scores)

---

## 7. Testing & Validation Requirements

### 7.1 Functional Testing

**TEST-FUNC-001: E.A.S.Y. Technique Detection**
- **Objective**: Validate coach detects all 12 checklist items accurately
- **Method**: 50+ test conversations with known technique usage
- **Pass Criteria**: >85% true positive rate, <10% false positive rate

**TEST-FUNC-002: Persona Behavior**
- **Objective**: Validate personas exhibit expected traits and objections
- **Method**: 20+ sessions per persona, qualitative review
- **Pass Criteria**: Testers rate realism >4/5, objections appropriate to difficulty

**TEST-FUNC-003: Objection Handling**
- **Objective**: Validate 30+ objections raised contextually
- **Method**: Test scenarios designed to trigger each objection
- **Pass Criteria**: Objection raised when appropriate, resolution hints accurate

---

### 7.2 Performance Testing

**TEST-PERF-001: Load Testing**
- **Objective**: Validate system handles 100 concurrent sessions
- **Method**: Load testing tool (k6, Locust) simulates 100 WebSocket connections
- **Pass Criteria**: <5% error rate, latency within targets

**TEST-PERF-002: Audio Latency**
- **Objective**: Measure WebSocket audio streaming latency
- **Method**: Timestamp comparison (client send → server receive → client receive)
- **Pass Criteria**: P95 latency <400ms

**TEST-PERF-003: Coach Hint Latency**
- **Objective**: Measure hint generation time
- **Method**: Timestamp comparison (turn end → hint displayed)
- **Pass Criteria**: P95 latency <2.5s

---

### 7.3 User Acceptance Testing

**TEST-UAT-001: Real Sales Reps**
- **Objective**: Validate system meets user needs
- **Participants**: 10-20 Ashley sales reps (new hires + experienced)
- **Method**: Guided sessions + feedback survey
- **Pass Criteria**: Satisfaction >4/5, perceived value >4/5

**TEST-UAT-002: Persona Realism**
- **Objective**: Validate personas feel like real customers
- **Participants**: Same as UAT-001
- **Method**: Post-session survey on persona authenticity
- **Pass Criteria**: Realism rating >4/5 across all personas

**TEST-UAT-003: Coaching Quality**
- **Objective**: Validate hints are helpful and accurate
- **Participants**: Sales managers review hint quality
- **Method**: Review 50 training sessions, rate hint relevance
- **Pass Criteria**: >80% of hints rated "helpful" or "very helpful"

---

### 7.4 Security Testing

**TEST-SEC-001: Authentication**
- **Objective**: Validate OAuth flow and token security
- **Method**: Penetration testing, token expiration tests
- **Pass Criteria**: No authentication bypass, tokens expire correctly

**TEST-SEC-002: Authorization**
- **Objective**: Validate users can only access own sessions
- **Method**: Attempt to access other users' sessions via API
- **Pass Criteria**: 403 Forbidden on unauthorized access

**TEST-SEC-003: Data Leakage**
- **Objective**: Validate no sensitive data exposed
- **Method**: Review API responses, logs, error messages
- **Pass Criteria**: No API keys, tokens, or PII in responses

---

## 8. Constraints & Dependencies

### 8.1 Technical Constraints

**CONST-TECH-001: Gemini Live API Preview Status**
- **Constraint**: Gemini 2.5 Flash Live API is in preview (not GA)
- **Risk**: Breaking API changes, no SLA, potential deprecation
- **Mitigation**: Monitor release notes, maintain API version flexibility

**CONST-TECH-002: Firestore Vector Search Preview**
- **Constraint**: Firestore vector search in preview (not GA)
- **Risk**: API changes, performance unpredictability
- **Mitigation**: Have fallback to non-RAG coach hints if vector search fails

**CONST-TECH-003: WebRTC Browser Support**
- **Constraint**: Requires modern browser with WebRTC support
- **Impact**: No support for IE, older Safari versions
- **Mitigation**: Display browser compatibility check on login

**CONST-TECH-004: Single Organization Scope**
- **Constraint**: System designed for Ashley Furniture only (not multi-tenant)
- **Impact**: No organization-level isolation, shared user namespace
- **Future**: Require refactor for multi-tenant support

---

### 8.2 Dependencies

**DEP-001: GCP Availability**
- **Dependency**: Google Cloud Platform services (Cloud Run, Firestore, Secret Manager)
- **SLA**: 99.95% uptime (Cloud Run), 99.95% (Firestore)
- **Failure Mode**: Service unavailable if GCP region down

**DEP-002: Gemini API Rate Limits**
- **Dependency**: Gemini API quota and rate limits
- **Unknown**: Live API rate limits not documented (preview product)
- **Failure Mode**: Session creation fails if quota exceeded

**DEP-003: OAuth Provider Availability**
- **Dependency**: Google/Microsoft OAuth services
- **SLA**: 99.9% (Google), 99.9% (Microsoft)
- **Failure Mode**: New logins fail if OAuth service down (existing sessions continue)

---

### 8.3 Assumptions

**ASSUME-001: Stable Internet**
- **Assumption**: Users have reliable broadband internet (>5 Mbps)
- **Impact**: Poor audio quality or disconnects if connection unstable

**ASSUME-002: Microphone Access**
- **Assumption**: Users grant microphone permission and have working mic
- **Impact**: Cannot use training mode without microphone

**ASSUME-003: English Language**
- **Assumption**: All training content in English
- **Future**: Localization not planned (single language system)

**ASSUME-004: Desktop Primary Device**
- **Assumption**: Most training sessions conducted on desktop/laptop
- **Impact**: Mobile experience de-prioritized

---

## 9. Open Questions & Risks

### 9.1 Open Questions

**Q-001: Acceptable False Positive Rate**
- **Question**: What % of incorrect technique credits is acceptable?
- **Options**: 5% (strict), 10% (balanced), 15% (lenient)
- **Impact**: Affects coach analyzer prompt tuning and evaluation criteria

**Q-002: Product Catalog Depth**
- **Question**: Should coach reference real Ashley SKUs or generic placeholders?
- **Options**: Real SKUs (requires catalog integration), Generic (simpler, less realistic)
- **Impact**: RAG implementation complexity and hint specificity

**Q-003: Financing Complexity**
- **Question**: Should system simulate actual payment calculations?
- **Options**: Real calculations (complex), Conceptual (simpler)
- **Impact**: Realism vs implementation effort

**Q-004: Session Length**
- **Question**: Is 30-minute timeout sufficient for advanced practice?
- **Options**: 30 min (current), 45 min, 60 min, configurable
- **Impact**: Infrastructure cost (longer sessions = more API usage)

**Q-005: Evaluation Criteria**
- **Question**: Optimize for strict accuracy or learning encouragement?
- **Options**: Strict (harder to pass), Lenient (easier, more motivating)
- **Impact**: User satisfaction vs skill rigor

---

### 9.2 Technical Risks

**RISK-TECH-001: Gemini API Stability**
- **Risk**: Live API in preview may have reliability issues
- **Probability**: Medium
- **Impact**: High (sessions crash or fail to start)
- **Mitigation**: Implement comprehensive error handling, fallback to text mode (future)

**RISK-TECH-002: WebSocket Reliability**
- **Risk**: Network instability causes frequent disconnects
- **Probability**: Medium
- **Impact**: Medium (user frustration, incomplete sessions)
- **Mitigation**: Auto-reconnection, state persistence, graceful degradation

**RISK-TECH-003: Transcription Accuracy**
- **Risk**: Gemini transcription misses technical vocabulary (product names, Ashley terms)
- **Probability**: High
- **Impact**: Medium (incorrect coaching, user confusion)
- **Mitigation**: Custom vocabulary injection (future), user feedback mechanism

**RISK-TECH-004: Firestore Vector Search Performance**
- **Risk**: Query latency exceeds 200ms target as document count grows
- **Probability**: Low
- **Impact**: Medium (coach hints delayed beyond 2.5s target)
- **Mitigation**: Index optimization, query caching, hybrid search

---

### 9.3 UX Risks

**RISK-UX-001: Persona Realism**
- **Risk**: AI personas feel robotic or scripted
- **Probability**: Medium
- **Impact**: High (users disengage, training perceived as ineffective)
- **Mitigation**: User testing with real sales reps, prompt refinement

**RISK-UX-002: Grading Fairness**
- **Risk**: Users perceive evaluation as unfair or inconsistent
- **Probability**: Medium
- **Impact**: High (trust in system lost)
- **Mitigation**: Transparent scoring criteria, appeal process (future), qualitative feedback

**RISK-UX-003: Overwhelming Hints**
- **Risk**: Too many coaching hints overwhelm user during session
- **Probability**: Low
- **Impact**: Medium (cognitive overload, frustration)
- **Mitigation**: Throttle hints to max 1 per 3 turns, intervention level filtering

**RISK-UX-004: Session Abandonment**
- **Risk**: Users quit mid-session due to difficulty or technical issues
- **Probability**: Medium
- **Impact**: Medium (incomplete training, wasted API costs)
- **Mitigation**: Save progress, allow resumption (future), difficulty calibration

---

## 10. Reference Documentation

### 10.1 Business & Training

- **E.A.S.Y. Selling System** (1,146 lines): `/documentation/AshleyFurnitureEASYSellingSystem.md`
  - Complete methodology specification
  - Stage requirements, techniques, scripts
  - PBM framework, objection handling

- **Stakeholder Feedback Analysis** (520 lines): `/documentation/STAKEHOLDER_FEEDBACK_ANALYSIS.md`
  - Legacy system limitations
  - Current system improvements
  - User pain points and solutions

---

### 10.2 Technical Documentation

- **API Specification** (527 lines): `/documentation/API_SPECIFICATION.md`
  - REST endpoint contracts
  - WebSocket protocol
  - Error handling, rate limits

- **Database Schema** (609 lines): `/documentation/DATABASE_SCHEMA.md`
  - Firestore collections
  - Entity relationships
  - Indexes and query patterns

- **Agent Flow** (214 lines): `/documentation/AGENT_FLOW.md`
  - Step-by-step conversation processing
  - State management across turns
  - Dual-agent coordination

- **RAG Integration Plan** (658 lines): `/documentation/RAG_INTEGRATION_PLAN.md`
  - Firestore vector search setup
  - PDF processing pipeline
  - Product-aware coaching

- **RAG Phase 1 Implementation**: `/documentation/RAG_PHASE_1_IMPLEMENTATION.md`
- **RAG Phase 2 Implementation**: `/documentation/RAG_PHASE_2_IMPLEMENTATION.md`
- **RAG Phase 3 Implementation**: `/documentation/RAG_PHASE_3_IMPLEMENTATION.md`

---

### 10.3 Implementation Guides

- **Backend Migration Plan**: `/documentation/BACKEND_MIGRATION_PLAN.md`
  - Architecture decisions
  - Migration from legacy system

- **Admin Dashboard**: `/documentation/ADMIN_DASHBOARD.md`
  - Metrics and monitoring
  - Manager view features

- **Admin Troubleshooting**: `/documentation/ADMIN_TROUBLESHOOTING.md`
  - Common issues and resolutions

- **Terraform Infrastructure**: `/documentation/TERRAFORM_INFRASTRUCTURE.md`
  - GCP resource configuration
  - Deployment automation

- **Setup Checklist**: `/documentation/SETUP_CHECKLIST.md`
  - Environment setup
  - Deployment steps

- **Session State Resumption**: `/documentation/SESSION_STATE_RESUMPTION.md`
  - Reconnection handling
  - State persistence

---

### 10.4 Codebase References

**Backend (Python):**
- **Main App**: `/backend/app/main.py`
- **Agents**: `/backend/app/agents/` (customer_agent.py, coach/, personas.py, state.py, prompts.py)
- **Services**: `/backend/app/services/` (gemini_service.py, coach_agent_service.py, customer_agent_service.py, rag_service.py)
- **API Routes**: `/backend/app/api/` (auth.py, sessions.py, personas.py, admin.py, ws/gemini_relay.py)
- **Data**: `/backend/app/data/` (easy_system.py, objections.py)
- **Models**: `/backend/app/models/` (session.py, evaluation.py, transcript.py, user.py, coach.py)
- **Repositories**: `/backend/app/repositories/` (session_repository.py, evaluation_repository.py, transcript_repository.py, user_repository.py)

**Frontend (TypeScript/React):**
- **Main App**: `/gstudio_ts/App.tsx`
- **Components**: `/gstudio_ts/components/`
- **Services**: `/gstudio_ts/services/`

---

## Appendix A: Glossary

**E.A.S.Y. Selling System**: Ashley Furniture's proven 4-stage sales methodology (Engage, Ask, Show, Yes)

**PBM (Personal Buying Motivator)**: The underlying emotional/practical reasons driving a customer's purchase decision (e.g., durability, style, budget)

**Persona**: AI customer archetype with backstory, needs, objections, and behavioral traits

**Coach Agent**: AI service that analyzes salesperson technique and generates hints

**Customer Agent**: AI service that simulates customer persona behavior

**LangGraph**: Framework for building stateful AI agents with conversation memory

**RAG (Retrieval-Augmented Generation)**: Technique combining vector search with LLM generation for product-aware coaching

**Gemini Live API**: Google's real-time voice conversation API (WebSocket-based)

**Firestore**: Google Cloud NoSQL database with vector search capabilities

**JWT (JSON Web Token)**: Authentication token format containing user claims

**WebSocket**: Bidirectional communication protocol for real-time audio streaming

**ADS Model**: Objection handling framework (Acknowledge, Discover, Solve)

**Layer 2 Discovery**: Follow-up questions asking "why" to uncover deeper customer motivations

**Clear the Constraint**: Technique to identify real objections (Confirm → Clarify → Commit)

**Power Demonstration**: Showing 3 products across Good/Better/Best tiers with physical interaction

**Pay Your Way**: Presenting 3 payment options (Lowest Monthly, Lowest Price, Best of Both)

---

## Appendix B: Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-19 | Engineering Team | Initial PRD created from existing documentation |

---

**End of Document**

*This PRD is the authoritative functional and technical specification for Luxe Sales Coach v2. Changes require approval from Product and Engineering leadership.*
