# Claims Co-Pilot — UI Implementation Spec

**Audience:** a coding agent implementing the production front end.
**Visual reference:** `concept-a4-clearline-refined.html`. Open it in a browser. When this spec and the prototype disagree, this spec wins.
**Product:** an examiner-facing workspace for auto insurance claims. It has three parts:
- a risk-sorted queue
- a per-claim Copilot (checklist + chat)
- a semi-autonomous multi-agent investigation that produces a dossier for a human decision

---

## 0. Non-negotiable principles

1. **Humans decide.** No agent output can approve, deny, or refer a claim. Only an explicit examiner action in the Decision UI can. Agents recommend.
2. **Never block.** Long-running work (checklist, investigation) renders inline with live progress. Do not use a modal or spinner that blocks the page for agent work. The only modal is the decision confirmation.
3. **Color has one meaning each:**
   - Violet (`accent`) marks what is interactive or agent-active.
   - Red, amber, and green are status only (risk level, check result).
   - Never use status colors decoratively, and never use violet for status.
4. **Lead with the conclusion.** Every claim screen shows the answer first (headline, recommendation, counts), then details.
5. **Every claim is traceable.** Every Copilot statement and dossier finding links to a source, either a checklist step or a document.
6. **Plain copy.** Use sentence case. Buttons say exactly what happens. No jokes, and no consumer-facing reassurance ("your claim is in good hands").

---

## 1. Tech assumptions

These are defaults; change them if the host repo differs.

- React 18+ with TypeScript (strict)
- Routing: React Router or the Next.js app router
- Styling: CSS variables for tokens (section 2), plus Tailwind or CSS modules
- Server state: TanStack Query. Live agent data: SSE or WebSocket (section 5).
- Font: **Instrument Sans** (400/500/600/700) with a system sans fallback
- `font-feature-settings: "tnum" 1` globally, so all numbers use tabular figures

---

## 2. Design tokens

```json
{
  "color": {
    "canvas":       "#F4F3F8",
    "surface":      "#FFFFFF",
    "ink":          "#16151D",
    "ink2":         "#3B3947",
    "muted":        "#6A6878",
    "line":         "#E5E3EC",
    "line2":        "#EFEDF4",

    "accent":       "#A100FF",
    "accentInk":    "#7500C0",
    "accentSoft":   "#F4EAFF",
    "accentLine":   "#E3D0FA",
    "accentGlow":   "#C77DFF",

    "high":         "#C22F3A",
    "highSoft":     "#FCEEEF",
    "med":          "#A2650C",
    "medSoft":      "#FBF2E2",
    "medLine":      "#F0DDB8",
    "medBar":       "#E0A43A",
    "low":          "#2F7A55",
    "lowSoft":      "#E9F5EE",
    "lowBar":       "#43B581",
    "neutralRisk":  "#A09CB0"
  },
  "gradient": {
    "hero": "radial-gradient(760px 300px at 94% -20%, rgba(184,92,255,.30), transparent 70%), radial-gradient(560px 260px at 60% -70%, rgba(255,140,210,.18), transparent 70%), linear-gradient(180deg, #FBF6FF 0%, #F2E8FF 70%, #F1ECF8 100%)",
    "heroEdge": "linear-gradient(90deg, transparent, rgba(161,0,255,.2), transparent)",
    "primaryButton": "linear-gradient(135deg, #B53DFF, #A100FF 55%, #8A00DB)",
    "userBubble": "linear-gradient(135deg, #B53DFF, #8A00DB)",
    "brandMark": "linear-gradient(140deg, #C77DFF, #A100FF 55%, #7500C0)"
  },
  "radius": { "s": 7, "m": 10, "l": 14, "pill": 999, "dialog": 16 },
  "space":  [4, 8, 12, 16, 20, 24, 28, 32, 40],
  "font": {
    "family": "\"Instrument Sans\", ui-sans-serif, -apple-system, \"Segoe UI\", system-ui, sans-serif",
    "size":   { "xs": 12, "sm": 13, "base": 14, "md": 15, "lg": 18, "xl": 22, "stat": 26 },
    "weight": { "regular": 400, "medium": 500, "semibold": 600 },
    "tracking": { "heading": "-0.02em", "subheading": "-0.01em" }
  },
  "shadow": {
    "primaryButton": "0 6px 16px -10px rgba(161,0,255,.8)",
    "focusRing":     "0 0 0 3px rgba(161,0,255,.08)",
    "liveNode":      "0 0 0 4px #F4EAFF",
    "floating":      "0 16px 40px -16px rgba(22,21,29,.5)",
    "dialog":        "0 30px 80px -20px rgba(22,21,29,.45)"
  },
  "motion": {
    "fast": "150ms ease",
    "base": "250ms ease",
    "progress": "500ms ease",
    "pulse": "1.4s ease-in-out infinite",
    "spin": "0.8s linear infinite"
  },
  "layout": {
    "sidebarWidth": 236,
    "topBarHeight": 56,
    "pageGutter": 28,
    "queuePreviewWidth": 350,
    "chatPanelWidth": 400,
    "activityPanelWidth": 400,
    "dossierAsideWidth": 330
  }
}
```

