# Handoff: Voiceprint Direction — SalesTrainer Voice-First Coaching UI

## Overview

**Voiceprint** is a voice-first trainer interface for SalesTrainer, framing training modes and dashboards as rooms in a blueprint-style floor plan. The design anchors the AI coaching metaphor in spatial navigation: agents navigate a training "building" to select coaching modes (Live Practice, Performance Assessment), review session archives, and access manager/admin dashboards.

The core innovation is treating the app as a real-estate floorplan — a visual metaphor that works because SalesTrainer trains real estate agents. Every customer persona gets a hand-drawn room-plan sketch (unique to their profile), and high-stakes sessions are treated as "confidential dossiers" with redacted subject details until grading is complete.

## About the Design Files

The files in this bundle are **high-fidelity HTML prototypes** showing the intended look, layout, typography, colors, and interactions. These are **not production code** — they are design references created to explore the Voiceprint direction.

**Your task:** Implement these designs in your target codebase (React, Vue, native, etc.) using your framework's established patterns, component libraries, and design system. Treat the HTML prototypes as pixel-perfect mockups to recreate, not code to copy directly.

## Fidelity

**High-fidelity (hifi)**: All designs are pixel-perfect mockups with final colors, typography, spacing, and interactive states fully specified. Recreate them in your codebase's framework using the exact dimensions, colors, and behavior described below.

## Screens / Views

### 1. Lobby (Floor Plan)
**Purpose:** Entry point. User sees a blueprint-style floor plan with five clickable rooms representing training modes.

