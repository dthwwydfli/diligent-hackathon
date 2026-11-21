# UI_SPEC: Namesake analyst view (low-level design, v3)

**Status:** spec-anchored. The reference implementation is the Vite + React + TypeScript app in `ui/`. If the spec and the app disagree, fix whichever is wrong.

**Visual language:** RonDesignLab's Cargo, EHR and DevOps dashboards. What we take from them:

- a spatial **canvas** as the centrepiece;
- a cool grey page;
- frosted white groups;
- black primary buttons;
- saturated single-meaning chips.

**Interaction rules:** Apple's Human Interface Guidelines. Clarity, deference to content, depth through layering, and *one place for every piece of information*.

**Stack:** Vite, React 19, TypeScript, Tailwind CSS v4, Motion (`motion/react`), Lottie (`lottie-web`, Jitter-compatible SVG renderer), `@thesvg/ui-react` (glass look), `@thesvg/flags`, `@thesvg/react` (KYC brand badges), `lucide-react` (chrome controls). Local Geist / Geist Mono woff2 only (no CDN fonts).

---

## 0. Rules that decide what goes on screen

1. **Every element has a job, or it's deleted.** If you can't say which of the analyst's questions it answers, it doesn't ship. The questions:
   - Who is the customer?
   - Who is the listed person?
   - What links them?
   - What did we decide, and why?
2. **Each fact appears once.** The decision appears once (the verdict card). Each fact appears once (its canvas node). Each check outcome appears once (the ladder). Colour is what ties them together; repeated text is not.
3. **No dead controls.** Every visible control works.
4. **Content first, chrome second.** Names and facts are large and dark. IDs, sources and dates are small and grey. The canvas has no borders; groups float.
5. **People-readable first, IDs second.** Every ID (`CUS-…`, `NOTE-…`) appears *next to* a human statement, never instead of one.

### What was removed from v1, and why

| Removed | Why |
|---|---|
| Left icon rail | There are only three real pages; they live in the top segmented control. |
| Fake nav dropdowns, hamburger, avatar, refresh | Dead controls. |
| Resolution-path chips (ACC – CUS – H) | Replaced by one plain sentence. |
| Candidate cards column | Repeated the canvas's Person A / Person B groups. |
| Context-bar pills | Repeated the verdict and the canvas. |
| Canvas tools, Layer select, Views, legend | Not needed; the ladder carries the chips. |
| Right-panel tabs | Evidence repeated the canvas. |
| Bottom evidence table + filter bar | Four rows don't need filters. |
| Purple | Replaced (see 1.1). |
| Static `string.Template` HTML generator | Replaced by the React app in `ui/`. |

---

## 1. Tokens

### 1.1 Colour: one meaning each

| Token | Hex | Meaning (only this) |
|---|---|---|
| `--canvas` | `#DCDFE4` | Page background |
| `--surface` | `#FFFFFF` | Cards, panels, fact nodes |
| `--plot` | `#EFF0F2` | The Identity Graph board |
| `--glass` | `rgba(255,255,255,.74)` + `blur(6px)`, 1px white border | Node groups on the board |
| `--ink` / `--ink-2` / `--ink-3` / `--ink-4` | `#0A0A0A` / `#55585E` / `#8E9299` / `#B4B8BE` | Text tiers; ink is also the primary button |
| `--clear` (soft `#ECF7D6`, text `#3F6300`) | `#B4F110` | **Different person**, and links that **contradict** |
| `--match` (soft `#FFE6EF`, text `#B3245A`) | `#FF6A9E` | **Same person**, and links that **agree** |
| `--review` (soft `#FBF7CF`, text `#6E6500`) | `#F1E516` (draw lines in `#E2D400`) | **Review**, and checks that are **unknown** |
| `--caution` (soft `#FFEBD3`) | `#FC9519` | An **uncertain fact**, or a **blocked clearance** |
| `--source` (soft `#DCE8FF`) | `#0068FF` | **Where a fact came from** |
| `--verified` | `#5CD389` | An approved identity check |

No other accent colours. No gradients. Status text sits on the soft tint; only the decisive chip uses the strong fill.

### 1.2 Type

- **Geist** for all text; **Geist Mono** for IDs and machine codes only. Both SIL OFL, bundled as woff2 in `ui/public/fonts/`, never loaded from a CDN.
- Turn on antialiasing. Monospace is **never** used for descriptions.