### 2.1 Color usage rules

| Use | Token | Never |
|---|---|---|
| Primary action, selected row, current nav, citations, live agent | `accent*` | Status of a claim or check |
| Risk high / check failed | `high*` | Buttons (except the outline "Refer to SIU" danger button) |
| Risk medium / check needs review / agent holding | `med*` | "Error" meaning |
| Check passed / requirement met | `low*` | Risk "low" text (use `ink2` for low-risk numbers) |
| Low risk | `neutralRisk` / `ink2` | Green (low risk is not "good", just not flagged) |

### 2.2 Typography scale

| Role | Size / weight | Notes |
|---|---|---|
| Page title (`h1`) | 22 / 600, tracking −0.02em | Claim pages: `COL-107` in 600 plus member name in 500 `ink2` |
| Section / panel title | 15 / 600 | |
| Dossier headline | 20 / 600 | max 34ch |
| Body | 14 / 400, line-height 1.45 | |
| Secondary / meta | 13 / 400 `muted` | |
| Label / pill | 12.5 / 500 | |
| Stat number | 26 / 600, tracking −0.02em | |

Do **not** use all-caps labels, letter-spaced eyebrows, or monospace for IDs.

---

## 3. Domain schema (TypeScript)

These are the source-of-truth types. Keep them in `src/types/domain.ts`.

```ts
// ---------- Primitives ----------
export type ISODate = string;          // "2025-11-24"
export type ISODateTime = string;      // "2026-01-12T02:35:17Z"
export type Money = { amount: number; currency: "USD" };  // render with Intl.NumberFormat

export type ClaimType = "collision" | "comprehensive" | "theft" | "liability" | "medical_pay";
export type RiskLevel = "high" | "medium" | "low";
export type ClaimState =
  | "new"               // nothing run yet
  | "checklist_running"
  | "checklist_done"
  | "investigating"     // agent run active
  | "dossier_ready"
  | "decided";

// Risk thresholds are the ONLY place risk level is derived
export const riskLevel = (score: number): RiskLevel =>
  score >= 70 ? "high" : score >= 35 ? "medium" : "low";

// ---------- Claim ----------
export interface Member { id: string; name: string; priorClaimCount: number; }
export interface Vehicle { year: number; make: string; model: string; acv: Money; }
export interface RepairShop { id: string; name: string; watchlisted: boolean; watchlistedSince?: ISODate; }

export interface Claim {
  id: string;                    // "COL-107"
  type: ClaimType;
  member: Member;
  vehicle: Vehicle;
  estimate: Money;
  incidentDate: ISODate;
  coverage: { start: ISODate; end: ISODate };
  shop?: RepairShop;
  riskScore: number;             // 0–100, one decimal
  rulesTriggered: number;        // "flags"
  openTasks: number;
  dueAt: ISODateTime;            // SLA deadline
  state: ClaimState;
  flagReasons: FlagReason[];     // human-readable, max 3 shown in preview
  activeInvestigationId?: string;
  dossierId?: string;
  assigneeId?: string;
}

export interface FlagReason { severity: "high" | "medium"; text: string; } // "Estimate is 1.4× the vehicle's value"

// ---------- Checklist ----------
export type CheckResult = "passed" | "review" | "failed";
export type CheckStatus = "waiting" | "running" | CheckResult;

export interface EvidenceItem { label: string; value: string; }  // { label: "Ratio", value: "1.40× (threshold 0.75×)" }
export interface SourceRef { id: string; label: string; kind: "document" | "system" | "registry" | "history"; href?: string; }

export interface ChecklistStep {
  id: string;                    // "estimate_vs_acv"
  index: number;                 // 0–6, fixed order
  title: string;                 // "Estimate vs. vehicle value"
  status: CheckStatus;
  summary?: string;              // one sentence, present once status ∈ CheckResult
  evidence?: EvidenceItem[];
  sources?: SourceRef[];
  durationMs?: number;
}

export interface ChecklistRun {
  id: string;
  claimId: string;
  startedAt: ISODateTime;
  finishedAt?: ISODateTime;
  steps: ChecklistStep[];        // always 7, in order
  counts: { passed: number; review: number; failed: number };
}

// The 7 steps, in order (titles are canonical copy):
// 0 initial_review            "Initial review"
// 1 damage_documentation      "Damage documentation"
// 2 coverage_timeline         "Coverage timeline"
// 3 estimate_vs_acv           "Estimate vs. vehicle value"
// 4 repair_shop               "Repair shop"
// 5 policy_status             "Policy status"
// 6 damage_photos             "Damage photos"

// ---------- Investigation (multi-agent) ----------
export type AgentRole = "orchestrator" | "investigator" | "case_writer" | "examiner";
export type AgentNodeStatus = "idle" | "active" | "done" | "holding" | "waiting";

export interface AgentNode {
  role: AgentRole;
  label: string;                 // "Orchestrator" | "Investigator" | "Case writer" | "You"
  purpose: string;               // "Plans the work" | "Gathers evidence" | "Tests the evidence" | "Final say"
  status: AgentNodeStatus;
  statusText: string;            // "Comparing shop invoices", "Holding: 2 gaps"
}

export interface Pass {
  number: number;                // 1-based
  summary: string;
  outcome: "complete" | "gaps" | "running";
  gapCount?: number;
}

export interface RequiredCheck { id: string; label: string; met: boolean; }  // 6 total

export interface Investigation {
  id: string;
  claimId: string;
  status: "running" | "paused" | "complete" | "stopped" | "failed";
  startedAt: ISODateTime;
  currentPass: number;
  maxPasses: number;             // 5
  nodes: [AgentNode, AgentNode, AgentNode, AgentNode]; // fixed order: orchestrator, investigator, case_writer, examiner
  passes: Pass[];
  stats: { sourcesChecked: number; findings: number; openGaps: number };
  requiredChecks: RequiredCheck[];
  loopback?: { from: "case_writer"; to: "investigator"; reason: string }; // present when last case-writer verdict was "hold"
}

// ---------- Activity stream ----------
export type ActivityEvent =
  | { kind: "agent_step";  id: string; at: ISODateTime; agent: AgentRole; text: string; current?: boolean }
  | { kind: "hold";        id: string; at: ISODateTime; agent: "case_writer"; text: string; gaps: string[] }
  | { kind: "phase";       id: string; at: ISODateTime; phase: "investigate" | "compile" | "assess"; pass: number }
  | { kind: "steer";       id: string; at: ISODateTime; text: string; appliesToPass: number }   // examiner instruction
  | { kind: "error";       id: string; at: ISODateTime; agent: AgentRole; text: string; retryable: boolean };

// ---------- Dossier ----------
export type FindingWeight = "strong" | "moderate" | "mitigating";
export interface Finding { id: string; title: string; detail: string; weight: FindingWeight; sources: SourceRef[]; }
export interface OpenItem { id: string; title: string; detail: string; action?: { label: string; kind: "draft_appraisal_request" | string }; }

export type Recommendation = "refer_to_siu" | "approve" | "deny" | "request_appraisal";

export interface Dossier {
  id: string;
  claimId: string;
  investigationId: string;
  recommendation: Recommendation;
  headline: string;              // "Likely inflated estimate through a watchlisted shop"
  summary: string;               // 1–2 sentences, conclusion first
  findings: Finding[];           // ordered strong → moderate → mitigating
  openItems: OpenItem[];
  requiredChecks: RequiredCheck[];
  passes: number;
  sourceCount: number;
}

// ---------- Decision ----------
export type DecisionAction = "approve" | "deny" | "refer_to_siu" | "request_appraisal";
export interface DecisionRequest { claimId: string; action: DecisionAction; note?: string; } // note REQUIRED for deny, refer_to_siu
export interface DecisionResult { id: string; claimId: string; action: DecisionAction; at: ISODateTime; undoableUntil: ISODateTime; }

// ---------- Copilot chat ----------
export interface Citation { label: string; target: { kind: "check"; stepIndex: number } | { kind: "source"; source: SourceRef }; }
export type ChatPart = { type: "text"; text: string } | { type: "cite"; citation: Citation } | { type: "context_card"; title: string; rows: { label: string; value: string }[] };
export interface ChatMessage { id: string; role: "user" | "copilot"; parts: ChatPart[]; at: ISODateTime; feedback?: "helpful" | "not_helpful"; }
```