**Layout:**
- Page: 1280×820px
- SVG floor plan (940×640 viewBox) centered, containing 5 rooms
- Right sidebar: 250px wide, C.O.R.E. mastery strip + sticky note
- Header: brand title, subtitle, time greeting, avg score stat
- Bottom/right: dimension lines showing scale (64'-0" × 41'-0")

**Rooms:**
- RM01 (top-left): LIVE PRACTICE — coached conversation with mood/score feedback
- RM02 (top-right): PERFORMANCE ASSESSMENT — unassisted graded conversation
- RM03 (bottom-left): SESSION ARCHIVE — transcripts + scorecards (30-day log)
- RM04 (bottom-center): MANAGER OFFICE — team roster dashboard
- RM05 (bottom-right): ADMIN WING — regional survey (3 regions, 12 stores, 83 agents)

**Styling:**
- SVG walls: stroke #FFF, stroke-width 2.5px
- Room fills: transparent, hover rgba(255,255,255,0.07)
- Room text: names in Anton 23px, subs in IBM Plex Mono 10px
- Furniture: stroke rgba(255,255,255,0.35), 1px (visual noise)
- C.O.R.E. strip: 4 cells, bg rgba(255,255,255,0.045), border 1px var(--line-faint)
- Sticky note: bg #CFE6A8, color #2C3B1E, 190px wide, rotated -4deg, shadow 3px 4px 10px rgba(0,0,0,0.3)

**Interactions:**
- RM01 click → Persona Draft (mode: "live")
- RM02 click → Persona Draft (mode: "assess")
- RM03 click → Session Archive
- RM04 click → Manager Office
- RM05 click → Admin Wing

### 2. Persona Draft
**Purpose:** Select which customer persona to practice with.

**Layout:**
- 1280×820px
- Header with back nav, title "SELECT A CUSTOMER TO DRAFT", avg score stat
- Main: horizontal scrolling card row (7 cards, 196px wide each)
- Cards staggered: rotate(-1deg), rotate(0.7deg translateY(3px)), rotate(-0.4deg translateY(-2px))

**Card Structure:**
- Border: 7px solid; color by regard:
  - High (Marcus): #8FBF6B (--rapport)
  - Medium (Jennifer, Amanda, Alex, Thomas): #7EB0EE (--standard)
  - Low (Diane, Ray): #E4574A (--hard)
- Padding: 14px, bg rgba(6,20,40,0.72), shadow 0 10px 24px rgba(0,0,0,0.4)
- Tier tab: positioned top-left (-21px), rotated -2deg, colored bg matching regard tier
- Content: name (Anton 24px, text-shadow), mini-plan SVG (unique per persona), meta (role + line, 9.5px), footer (best score / "NEW" + difficulty pips)

**Personas:**
1. Marcus — High, difficulty 1, best 91, contractor/renovation sketch
2. Jennifer — Medium, difficulty 2, best 78, first-time buyer sketch
3. Amanda — Medium, difficulty 2, best none, relocating-with-kids sketch
4. Alex — Medium, difficulty 2, best 64, urban loft sketch
5. Thomas — Medium, difficulty 2, best none, hobby-farm sketch
6. Diane — Low, difficulty 3, best 55, downsizing sketch
7. Ray — Low, difficulty 3, best none, duplex-investor sketch

**Mini-plan SVGs:** Each is a unique 120×80 architectural sketch (SVG, hand-drawn style) reflecting the persona's housing situation. See HTML for exact paths.

**Interactions:**
- Hover card: scale up, glow
- Click card: set currentPersona, navigate to Live Practice OR Assessment (based on sessionMode)

### 3. Live Practice
**Purpose:** Real-time coached conversation with a customer persona.

**Layout:**
- 1280×820px
- Header: "LIVE PRACTICE" title, persona name/role/regard, time counter ("t+ 02:14")
- 3-column body (250px / flex-1 / 250px):
  - **Left:** C.O.R.E. phases panel (5 items, one marked "on") + Live score (72 / 100, +8 delta)
  - **Center:** Speaking tag, speaker-unit canvas (300×300), transcript quote, hint text, controls
  - **Right:** Mood track (gradient bar), sticky note coach tip, "Watch for" objections panel

**Panels:**
- bg var(--blue-panel) / rgba(255,255,255,0.045)
- border 1px var(--line-faint), padding 13–15px
- Title: 9.5px uppercase, colored dot indicator

**C.O.R.E. Phases:**
- 5 rows (C, O, R, E + one extra or grouped), only C marked "on" (opacity 1, others 0.45)
- Each: letter (Anton 14px), name (Oswald 12px uppercase), progress "X/3" (10px)
- Dashed dividers between rows

**Live Score:**
- Big number: 38px Anton "72"
- "/ 100" (11px muted)
- Delta: 13px Oswald, color var(--rapport), "+8 ▲"

**Speaker-Unit Canvas:**
- Size: 300×300px ideal, fills live-frame
- Renders via requestAnimationFrame
- Layers: rounded box outline, corner dots, 5 concentric dot rings, central cone, 5 LED lights at bottom
- No wave arcs — pure LED-based visualization
- Energy-driven: LEDs light proportional to voice energy
- Resize on-demand: if canvas.width === 0 in frame loop, call resize()

**Transcript:**
- Centered, max 560px
- Quote: 18px Oswald, line-height 1.5
- <em> tags: color var(--amber), font-style normal
- Hint: 10px uppercase, muted, margin-top 10px

**Controls (live-controls):**
- Initial: "▸ Begin session" visible; Mute, Hint, End hidden
- After Begin: Begin hidden; Mute, Hint, End visible
- Mute: toggles "🎤 Mute" ↔ "🔇 Unmute"; on mute, bg color changes to var(--hard)
- Hint: pulses sticky note (0.8s stickyPulse animation, 2 iterations)
- End: resets all state, goes to Lobby

**Mood Track:**
- Height 6px, bg var(--line-faint)
- Gradient fill (left→right): hard → amber → rapport
- Pin: 1px wide, 14px tall, at 62% left

**Interactions:**
- Begin click → setListening(true), show Mute/Hint/End
- Mute toggle → setListening(false), change tag + button state
- Hint click → remove/re-add .pulse class on sticky note
- End click → resetSession(), go('home')

### 4. Performance Assessment
**Purpose:** Unassisted graded conversation. Subject identity withheld; no coaching, no live score, no transcript.

**Layout:**
- Same 3-column structure as Live Practice
- Header: "PERFORMANCE ASSESSMENT" title, case file line (Case file VP-2214 · Subject [redacted] · Scenario [redacted]), red "CONFIDENTIAL · NO COACHING" stamp

**Left Column (Subject Dossier):**
- Panel with red dot title "Subject dossier"
- 4 rows of redaction bars (Name, Profile, Regard, Objections)
- Footer: "Declassified after grading" (9px muted)

**Redact Styling:**
- bg rgba(10,16,26,0.92), color transparent
- border 1px dashed var(--line-dim), border-radius 1px
- box-shadow 0 0 0 1px rgba(255,255,255,0.08)
- user-select none

**Center:**
- Speaking tag says only "Subject" (no name)
- Transcript is blurred: `<div class="blur-line">The subject's words are withheld...</div>`
- blur-line: filter blur(5px), opacity 0.75, user-select none, pointer-events none
- Controls: Begin, Mute, End & grade (no Hint button)

**Right Column:**
- Sealed panel: "SEALED" (22px Anton, muted) + note about reveal after grading
- Rules panel: "No hints · no transcript · no live score. Subject identity withheld. One take, graded end-to-end against C.O.R.E."

**Results View (after End & grade):**
- Green "Declassified · case file VP-2214" stamp
- Big score (72px Anton, text-shadow)
- Subtitle: persona name + "assessment" + duration
- 4-cell grid: C/O/R/E grades (color-coded)
- Sticky note: coach's observation
- 3 buttons: "↺ Run it again", "File in archive ▸", "Lobby"

**Interactions:**
- Begin → show Mute, End & grade
- Mute → same behavior as Live Practice
- End & grade → hide assessRun, show assessResults (no navigation)
- Run it again → resetAssess()
- File in archive → go('archive')
- Lobby → go('home')

### 5. Session Archive
**Purpose:** Browse past 14 sessions (30 days), click to open detailed overlay.

**Layout:**
- 1280×820px
- Header: back nav, title "SESSION ARCHIVE", subtitle "transcripts + scorecards · last 30 days"
- Main body: 2-column (flex-1 / 320px max)
  - **Main:** KPI row (3 cards: Sessions 14, Best score 91, Trend +11), session log table
  - **Side:** Selected session detail sheet (initially first row)

**KPI Cards:**
- Flex row, gap 12px
- Each: bg var(--blue-panel), border 1px var(--line-faint), padding 12px 14px
- Label (8.5px muted), value (27px Anton), sub (9.5px muted)

**Session Log Table:**
- Columns: Date | Customer | Mode | Length | Score | Δ Best
- 7 rows of data (Jul 15, 14, 12, 11, 09, 08, 05)
- Mode: badge (class "mode-tag practice" or "mode-tag assess")
- Score: 17px Anton, color-coded (rapport ≥80, amber ≥65, hard <65)
- Δ: "★ best" or "+N / −N" with arrow icon (class "up" or "dn")
- Row hover: bg rgba(255,255,255,0.04)
- Row selected: bg rgba(240,162,78,0.08)

**Side Detail Sheet:**
- Scorecard header: date + mode badge, score (44px Anton), name + length (10px muted)
- Quote: 12.5px Oswald, border-left 2px, padding-left 12px, italic-style text
- Coach note: 10.5px muted, line-height 1.7

**Interactions:**
- Click table row → mark selected, render side detail, open overlay with full data

### 6. Session Detail Overlay
**Purpose:** Full session replay: transcript, grades, hints timeline, coach note.

**Layout:**
- Fixed position overlay
- Backdrop: rgba(4,10,20,0.88), blur(4px), opacity 0 → 1
- Sheet (dark blue gradient, max 880px width, scrollable):
  - Close button (top-right, "CLOSE ✕")
  - Header: title (name + date), meta (badges + mood + delta), score (right)
  - Two-column body: transcript (left) | grades + hints + note (right)

**Header:**
- Title: 30px Anton, uppercase
- Meta: 10px uppercase, flex row (Mode badge, length, mood, delta)
- Score: 58px Anton, right-aligned, color-coded

**Transcript Column:**
- Title: "Transcript — key exchange SHEET T-[DATE]" (9.5px sec-title bar)
- Turns: flex rows with "Who" label (64px wide, 8.5px uppercase) + quoted speech (12px, line-height 1.6)
- Turn classes: ao-turn agent (color var(--standard)) or ao-turn cust (color var(--amber))
- <mark> tags: bg rgba(240,162,78,0.22), color var(--amber), padding 0 3px

**Right Stack:**
1. C.O.R.E. Grades: 4 cells in flex row (letter, grade 24px, label)
2. Hints Used: section with count; each hint shows timestamp + tip text
   - Or: "Hints unavailable — assessment room" / "Ran clean — no hints requested"
3. Coach Note: sticky note (rotated 1.2deg)

**Animations:**
- Backdrop: opacity 0 → 1 over 0.25s ease
- Sheet: transform translateY(24px) rotate(-0.4deg) → translateY(0), opacity 0 → 1, over 0.3s cubic-bezier(0.2, 0.9, 0.3, 1.1)
- Close: Esc key, backdrop click, or button click

### 7. Manager Office
**Purpose:** Team roster ranked by score, flags for at-risk agents.

**Layout:**
- 1280×820px
- Header: back nav, title, subtitle (store + manager), scribble
- 2-column body (flex-1.5 / 320px):
  - **Main:** KPI row (3 cards), team roster table
  - **Side:** Stack of sticky notes (3 flags + 1 bright spot)

**KPI Row:**
- "Team avg" (71, amber)
- "At risk" (3, red)
- "Store rank" (9/12)

**Team Roster Table:**
- Columns: # | Agent | Score | C·O·R·E | Δ Week | Flag
- 7 rows (Priya, Jordan, Malik, Casey, Devon, Elena, Trevor)
- Score: 17px, color-coded
- C·O·R·E bar: 76px width, fill = avg(4 core scores) / 100
- Δ: "up" or "dn" class (arrow icon, colored)
- Flag: ⚑ symbol (red) if flagged

**Sticky Notes (side):**
- 4 total: 3 red flags (Casey, Elena, Trevor) + 1 bright spot (Malik, lighter bg)
- Each with st-title ("Flag · [name]" or "Bright spot ✓"), rotated 1.5–2.5deg
- Shadow 3px 4px 10px rgba(0,0,0,0.3)

### 8. Admin Wing
**Purpose:** Regional survey: 3 regions (NC, SC, TX), 12 stores, 83 agents.

**Layout:**
- 1280×820px
- Header: back nav, title, subtitle (all regions), scribble
- 2-column body (flex-1.5 / 320px):
  - **Main:** Region cards (3-column), store rollup table
  - **Side:** Top performers + Needs attention tables

**Region Cards:**
- 3-column flex, gap 12px
- Each: bg var(--blue-panel), border-top 3px (NC: var(--rapport), SC: var(--amber), TX: var(--hard))
- Name (11px uppercase), score (30px Anton), bar chart (7 bars, varied heights), sub (9px)

**Store Rollup Table:**
- Columns: # | Store | Manager | Agents | Score | Δ
- 12 rows (Houston, Raleigh, Charleston, etc.)
- Score: 17px, color-coded
- Region color on manager row

**Side Tables:**
- "Top performers" (5 rows)
- "Needs attention" (5 rows)
- Both: compact, 11.5px text

---

## Interactions & Behavior

### Navigation
- Lobby ↔ Persona Draft ↔ Live/Assess
- Persona Draft ↔ Archive
- All pages have back nav to Lobby
- Archive → Overlay (no page change, modal)

### Button States (Live / Assessment)
- Initial: Begin visible, Mute/Hint/End hidden
- After Begin: Begin hidden, Mute/Hint/End visible
- Mute: toggles text + class (changes bg to hard on muted)
- Hint: pulses sticky note
- End: reset state, go home

### Speaker Canvas
- Continuous frame loop (requestAnimationFrame)
- Resize detection: if canvas.width === 0 && rect.width > 0, call resize()
- Energy bursts: 0.25–0.65 when listening, 0.04 when muted
- Burst pattern: every 0.35–0.75s listening, 0.9–2.0s idle

### Overlay
- Click row → openOverlay(session)
- Backdrop/Esc close
- Sheet scrolls if overflow

---

## State Management

### Global
- currentPersona: string (persona name)
- sessionMode: "live" or "assess"
- muted: boolean
- pages: { home, personas, live, assess, archive, manager, admin }

### Page-specific
- Live: C.O.R.E. progress (C on, others off), mood position (62%), time
- Archive: selected row, overlay open/closed
- Results: score + grades (hardcoded for demo)

---

## Design Tokens

### Colors
- --blue: #2058A6
- --blue-deep: #123157
- --blue-panel: rgba(255,255,255,0.045)
- --text: #EFF5FF
- --text-muted: rgba(239,245,255,0.6)
- --amber: #F0A24E
- --rapport: #8FBF6B (high regard)
- --standard: #7EB0EE (medium)
- --hard: #E4574A (low)
- --special: #C79BEE
- --sticky: #CFE6A8
- --sticky-ink: #2C3B1E
- --line: #FFFFFF
- --line-dim: rgba(255,255,255,0.35)
- --line-faint: rgba(255,255,255,0.10)

### Typography
- **Anton**: titles, scores (no weights)
- **Caveat**: scribbles, handwriting (500, 600)
- **Oswald**: labels, badges (500, 600)
- **IBM Plex Mono**: body, details (400, 500)

Sizes: 8.5px–72px, letter-spacing 0.01–0.24em

### Spacing & Sizing
- Viewport: 1280×820px (desktop)
- Card: 196px wide
- Sidebar: 250–320px
- Padding: 12–16px
- Gap: 8–20px

### Shadows & Borders
- Sticky notes: 3px 4px 10px rgba(0,0,0,0.3)
- Overlay: 0 24px 70px rgba(0,0,0,0.6), 0 0 0 1px rgba(0,0,0,0.4)
- Text glow: text-shadow 0 0 24px rgba(255,255,255,0.25)

### Animations
- Standard: 0.25s ease
- Overlay: 0.3s cubic-bezier(0.2, 0.9, 0.3, 1.1)
- Pulse: 0.8s stickyPulse, 2 iterations

---

## Assets

### Fonts (Google Fonts)
- Anton, Caveat (500/600), Oswald (500/600), IBM Plex Mono (400/500)

### SVG Assets
- 7 persona mini-plan sketches (120×80 viewBox each, unique architectural drawings)
- 1 lobby floor plan (940×640 viewBox)
- All custom SVG paths; no external image files

---

## Files in This Bundle

- **Voiceprint Direction.html** — Full desktop design (8 pages, all interactive)
- **Voiceprint Mobile.html** — Mobile variant (3 pages: Lobby, Persona Draft, Live Practice only)

Both are standalone HTML files with embedded CSS and JavaScript. Use them as pixel-perfect reference mockups.

---

## Implementation Checklist

- [ ] Lobby floor plan (SVG layout, room clickability)
- [ ] Persona cards (7 sketches, selection logic)
- [ ] Live Practice page (speaker canvas, controls, panels)
- [ ] Performance Assessment (redaction styling, results scorecard)
- [ ] Session Archive (table, side detail sheet)
- [ ] Session overlay (modal, transcript, grades, hints)
- [ ] Manager Office dashboard (KPI, roster table, flags)
- [ ] Admin Wing dashboard (regions, store table, top/bottom performers)
- [ ] Navigation (5-page router)
- [ ] Speaker canvas (resize, frame loop, energy visualization)
- [ ] Button state machine (Begin → Mute/Hint/End)
- [ ] Overlay animation (enter/exit, backdrop)
- [ ] Responsive mobile (or separate mobile app)