| Role | Spec |
|---|---|
| Page title (customer's name) | 28 / 400 / −0.6px |
| Board title, verdict | 22 / 400–500 / −0.4px |
| Section title ("How it was decided") | 18 / 400 / −0.3px |
| Body, fact title | 13 / 500 |
| Group header | 13 / 600 |
| Secondary line, notes | 11.5–12 / 400, `--ink-3` |
| Caps label | 11 / 500 / +0.6px, uppercase |
| IDs | Geist Mono 11.5 / 400, `--ink-3` |
| Chip | 11.5 / 600 |

### 1.3 Shape, space, depth

- **Radii:** chip 6 · control 10 · fact node 10 · group and card 14 · board and panel 20 · circles 50%.
- **Spacing:** an 8pt grid (4 for tight). Page padding 20/24; panel padding 20; gap between panels 12.
- **Depth through layering, not shadows:** page `--canvas` → board `--plot` → glass group → white fact node. The only shadow is on the active segment: `0 1px 2px rgba(0,0,0,.06)`.
- **One outline on screen:** the decisive ladder row, 1px `--ink`.

### 1.4 Icons and flags

- **UI icons:** `@thesvg/ui-react` glass look (`*GlassIcon`), matching https://thesvg.org/ui?v=glass. Used in group handles (person, verified, profile, source, ghost) and Run metric cards.
- **Flags:** `@thesvg/flags` (`flag-{iso2}`), circle or rounded 4×3, `aria-hidden="true"` beside the country name. Shown next to the customer title (primary country), watchlist name, Queue name cells, and country fact nodes.
- **Brand badges:** `@thesvg/react` for known KYC/API providers; fall back to a glass shield UI icon.
- **Chrome controls:** `lucide-react` for back, prev/next, copy/check, and search.

### 1.5 Motion

- **Motion (`motion/react`):** shared `layoutId` spring pill on segmented controls; staggered spring entrance on glass groups and ladder rows; SVG Bézier `pathLength` draw on Identity Graph edges; spring width reveal on the Run stacked bar. Honour `prefers-reduced-motion`.
- **Lottie (`lottie-web`, SVG renderer):** small bundled JSON micro-animations for verdict status, copy confirmation, and empty-run state. Compatible with Jitter Lottie exports.

---

## 2. Pages (exactly three, in the top segmented control)

| Page | Question it answers | Contents |
|---|---|---|
| **Queue** (`/`) | What needs a human? | Segmented filter `All · Review · Same · Cleared` with counts. One table, sorted Review → Same → Cleared, then by alert ID. Five columns: Customer · Listed as · Decision · Reason · Alert. Working name search. Row click opens Case. |
| **Case** (`/case/:hitId`) | Is this hit our customer, and why? | Header + Identity Graph + decision panel |
| **Run** (`/run`) | Can we trust the system? | Built only from `summary.json`. Four large figures + stacked bar. Missing file → "No run yet", **no placeholder numbers**. |

**Top bar:** logo (20px black rounded square with a lime dot, "Namesake" 16/600), the segmented control (Queue / Case / Run; active segment white with spring pill), and on the right one line of plain text: dataset · hit count · run time.

---

## 3. Case page

### 3.1 Header

- Back circle (34px, white) → Queue (`lucide` chevron).
- **Title = the customer's name** + primary-country flag when known.
- **Subline in mono:** `Alert A-… · Hit H-… · screened YYYY-MM-DD`.
- **Right side:** pager "Hit n of N in alert" with prev/next (enabled only when N > 1). Black **Copy result** button copies this hit's output line JSON.

### 3.2 Identity Graph (the canvas)

**Board:** `--plot`, radius 20, 1fr wide, 560 high, `overflow:hidden`.

**Board header:** title "Identity Graph"; caps labels "OUR CUSTOMER" / "WATCHLIST PROFILE"; one "how we found them" sentence under the left label.

**Left column** (x = 24, w = 280): Person group (glass UI icon handle), Verified group (green check / glass shield), Ghost groups (opacity .6).

**Right column** (x = board width − 314, w = 290): Profile group, fact nodes for birth date and countries (with flags), Source groups (blue glass icon).

**Rows aligned by meaning:** name ↔ name, birth date ↔ birth date, country ↔ country.

**Links:** 2px Bézier from right edge of left node to left edge of right node, with 3.5px end dots. Colour = outcome (`match` / `clear` / `review` dashed). Provenance dashed `--source`. Drawn from element anchors; redrawn on resize. Hovering a ladder row highlights its links.

**Uncertain facts:** 1.5px `--caution` outline + "uncertain · readers disagree".

**Missing facts:** dashed `--ink-4` empty node, yellow dashed link.

### 3.3 Decision panel (white, radius 20, 360 wide)

**Verdict card** (soft colour of the decision): caps "DECISION"; title Different person / Same person / Needs review; reason code in mono; reason text; at most one status line with a Lottie/dot ("Every fact used is certain" or "Clearance blocked: …"). For REVIEW, no third repeat of the missing fact.

**"How it was decided" ladder**, rows in policy order: Type, Time, Birth date, Country, Name, Result. Hover highlights canvas links. Result row outlined in ink with the strong chip.

---

## 4. States

| State | Canvas | Panel |
|---|---|---|
| Different person | Contradicting pair linked in lime | Lime verdict; contradicting check = Contradicts |
| Same person | Pink links for name, birth date, country | Pink verdict |
| Needs review | Yellow dashed link to a "not found" ghost node | Yellow verdict |
| Clearance blocked | Orange outline on the uncertain fact | Status line "Clearance blocked: …" |
| Several people fit | Two Person groups on the left | Verdict says "N people fit"; AMBIGUOUS |
| Person vs company | One lime link "Individual ↔ Company" | Type row = Contradicts |

---

## 5. About the IDs

| Prefix | Record |
|---|---|
| `A-` | alert |
| `H-` | hit |
| `CUS-` | customer record |
| `ACC-` | account |
| `APP-` | KYC applicant |
| `KYC-` | identity check |
| `NOTE-` | support / onboarding note |
| `SR-` | web search result |

---

## 6. Data contract (trace JSON → page)

The engine writes its own trace (engine SPEC §5.8b). `tools/report/export_ui_data.py` converts it into the page JSON below. The UI never reads engine internals directly, and `system/` never imports UI code.

```ts
export type Decision = "DIFFERENT_ENTITY" | "SAME_ENTITY" | "REVIEW";
export type LinkOutcome = "match" | "clear" | "review" | "source";

export interface CasePage {
  hit_id: string;
  alert_id: string;
  screened_at: string;
  hit_index: [number, number];
  customer_name: string;
  customer_country_iso2?: string | null;
  found_via: {
    kind: "account" | "login" | "email" | "search" | "none";
    id?: string | null;
    holders?: number;
    fit?: number;
  };
  persons: PersonBlock[];
  ghosts: GhostBlock[];
  profile: ProfileBlock;
  links: [string, string, LinkOutcome][];
  ladder: LadderRow[];
  decision: Decision;
  reason_code: string;
  reason: string;
  status: { kind: "certain" | "blocked" | "none"; text: string };
  missing: { side: "profile" | "customer"; display: string }[];
  output_line: Record<string, unknown>;
}

export interface PersonBlock {
  label: string;
  fits: boolean;
  records: string[];
  merged_by?: string | null;
  name: { id: string; display: string; country_iso2?: string | null };
  verified?: {
    provider: string;
    source: string;
    date: string;
    facts: FactNode[];
  } | null;
}

export interface FactNode {
  id: string;
  display: string;
  line?: string;
  certain?: boolean;
  country_iso2?: string | null;
  source?: string | null;
}

export interface GhostBlock {
  label: string;
  line: string;
}

export interface ProfileBlock {
  category: string;
  score?: number | null;
  name: { id: string; display: string; country_iso2?: string | null };
  facts: FactNode[];
  sources: { id: string; label: string; note: string; supports: string }[];
}

export interface LadderRow {
  check: string;
  phrase: string;
  outcome: "agrees" | "contradicts" | "unknown" | "result";
  result_chip?: "Same" | "Cleared" | "Review";
  link_ids?: string[];
}

export interface QueueRow {
  hit_id: string;
  alert_id: string;
  customer_name: string;
  customer_country_iso2?: string | null;
  listed_name: string;
  listed_country_iso2?: string | null;
  category: string;
  decision: Decision;
  reason_code: string;
}

export interface RunSummary {
  hits: number;
  unsafe_practice: number;
  practice_labels: number;
  identical_runs: number;
  runs: number;
  seconds: number;
  cost_usd: number;
  split: Record<Decision, number>;
}
```

Synthetic sample: `ui/src/data/syntheticSample.ts` (no participant data). Live data: `ui/public/data/{queue,summary}.json` and `ui/public/data/cases/<hit_id>.json` (git-ignored).

---

## 7. Build

- `tools/report/export_ui_data.py` uses the Python standard library only.
- `ui/` is Vite + React + TypeScript + Tailwind CSS v4.
- Fonts are referenced relatively from `ui/public/fonts/`; pages work offline for the synthetic sample.
- All data text is escaped / rendered as React text nodes. Snippets and notes are untrusted and never inserted as HTML.
- `ui/public/data/`, `demo/`, and `runs/` are git-ignored.

## 8. Acceptance checklist

1. No piece of information appears in two places on one page.
2. Every visible control works (back, pager, Copy result, Queue filter, Queue search, Run bar → Queue filter).
3. Only the colours in 1.1 appear, each with its one meaning. No purple.
4. Geist renders for text and Geist Mono for IDs only.
5. No text wraps or truncates at 1440 px. Group notes and ladder phrases stay on one line.
6. Every link meets its nodes and is redrawn on resize; ladder hover highlights links.
7. The decision is readable in 3 seconds from the colour alone.
8. Country flags appear beside names / country facts when an ISO-2 code is known; decorative flags are `aria-hidden`.
9. Glass thesvg UI icons appear in group handles; Lucide icons power chrome controls.
10. Motion / Lottie animations honour `prefers-reduced-motion`.
11. Missing `summary.json` shows "No run yet" with no placeholder numbers.
12. `tsc --noEmit`, `vite build`, and Vitest acceptance tests pass.