---

## 4. REST endpoints (expected)

| Method | Path | Returns | Used by |
|---|---|---|---|
| GET | `/claims?range=today\|week\|all&type=&risk=&sort=risk_desc` | `{ items: Claim[], total: number, counts: Record<RiskLevel, number> }` | Queue |
| GET | `/claims/:id` | `Claim` | All claim pages |
| POST | `/claims/:id/checklist-runs` | `ChecklistRun` (status running) | Run checklist |
| GET | `/claims/:id/checklist-runs/latest` | `ChecklistRun` | Copilot page |
| POST | `/claims/:id/investigations` | `Investigation` | Start investigation |
| POST | `/investigations/:id/pause` / `resume` / `stop` | `Investigation` | Hero actions |
| POST | `/investigations/:id/steer` `{ text }` | `ActivityEvent (steer)` | Steer input |
| GET | `/dossiers/:id` | `Dossier` | Dossier page |
| POST | `/claims/:id/decisions` | `DecisionResult` | Decision dialog |
| DELETE | `/decisions/:id` | 204 | Undo (only before `undoableUntil`) |
| POST | `/claims/:id/chat` `{ text }` | stream of `ChatPart` | Copilot chat |
| POST | `/claims/bulk/checklist-runs` `{ claimIds }` | `{ runIds }` | Queue bulk bar |

---

## 5. Live event contract (SSE or WebSocket)

Channel: `/claims/:id/events`. Each message is JSON with a `type` field.

