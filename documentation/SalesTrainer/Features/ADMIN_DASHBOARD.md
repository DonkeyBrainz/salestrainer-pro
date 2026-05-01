---
tags: [#features, #admin, #dashboard]
---

# Admin Dashboard

## Overview
Admin-only dashboard for monitoring persona authenticity, user activity, and system metrics.

**Access:** Restricted to admin user only (miklpuerto69@gmail.com)

**URL:** `/admin`

---

## Features

### 1. Persona Metrics Tab

**Tracks persona authenticity through "volunteer behavior" scoring:**

#### Metrics Tracked
- **Volunteer Score:** How much information personas volunteer unprompted (0-2+ scale)
- **First Message Volunteer Rate:** % of sessions where persona volunteers info in first message
- **Sessions Count:** Number of sessions for each persona
- **Message Count:** Total customer messages
- **Sales Mode Violations:** (Future) Count of inappropriate salesperson behaviors

#### Expected Behavior
- **High Regard Personas** (eager_newlywed): Score ~1.0-1.5
  - Volunteers name, needs, budget, personal details unprompted
  - 100% first message volunteer rate

- **Medium Regard Personas** (busy_parent, skeptical_shopper): Score ~0.5-0.7
  - Volunteers some info (usually name) but guarded
  - 60-100% first message volunteer rate

- **Low Regard Personas** (price_resistant, demanding_professional): Score ~0.2-0.4
  - Very reserved, minimal volunteering
  - 20-40% first message volunteer rate

#### Displays
1. **By Difficulty Table**
   - Volunteer scores grouped by regard level
   - Validates 7x difference between high and low regard

2. **By Persona Table**
   - Individual persona performance
   - Sorted by volunteer score (high to low)
   - Color-coded scores:
     - Green (>1.0): High volunteering
     - Yellow (0.5-1.0): Medium volunteering
     - Red (<0.5): Low volunteering

### 2. User Metrics Tab

**Tracks user engagement and testing patterns:**

#### Metrics Tracked
- **Total Sessions:** All sessions created by user
- **Total Transcripts:** Sessions with captured conversations
- **Total Messages:** All messages exchanged
- **Avg Messages/Session:** Engagement depth
- **Avg Session Duration:** Time spent per session
- **Session Breakdown:** Training vs Evaluation counts
- **Persona Usage:** Which personas each user practices with
- **Last Active:** Most recent session timestamp

#### Summary Cards
- **Total Users:** All registered users
- **Active (7d):** Users with sessions in last 7 days
- **Active (30d):** Users with sessions in last 30 days

#### User Table
Sorted by total sessions (most active first):
- User name and email
- Session and transcript counts
- Average engagement metrics
- Last active date

---

## API Endpoints

### GET `/api/v1/admin/personas/metrics`

**Auth:** Requires admin access (Bearer token)

**Response:**
```typescript
{
  totalSessions: number;
  totalTranscripts: number;
  byPersona: Array<{
    personaId: string;
    sessions: number;
    messageCount: number;
    volunteerScore: number;
    firstMessageVolunteerRate: number;
    salesModeViolations: number;
    volunteerCategories: Record<string, number>;
  }>;
  byDifficulty: Array<{
    difficulty: string;
    sessions: number;
    messageCount: number;
    volunteerScore: number;
    firstMessageVolunteerRate: number;
  }>;
}
```

### GET `/api/v1/admin/users/metrics`

**Auth:** Requires admin access (Bearer token)

**Response:**
```typescript
{
  totalUsers: number;
  activeUsers7d: number;
  activeUsers30d: number;
  users: Array<{
    userId: string;
    userName: string;
    userEmail: string;
    totalSessions: number;
    totalTranscripts: number;
    totalMessages: number;
    avgMessagesPerSession: number;
    avgSessionDurationMinutes: number;
    sessionBreakdown: Record<string, number>;
    personaUsage: Record<string, number>;
    lastActive: string | null;
  }>;
}
```

---

## Access Control

### Backend
**File:** `backend/app/api/admin.py`

```python
ADMIN_EMAILS = [
    "miklpuerto69@gmail.com",
]

async def require_admin(user: User) -> User:
    """Verify user has admin privileges."""
    if user.email not in ADMIN_EMAILS:
        raise ForbiddenError("Admin access required")
    return user
```

### Frontend
**File:** `frontend/src/components/UserMenu.tsx`

Admin button only visible to users with email in `ADMIN_EMAILS` list.

---

## Volunteer Behavior Scoring

### What It Measures
How much information customers share **without being prompted** by the salesperson.

### Scoring Categories
1. **Name** - "I'm Sarah", "My name is..."
2. **Needs** - "I'm looking for", "I need..."
3. **Personal Details** - "My husband and I...", "We just moved..."
4. **Budget** - "Between $2000-4000", "Under $600"
5. **Enthusiasm** - "So excited!", exclamation marks
6. **Timeline** - "Need it by next week", "No rush"
7. **Preferences** - "I love...", "Important to us..."

### Calculation
- Each volunteered category adds +1 to message score
- Average score across all customer messages = Volunteer Score
- First message volunteer rate = % of sessions where first message has score >0

### Example Scores

**High Regard (eager_newlywed):**
> "Hi there! I'm Maria. My husband and I just moved into our first apartment, and we're looking for a living room set - specifically a sofa and coffee table. We're hoping to stay between $2,000 to $4,000!"

**Categories:** name, personal, needs, budget, enthusiasm = **5 points**

**Low Regard (price_resistant):**
> "It feels alright, I guess. But I'm sure it's way over my budget."

**Categories:** budget = **1 point** (guarded, no name, no specifics)

---

## Usage

### Accessing the Dashboard

1. **Log in** to the app with an admin email
2. **Click "Admin" button** in the user menu (top right)
3. **View metrics** across two tabs:
   - Persona Metrics
   - User Metrics

### Interpreting Persona Metrics

**✅ Good Signs:**
- High regard personas: Score >1.0, 100% first msg rate
- Low regard personas: Score <0.5, <50% first msg rate
- 5-7x difference between high and low regard
- No sales mode violations

**⚠️ Warning Signs:**
- All personas scoring similarly (no differentiation)
- Low regard personas scoring >1.0 (too friendly)
- High regard personas scoring <0.5 (too reserved)
- Sales mode violations >0 (personas acting like salespeople)

### Interpreting User Metrics

**✅ Engaged Users:**
- Multiple sessions per week
- Avg >10 messages per session
- Avg duration >2 minutes
- Testing multiple personas

**⚠️ Struggling Users:**
- Many sessions but low message counts (restarting frequently)
- Short durations (<1 minute)
- Only testing easy personas (avoiding challenges)
- Zero transcripts despite many sessions (technical issues)

---

## Technical Implementation

### Backend Stack
- **FastAPI** - REST API endpoints
- **Firestore** - Data queries (sessions, transcripts, users)
- **Pydantic** - Request/response models
- **Python regex** - Pattern matching for volunteer detection

### Frontend Stack
- **React + TypeScript** - UI components
- **React Router** - /admin route
- **Tailwind CSS** - Styling
- **Lucide React** - Icons

### Files Created/Modified

**Backend:**
- `app/api/admin.py` (NEW) - Admin endpoints
- `app/main.py` - Added admin router

**Frontend:**
- `pages/AdminPage.tsx` (NEW) - Admin dashboard UI
- `components/UserMenu.tsx` - Added admin button
- `App.tsx` - Added /admin route

**Scripts:**
- `scripts/analyze_volunteer_behavior.py` - CLI tool for detailed analysis
- `scripts/detect_sales_mode_customers.py` - CLI tool for violation detection
- `scripts/sample_customer_messages.py` - CLI tool for quality sampling

---

## Future Enhancements

### Near-term
1. **Real-time sales mode violation detection**
   - Currently returns 0 for all personas
   - Implement pattern matching in backend

2. **Charts and visualizations**
   - Volunteer score trends over time
   - User activity heatmaps
   - Persona usage pie charts

3. **Export functionality**
   - Download metrics as CSV/JSON
   - Generate PDF reports

### Medium-term
4. **Drill-down views**
   - Click persona → See all sessions for that persona
   - Click user → See detailed user timeline
   - Click session → View full transcript

5. **Alerts and notifications**
   - Email when volunteer scores drift out of range
   - Slack notification for sales mode violations
   - Weekly summary reports

6. **A/B testing dashboard**
   - Compare persona versions
   - Test new difficulty behaviors
   - Measure impact of prompt changes

### Long-term
7. **ML-based anomaly detection**
   - Auto-detect when personas behave inconsistently
   - Flag unusual user patterns
   - Predict engagement drop-off

8. **Custom metrics builder**
   - Define custom patterns to track
   - Create custom scorecards
   - Build custom reports

---

## Maintenance

### Updating Admin Emails

**Backend:** `backend/app/api/admin.py`
```python
ADMIN_EMAILS = [
    "miklpuerto69@gmail.com",
    "user@example.com",
    # Add new admin emails here
]
```

**Frontend:** `frontend/src/components/UserMenu.tsx`
```typescript
const ADMIN_EMAILS = [
  'miklpuerto69@gmail.com',
  // Add new admin emails here
];
```

### Adding New Metrics

1. **Add to backend response model** (`app/api/admin.py`)
2. **Calculate metric** in endpoint function
3. **Add to frontend types** (`pages/AdminPage.tsx`)
4. **Display in UI** (table column or card)

### Troubleshooting

**403 Forbidden Error:**
- Verify user email is in ADMIN_EMAILS list (both backend and frontend)
- Check auth token is valid
- Ensure user is logged in

**No data showing:**
- Check if sessions exist in Firestore
- Verify transcripts are being created
- Check browser console for API errors

**Slow loading:**
- Metrics query all sessions/transcripts from Firestore
- Consider pagination for large datasets
- Add caching layer if needed

---

## Security Considerations

1. **Email-based access control**
   - Simple but effective for small team
   - Consider role-based access control (RBAC) for scale

2. **No sensitive data exposure**
   - User emails shown (already known to admin)
   - No passwords or auth tokens exposed
   - Transcript content not shown in list view

3. **API authentication**
   - All endpoints require valid JWT token
   - Admin check happens on server side
   - Frontend check is just for UI (security enforced in backend)

4. **Rate limiting** (Future)
   - Add rate limiting to admin endpoints
   - Prevent abuse from compromised admin account

---

## Related Documentation

- `documentation/LRIGGS_TESTING_ANALYSIS.md` - Example analysis using these metrics
- `scripts/analyze_volunteer_behavior.py` - CLI version of persona metrics
- `scripts/detect_sales_mode_customers.py` - Sales mode violation checker
- `backend/app/api/admin.py` - Backend implementation
- `frontend/src/pages/AdminPage.tsx` - Frontend implementation