```ts
export type LiveMessage =
  | { type: "checklist.step";      runId: string; step: ChecklistStep }
  | { type: "checklist.finished";  run: ChecklistRun }
  | { type: "investigation.node";  investigationId: string; node: AgentNode }
  | { type: "investigation.pass";  investigationId: string; pass: Pass }
  | { type: "investigation.stats"; investigationId: string; stats: Investigation["stats"]; requiredChecks: RequiredCheck[] }
  | { type: "investigation.loopback"; investigationId: string; loopback: NonNullable<Investigation["loopback"]> }
  | { type: "investigation.event"; investigationId: string; event: ActivityEvent }
  | { type: "investigation.status"; investigationId: string; status: Investigation["status"] }
  | { type: "dossier.ready";       dossierId: string };
```

**Client rules**

- Apply events idempotently, keyed by `id`.
- Out-of-order `checklist.step` messages: keep the one with the latest status. Status order is `waiting < running < result`.
- Only one `ActivityEvent` may have `current: true` at a time; the newest wins.
- On reconnect, refetch the full resource, then resume the stream.
- `dossier.ready` does three things:
  - shows a notification ("Dossier ready for COL-107" / action "Review")
  - sets the sidebar Dossier meta to "Ready"
  - sets the stepper's Dossier step to `ready`

---

## 6. App shell

### 6.1 Routes

| Route | Page | Sidebar item |
|---|---|---|
| `/queue` | Queue | Queue |
| `/claims/:id/checklist` | Checklist (running or finished) | Checklist |
| `/claims/:id/copilot` | Copilot (results + chat) | Copilot |
| `/claims/:id/investigation` | Live investigation | Investigation |
| `/claims/:id/dossier` | Dossier + decision | Dossier |

The Checklist and Copilot pages share one data source (the latest `ChecklistRun`). The Checklist page is the in-progress view. When a run finishes, it shows a banner linking to Copilot. It does **not** auto-redirect.

### 6.2 Sidebar (236px, sticky, full height)

1. **Brand:** a 28px gradient mark (`brandMark`) with a trend-line glyph, "Claims Co-Pilot" (14.5/600), and "Auto claims" (12, `muted`).
2. **Workspace nav:** Queue, with the total count as right-aligned meta.
3. **Claim group.** Render it only when a claim is open.
   - It sits below a divider.
   - Its label is `<b>COL-107</b> Matthew Garcia`.
   - It holds the Checklist, Copilot, Investigation, and Dossier items.
   - Each item's right-side meta reflects state:

   | Item | Meta |
   |---|---|
   | Checklist | `n/7` while running, "Done" after |
   | Investigation | pulsing dot + "Live" while running, "Paused", or none |
   | Dossier | "Draft", "Ready", or none |

4. **User** (pinned bottom): avatar initials, name, and role.
5. **Current item style:**
   - `accentSoft` background and `accentInk` text
   - a 3px `accent` bar flush to the sidebar's left edge
   - `aria-current="page"`

### 6.3 Top bar (56px, sticky, z-index 20)

- Background `rgba(251,246,255,.97)` with a 10px backdrop blur and a bottom border of `accentLine` at 60%.
- **Left:** breadcrumbs `Queue / COL-107 / <Page>`. Every crumb except the last is a button; the last is bold `ink` with `aria-current="page"`.
- **Right:**
  - search trigger (320px, placeholder "Search claims, members, shops", `⌘K` hint) that opens the command palette
  - notification bell with an `accent` dot when unread

### 6.4 Hero band (every page, full bleed under the top bar)

- Background `gradient.hero`, a 1px `heroEdge` line at the bottom, and padding of 24/28/20.
- **Queue hero:** title "Claims queue", a sub line ("45 open · sorted by risk · updated 2 min ago"), a Refresh button, and the risk tiles (7.1).
- **Claim hero:**
  - **Row 1:**
    - title `COL-107` plus member name
    - meta line: vehicle, type, "Estimate $X", "Covered start – end"
    - right side: risk pill, then page-specific actions (see each page)
  - **Row 2:** the case stepper (6.5).
- Buttons inside the hero use a translucent white background (`rgba(255,255,255,.75)`) with an `accentLine` border.

### 6.5 Case stepper

This is derived state; never store it separately. There are four equal columns, and each is a button that navigates.

```ts
type StepVisual = "pending" | "live" | "done" | "ready";
function deriveStepper(claim: Claim, run?: ChecklistRun, inv?: Investigation, dossier?: Dossier) {
  return [
    { key: "checklist", label: "Checklist",
      visual: !run ? "pending" : run.finishedAt ? "done" : "live",
      detail: !run ? "Not run" : run.finishedAt ? `${run.counts.passed} passed · ${run.counts.failed} failed` : "Running 7 checks",
      href: run?.finishedAt ? "copilot" : "checklist" },
    { key: "investigation", label: "Investigation",
      visual: !inv ? "pending" : inv.status === "complete" ? "done" : "live",
      detail: !inv ? (run?.finishedAt && run.counts.review + run.counts.failed > 0 ? "Recommended" : "Not started")
                   : inv.status === "complete" ? `${inv.passes.length} passes · ${dossier?.sourceCount ?? inv.stats.sourcesChecked} sources`
                   : inv.status === "paused" ? "Paused" : `Pass ${inv.currentPass} of up to ${inv.maxPasses}`,
      href: "investigation" },
    { key: "dossier", label: "Dossier",
      visual: dossier ? "ready" : "pending",
      detail: dossier ? "Ready for review" : inv?.loopback ? `Held: ${inv.stats.openGaps} gaps` : "—",
      href: "dossier" },
    { key: "decision", label: "Decision",
      visual: claim.state === "decided" ? "done" : "pending",
      detail: claim.state === "decided" ? "Decided" : dossier ? "Yours to make" : "Pending",
      href: "dossier" },
  ];
}
```

**Visuals.** Each step shows a 22px circle, a bold label (13/600), and a detail line (12, `muted`).

| Visual | Circle | Detail text |
|---|---|---|
| pending | white, `line` border, step number | `muted` |
| live | `accent` ring with transparent top, spinning | `accentInk` |
| done | `low` fill, white ✓ | `muted` |
| ready | `accent` fill, white number | `muted` |

The step matching the current page gets `cur`: white background, `accent` border, and the focus-ring shadow.

---

## 7. Pages

### 7.1 Queue (`/queue`)

**Risk tiles** (in the hero):
- Three toggle buttons, each at most 220px wide: High, Medium, Low.
- Each shows a 9px pip, the count (26/600), and a label (13, `muted`).
- Pip colors: `high`, `medBar`, `neutralRisk`.
- Clicking one filters the table; clicking it again clears the filter. Use `aria-pressed`.

**Toolbar:**
- **Segmented range:** Today n, This week n, All n.
- **Type chips:** All types, Collision, Comprehensive, Theft, Liability, Medical pay.
- **Sort** (right-aligned): a dropdown whose default is "Risk, high first".

**Layout:** a table plus a sticky preview panel (350px, `top: 76px`).

**Table:** `role="grid"`, rows 60px tall.

| Col | Width | Content |
|---|---|---|
| Select | 24px | Custom checkbox (`role="checkbox"`, `aria-checked`) |
| Claim | 100px | ID (600) and type below (12, `muted`) |
| Member · vehicle | minmax(130px, 1.4fr) | Name (500) and vehicle below (13, `muted`) |
| Signals | 70px | Flag icon + `rulesTriggered` (hidden if 0), task icon + `openTasks`. Both have tooltips. |
| Due | 80px | Relative: "Today", "Tomorrow", "n days". `high` color and 500 weight when due today or overdue. |
| Risk | 60px | **Colored number only, no meter or bar.** 600 weight. high → `high`, medium → `med`, low → `ink2`. |
| State | 124px | `investigating` → accent pill with pulsing dot, "Investigating". Otherwise a neutral pill with the state label ("New", "Checklist done", "Dossier ready"). |

Header: the Risk header shows a sort chevron and is `ink` colored when active.

**Row states:**

| State | Style |
|---|---|
| hover | `#FBFAFD` background |
| selected | `#FAF5FF` background, inset 3px `accent` left bar, `aria-selected` |
| checked | checkbox filled with `accent` |

**Row interactions:**

| Input | Result |
|---|---|
| Click row | Select it and update the preview |
| Double-click, or Enter on the selected row | Open the claim |
| Click checkbox | Toggle bulk selection only; do not change the preview |

**Table footer:** keyboard hints (`J` `K` move, `Enter` open, `X` select) and "Showing n of total".

**Bulk bar:**
- A floating `ink` bar, sticky at the bottom (`bottom: 18px`), visible when at least one row is checked.
- It shows "n selected" and the buttons Run checklist, Assign, and Clear.

**Preview panel:**
- A 3px `accent` top border.
- Risk pill, with "Due …" to its right.
- Title `ID · Name`, and a sub line `vehicle · type`.
- Key–value list: Estimate, Vehicle ACV, Incident.
- "Why it's flagged": up to 3 `flagReasons`, each with a severity dot (high red, medium amber).
- If the claim is investigating, an accent note: pulsing dot + "Copilot is investigating this claim — pass n of up to 5."
- Actions: **Open claim** (primary) and Assign. Open claim goes to Copilot if a run exists, otherwise to Checklist.

**Keyboard:** `J` and `K` move the selection within the filtered list, `X` toggles check, and `Enter` opens. Ignore these while the focus is in an input or textarea.

**States:**
- **Loading:** skeleton rows.
- **Empty after filtering:** "No claims match these filters" and a "Clear filters" button.
- **Error:** an inline panel ("Couldn't load the queue. Retry").

### 7.2 Checklist, running (`/claims/:id/checklist`)

**Hero:** the risk pill only on the right.

**Layout:** two columns, `1fr 400px`.

**Checklist panel:**
- **Header:** "Examiner checklist". On the right, "Step n of 7" and a 120px progress bar (4px tall, `accentGlow → accent` gradient, width animates over 500ms).
- **Step row:** a 24px icon, then the title and summary, the result label on the right, and a chevron if expandable.

  | Status | Icon | Title | Body | Result label |
  |---|---|---|---|---|
  | waiting | empty circle, `line` border | `muted`, 500 weight | — | — |
  | running | `accent` ring with transparent top, spinning | 600 | shimmer skeleton bar (220×8px) | "Checking…" in `accentInk` |
  | passed | `lowSoft` fill, ✓ in `low` | 600 | summary | "Passed" in `low` |
  | review | `medSoft` fill, `!` in `med` | 600 | summary | "Review" in `med` |
  | failed | `highSoft` fill, ✕ in `high` | 600 | summary | "Failed" in `high` |

- **Footer while running:** "Runs in the background. You can leave this page — we'll notify you when it's done." plus a **Cancel run** button.
- **On finish:**
  - hide the footer
  - show an `accentSoft` banner: "**Checklist finished.** 4 passed, 2 need review, 1 failed." with a **See results** primary button that links to Copilot
  - fire the notification "Checklist finished for COL-107" with the action "See results"

**Chat panel (right, sticky):**
- Header "Copilot" with a right-side note "Watching this run".
- Message thread. The first Copilot message includes a `context_card` titled "While this runs" with three rows of related facts.

### 7.3 Copilot (`/claims/:id/copilot`)

**Checklist panel:**
- **Header:** a 7-segment mini bar (120px, segment colors `lowBar`, `medBar`, `high` in step order) and three count pills: "n passed", "n review", "n failed".
- **Steps:** each is expandable (`button`, `aria-expanded`). The expanded body shows:
  - an evidence list (label/value grid on `#FAF9FC` with a `line2` border)
  - two buttons: **View source** and **Ask Copilot**, which prefills the chat with "Tell me about <step title>"
- **Next-step strip:** a light violet gradient strip.
  - Shown when `review + failed > 0` and no investigation exists.
  - Bold `accentInk` line: "Two checks need evidence the checklist can't gather."
  - One sentence explaining what the agents will do and that they stop for review.
  - Primary button: search icon + **Start investigation**.
- **Decision bar:** "Ready to decide now?" with Approve, Deny, and Refer to SIU (outline danger). Each opens the decision dialog (7.6).

**Chat panel:**
- Header "Copilot", with the right-side note "Answers cite their source".
- **User messages:** right-aligned, `userBubble` gradient, white text, radius 12/12/4/12.
- **Copilot messages:**
  - left-aligned, `ink2` text, with an 18px gradient mark + "Copilot" label above
  - under each Copilot answer: text buttons Helpful, Not helpful, Copy
- **Citation chip:** inline `accentSoft` pill (11.5px), for example "Check 4". A check citation does three things:
  - expands that step
  - scrolls it to the center
  - plays a 1.6s `accentSoft → transparent` background flash
- **Suggested prompts:** pill buttons above the composer.
- **Composer:** input ("Ask about this claim…") and a primary **Send** button. Enter sends.
- **Streaming:** render `ChatPart`s as they arrive, and show a typing indicator until the first part.

### 7.4 Investigation (`/claims/:id/investigation`)

**Hero actions:** risk pill, **Pause** / **Resume** toggle.
- Pausing shows the notification "Investigation paused after current step".
- Stop sits behind an overflow menu, with confirmation.

**Layout:** two columns, `1fr 400px`.

**Agent flow panel:**
- **Header:** "Agent flow", with "Pass n of up to 5 · elapsed" on the right.
- **Nodes:** four equal columns, 28px gap, min height 96px.
  - Each node shows its purpose (12, `muted`), label (600), and a status line (12.5) with a dot.
  - Nodes are joined by 1.5px `line` connectors. A connector leaving an `active` node is `accent`.

  | Node status | Style |
  |---|---|
  | done | `#CBE5D6` border, `low` status text |
  | active | `accent` border, `liveNode` shadow, `accentInk` label, pulsing dot |
  | holding | `medLine` border, `#FFFCF6` background, `med` status text |
  | waiting/idle | default border, `muted` text |

- **Loop-back:** rendered when `investigation.loopback` exists.
  - A dashed `medBar` path (1.5px, dash 4/4) from under the case writer to under the investigator, with an arrowhead pointing up at the investigator.
  - Label below the path: "Sent back with n gaps" (12/500, `med`).
  - Hidden below 760px.
- **Passes:** rows of `Pass n`, the summary, and the outcome.

  | Outcome | Text |
  |---|---|
  | complete | "Complete" in `low` |
  | gaps | "n gaps" in `med` |
  | running | "Running" in `accentInk` |

- **Stats strip:** three cells (Sources checked, Findings, Open gaps). Open gaps is `med` when above 0.
- **Steer section** (`#FCFAFF` background):
  - title "Steer the investigation"
  - help text: "Add context or redirect focus. The orchestrator picks it up on the next pass."
  - input (placeholder "e.g. Also check the tow company on the incident report") and a **Send to agents** primary button
  - submitting appends a `steer` event to the log and shows the notification "Sent to the orchestrator"

**Activity panel:**
- Header "Activity", with a right-side accent pill: pulsing dot + "Live".
- Each row: time (`h:mm:ss`, 12, `muted`), bold agent name, then the text.

  | Event kind | Style |
  |---|---|
  | hold | `#FFFBF3` background, inset 3px `medBar` left bar, agent name in `med`, gaps as a bulleted list |
  | steer | `accentSoft` background, agent label "You", sub line "Orchestrator will include this in pass n" |
  | error | `highSoft` background, a Retry button if retryable |
  | current | blinking 5×13px `accent` caret after the text |

- **Never** label a hold as "rejected", "insufficient", or "failed". Canonical copy: "Case writer held the dossier — n of 6 required checks not met yet:".
- Auto-scroll to the newest event only if the user is already at the bottom.

### 7.5 Dossier (`/claims/:id/dossier`)

**Hero actions:** risk pill, **Export PDF**, **Share**. Do not put a decision button here.

**Layout:** two columns, `1fr 330px`. The aside is sticky.

**Memo panel:**
- A 3px `accent` top border and padding of 30/38.
- **Recommendation pill:**

  | Recommendation | Pill |
  |---|---|
  | refer_to_siu | "Recommendation: refer to SIU", `high` |
  | approve | `low` |
  | request_appraisal | `med` |

- **Headline** (20/600), then the **summary** (15, `ink2`, max 66ch).
- **Findings:** rows of index, title (500), detail (13, `muted`), then source links (12, `accentInk`, underlined) and a weight pill on the right with `align-self: start`.

  | Weight | Pill |
  |---|---|
  | strong | `high` |
  | moderate | `med` |
  | mitigating | `low` |

- **Still open:** each `OpenItem` is a `medSoft` box with bold `med` title, detail, and an optional action button (for example **Draft request**).

**Aside, card 1 (required checks):**
- A 56px ring showing met/total, stroked with a `accentGlow → accentInk` gradient.
- "n of 6 / required checks met".
- The checklist of required checks: "Met" in `low` or "Open" in `med`.

**Aside, card 2 ("Your decision"):**
- Textarea "Note for the claim file", with the hint "Required for SIU referrals and denials."
- Buttons, stacked:
  - the recommended action as primary
  - **Request appraisal first** as outline
  - the action that contradicts the recommendation as a ghost button (for example "Approve anyway")

### 7.6 Decision dialog (the only modal)

- **Trigger:** any `[data-decide]` button.
- **Behavior:** `role="dialog"`, `aria-modal`, focus trap, Esc and scrim click close it, and it restores focus to the trigger.
- **Title:** `<Action> — <ClaimID>?`
- **Body copy by action:**

  | Action | Body |
  |---|---|
  | refer_to_siu / deny | "Add a note for the claim file. SIU will see this with the dossier." |
  | approve | "Copilot recommends referring this claim to SIU. Approving will release payment of $X." Reflect the actual recommendation and estimate. |
  | request_appraisal | "Copilot will draft the request for you to review before it's sent." No note field. |

- The note is prefilled from the aside textarea if present.
- **Validation:** for deny and refer, an empty note blocks submit. Show a `high` outline and the placeholder "A note is required for this decision", and focus the field.
- **Confirm button:** labeled with the action verb (Refer to SIU / Approve / Deny / Draft request).
- **On success:** notification with past-tense copy ("Referred to SIU · COL-107", "Approved · COL-107") and an **Undo** action while `undoableUntil` has not passed.

---

## 8. Shared components

| Component | Props (essentials) | Notes |
|---|---|---|
| `Button` | `variant: primary \| secondary \| ghost \| danger`, `size: sm \| md`, `icon?` | Primary uses `gradient.primaryButton` and its shadow. Hover on primary is solid `accentInk`. |
| `Pill` | `tone: high \| med \| ok \| accent \| plain`, `dot?: "static" \| "pulse"` | 12.5/500, radius pill, `white-space: nowrap`, `align-self: start` |
| `RiskNumber` | `score` | Colored number only (see 7.1). No bars, meters, or gauges anywhere. |
| `RiskPill` | `score` | "High risk · 98.4" |
| `Panel` | `title`, `right?`, `children` | Surface background, `line` border, radius `l`, `overflow: hidden` |
| `CaseStepper` | output of `deriveStepper`, `currentKey` | 6.5 |
| `ChecklistStepRow` | `step`, `expandable`, `onAsk` | 7.2 / 7.3 |
| `AgentFlow` | `nodes`, `loopback?` | 7.4 |
| `ActivityLog` | `events` | 7.4 |
| `CitationChip` | `citation`, `onActivate` | 7.3 |
| `ChatThread` / `Composer` | `messages`, `onSend`, `suggestions?` | |
| `DecisionDialog` | `claim`, `action`, `recommendation`, `initialNote` | 7.6 |
| `Toast` | `message`, `action?: { label; onClick }` | Bottom-right, `ink` background, 4.2s auto-dismiss, `role="status"`. Only one at a time. |
| `BulkBar` | `count`, actions | 7.1 |
| `Kbd` | `children` | 11px, `line` border, radius 4 |

**Icons:** 16px, stroke 1.7, `currentColor`, no fill (a Lucide-compatible set works).

---

## 9. Motion

Allowed motion is limited to state changes and "agent is working":

| Motion | Where |
|---|---|
| Spin (0.8s) | running check icon, live stepper circle |
| Pulse (1.4s opacity) | live dots only |
| Shimmer | skeleton bar in the running step |
| Width transition (500ms) | progress bar |
| Flash (1.6s) | citation target |
| Rotate 180° (200ms) | chevron on expand |
| Toast slide (250ms) | notification enter and exit |

No entrance animations on page load, no hover lift on cards, and no parallax. Under `prefers-reduced-motion: reduce`, disable all animation and transitions.

---

## 10. Accessibility

- WCAG 2.2 AA contrast. `accent #A100FF` on white is about 5.3:1, which is fine for text; `muted #6A6878` on white is AA.
- Status is never communicated by color alone: always pair it with an icon, a text label, or a number.
- Every interactive element is a real `button` or `a`. Visible focus uses a 2px `accent` outline with a 2px offset.
- Queue: `role="grid"` and `aria-selected` on rows; custom checkboxes use `role="checkbox"` and `aria-checked`.
- Live regions:
  - the preview panel: `aria-live="polite"`
  - notifications: `role="status"`
  - activity log: `aria-live="polite"` with `aria-relevant="additions"`
- Dialog: focus trap, labelled by its title, Esc closes it.
- Keyboard shortcuts must not fire while typing, and must be discoverable (table footer hints).

---

## 11. Responsive

| Breakpoint | Change |
|---|---|
| ≤1300px | Queue hides the Signals and State columns (the preview panel still shows state) |
| ≤1100px | All two-column layouts stack; sticky preview and chat become static; chat height 560px |
| ≤760px | Sidebar becomes a top block with no claim group or user; search hidden; stepper and agent nodes use 2 columns; loop-back and node connectors hidden; queue rows show checkbox, claim, member only |

---

## 12. Copy reference

| Context | String |
|---|---|
| Queue sub | "45 open · sorted by risk · updated 2 min ago" |
| Preview section | "Why it's flagged" |
| Running footer | "Runs in the background. You can leave this page — we'll notify you when it's done." |
| Checklist done | "Checklist finished. 4 passed, 2 need review, 1 failed." |
| Investigate strip | "Two checks need evidence the checklist can't gather." |
| Investigate strip body | "Copilot can investigate the shop, Matthew's history and the estimate, then draft a dossier. It stops for your review before anything is decided." |
| Hold event | "Case writer held the dossier — 2 of 6 required checks not met yet:" |
| Loop-back label | "Sent back with 2 gaps" |
| Steer help | "Add context or redirect focus. The orchestrator picks it up on the next pass." |
| Decision note hint | "Required for SIU referrals and denials." |
| Toasts | "Checklist finished for COL-107" · "Sent to the orchestrator" · "Investigation paused after current step" · "Referred to SIU · COL-107" |

**Banned:** "rejected", "INSUFFICIENT", "the databases are judging us", "your claim is in good hands", all-caps status words, and "→" appended to button labels.

---

## 13. Acceptance criteria

- [ ] Tokens are implemented as CSS variables and no hex values appear in components.
- [ ] Risk level is derived only via `riskLevel()`. The queue Risk column shows only the colored number.
- [ ] Violet never indicates status; red, amber, and green never decorate.
- [ ] The checklist runs inline with per-step live updates. Leaving the page and returning shows correct progress. The finish banner and notification appear.
- [ ] Clicking a check citation expands, scrolls to, and flashes the step.
- [ ] The stepper is derived (6.5) and correct on all four claim pages. Every step navigates.
- [ ] Breadcrumbs navigate. The sidebar claim group appears only with an open claim and shows live meta.
- [ ] The agent flow shows correct node states. The loop-back appears only when `loopback` is present. Hold events are amber, never red.
- [ ] Steer submits, appends to the log, and shows a notification. Pause/Resume toggles the label and the API state.
- [ ] Only one decision entry point per page area. On the dossier, the contradicting action is a ghost button.
- [ ] The decision dialog enforces notes for deny and refer, traps focus, supports Undo, and uses past-tense confirmation copy.
- [ ] Queue keyboard (J/K/X/Enter), tile filtering, and the bulk bar work. Shortcuts are ignored in inputs.
- [ ] Every data view has loading, empty, and error states.
- [ ] Reduced-motion disables all animation. Keyboard-only use completes the full flow: queue → checklist → investigation → dossier → decision.

---

## 14. Out of scope (next)

- **Dashboard page:** queue health, time-to-decision, and examiner/agent agreement rate.
- Command palette contents (`⌘K`).
- Assign flow and multi-examiner presence.
