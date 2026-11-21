# SPEC: Namesake v3, "same person or not"

Track 2 (sanctions screening), Grok Bot London Financial Crime Hackathon, Sat 21 Nov 2026.
Code freeze 17:00 London.

**Status:** spec-anchored. This file lives in the repo and changes when the system changes. The tests in `tests/` and `tools/` are what tie the two together.

**Source of truth:** `POLICY.md` and the organisers' files (`README.md`, `output.schema.json`, `validate.py`). Where this spec disagrees with `POLICY.md`, the policy wins. Fix the spec as soon as you notice.

**Build rule:** before writing code, restate the acceptance criteria (section 6) and the interpretation register (section 9) in your own words, and flag any line of `POLICY.md` you read differently. Don't start a component until its acceptance tests are written. Fixtures are synthetic. No dev IDs, names, or wording in `system/` or unit tests.

---

## Corrections vs the draft (policy / brief win)

1. **OpenRouter only.** Model calls go through OpenRouter with `OPENROUTER_API_KEY`. No direct xAI route unless organisers confirm a Grok key on Discord and `NAMESAKE_ALLOW_XAI=1` is set. Bad or missing key → reader-only path.
2. **Location + name/DOB agree → REVIEW.** Location contradiction does not clear when name and DOB agree (`INSUFFICIENT_DATA`). Evaluate the exception before clearing.
3. **Company legal forms stripped for companies only.** Placeholders still apply to people.
4. **Edit distance is Levenshtein.** A transposition is two edits. Shorter part's length picks the budget. Under 4 letters must be identical.
5. **Slash dates.** Day > 12 → DMY certain. Both ≤ 12 → uncertain; usable for confirmation only, never to enable a clearance.
6. **Death.** Only `deceased_date` before `screened_at` makes `DECEASED` true. Prose / `life_status` alone → UNKNOWN.
7. **Polarity without LLM.** Clean KYC notes (check date = `created_at`, parseable DOB/country/name, positive cue, no negative cue) are certain. Unclear polarity → UNKNOWN; cannot enable a clearance.
8. **Official time cap is 30 minutes.** Internal targets: under 2 minutes without LLM, under 8 with LLM.

---

## 1. Overview

For every watchlist hit, the system decides `DIFFERENT_ENTITY`, `SAME_ENTITY` or `REVIEW`. It also gives a reason code, the resolved customer record, a 2–4 sentence reason, and the IDs of the records that decided it.

It works the way an analyst does:

1. **Resolve the customer.** Follow the alert's link (or search when there is none), then merge the records that belong to one person (P2, P3).
2. **Resolve the listed person.** Gather the hit's DOBs, countries, names and dated reports from structured fields first, then from the profile text and the accepted search snippets (P5).
3. **Apply `POLICY.md` as code.** A three-valued proof engine clears a hit only when a contradiction is certain. It confirms on agreement and sends everything else to review (P6, P7).
4. **Explain.** The engine writes a reason in the style of the reference answers and cites the smallest set of records that proves the decision (P9).

A language model may help read free text. It never decides anything.

## 2. The bet

The practice labels were clearly produced by code that applies `POLICY.md`: the reference reasons and paths follow fixed templates. So the best possible system reproduces that program exactly and reads the reworded free text reliably. Our edge over other teams is not a better prompt. It is that we measure the unseen-set failure modes before 17:00:

- a generator twin: thousands of labelled cases built from dev, covering rare policy branches, with free text reworded by several LLMs;
- a second, independent implementation of the policy, compared against the engine on every case;
- text readers that don't depend on sentence wording;
- a proof engine that cannot clear on an uncertain fact.

## 3. Scoring, and the rules that follow from it

From the brief: unseen set (about 550 hits, 5 runs) 80%; dev 10%; reproducibility 10%, scaled by the unseen score. Within each set, decisions count 75% and reasons 25%.

| Truth \ We say | DIFFERENT_ENTITY | SAME_ENTITY | REVIEW |
|---|---|---|---|
| DIFFERENT_ENTITY | 0 | 3 | 3 |
| SAME_ENTITY | **60** | 0 | 2 |
| REVIEW | **60** | 2 | 0 |

At the practice-label mix, the all-REVIEW cost on 550 hits is about 1,188. So:

- one unsafe clearance costs about 5 decision points (about 3 total points);
- one missed clearance costs about 0.25 decision points;
- confusing SAME with REVIEW costs about 0.17 decision points.

Rules that follow:

- **R1.** Clear only on a certain contradiction. Clearing only beats REVIEW above about 95% confidence. That means every fact enabling the clearance must have certainty level C (section 5.3).
- **R2.** Confirm whenever the policy confirms. SAME vs REVIEW costs are symmetric, so hedging buys no safety. The policy's own REVIEW cases still apply, for example name and DOB agree but every country differs.
- **R3.** Pick defaults by cost. If an ambiguity affects a clearance, take the reading that doesn't clear. If it only affects SAME vs REVIEW, take the likelier reading.
- **R4.** The next hour always goes to preventing unsafe clearances.
- **R5.** Any decision flip between runs costs twice, once in decisions and once in reproducibility.

## 4. Inputs and outputs

Call: `system/run <data folder> <output file>`. It must work from any working directory, including from inside `system/`, with absolute or relative paths.

Reads from the data folder: `alerts.jsonl`, `hits.jsonl`, `customers.jsonl`, `accounts.jsonl`, `onboarding.jsonl`, `kyc_checks.jsonl`, `notes.jsonl`, `search_results.jsonl`, `name_variants.json`, `POLICY.md`. It must not require `practice_labels.jsonl`.

Writes exactly one JSON line per hit in `hits.jsonl` that validates against `output.schema.json`:

```json
{"hit_id": "H-XXXXXX", "alert_id": "A-XXXXXX", "decision": "DIFFERENT_ENTITY",
 "reason_code": "DOB_MISMATCH", "customer_record_id": "CUS-NNNNNN",
 "reason": "Two to four sentences with this hit's own facts and IDs.",
 "evidence": ["KYC-XXXXXX", "SR-XXXXXX"]}
```

`customer_record_id` is any record of the resolved person; `"AMBIGUOUS"` when more than one person fits, even if they all lead to the same decision; `null` when no record fits.
`reason_code` is any code that applies and belongs to the decision. The policy says any applicable code is accepted.
`evidence` holds the decisive records only, each an ID that exists in the folder.

Traces (optional) are written only when `NAMESAKE_TRACE_DIR` is set. Nothing else is written.

## 5. Architecture

```
alerts ─► [A] resolve customer ─► Person(s): facts with provenance and certainty
hits ───► [B] gather hit facts ─► HitFacts: facts with provenance and certainty
notes / profile first paragraph / snippets
        ─► [C] readers that ignore sentence wording, plus an LLM second opinion
                         │
                         ▼
          [D] three-valued checks per person (P6, P7)
          [E] decision table + aggregation over several persons (P3)
          [F] proof ─► minimal evidence + templated reason (P9)
          [G] writer: one valid line per hit, always
```

### 5.1 [A] Customer resolution (P2, P3, P4)

**Linked alerts.** Account (may give 2 holders), login or email leads to candidate records. If a link leads to more than one person, the screened details choose, using the same test as for unlinked alerts.

**Unlinked alerts.** A record fits when every screened detail present agrees:

- its full, preferred or login name agrees with the screened name (P8);
- its DOB equals the screened DOB in every part both give;
- the screened country is its residence or nationality;
- the screened city is in its city or address.

Look these up through pre-built indexes, never by scanning 72k records per hit. Never use another customer's records.

**Merging into one person.** Use union-find over two kinds of edge: (shared phone and the same full DOB) and (same document number on approved checks). Merging is transitive because the policy says so. All merged facts count. Shared phone or address alone is not an edge.

**Verified facts.** The most recent approved check of the person, from `kyc_checks` or from a note that passes the polarity gate (5.4), sets the legal name, the DOB and the document country. Rejected or expired checks are not evidence.

**Several persons.** Decide each separately. If all decisions are the same, emit it; otherwise emit `REVIEW` / `AMBIGUOUS_CUSTOMER_RECORD`. Either way `customer_record_id` is `"AMBIGUOUS"`.

### 5.2 [B] Hit facts (P5)

**Names:** `name`, aliases and `first_name`/`middle_name`/`last_name`. Use `best_matching_name` to settle given-name vs surname order. Strip bracketed tags.

**DOBs:**

- the `dobs` field, plus birth sentences in the first paragraph of `profile_notes`;
- only if both give nothing, accepted search results.

An age at a date gives two possible birth years. For companies, only `dobs` is an incorporation date.

**Accepted snippet.** The query equals the hit name's lowercase words sorted alphabetically. The snippet contains the listing phrase for the hit's primary (or first) category exactly, and names a country tied to the hit. Accepted snippets add their possible birth years to one set.

**Countries tied to the hit:** `countries`, `nationality`, `citizenship`, the last part of each address, and `place_of_birth`. "International" and "Europe" are not countries. Territories count as their own country.

**Dated reports:** only lines of the exact form `According to …; <Month D, YYYY>: …`. The policy says this form is worded the same in the unseen set, so use exact matching and nothing looser. The earliest such date is what the under-16 / incorporated-after test uses.

**Death:** a date of death before `screened_at`, from `deceased_date`. Any other death wording makes DECEASED UNKNOWN, never TRUE (register I4).

### 5.3 Facts and certainty

Every fact carries a value, a source ID, a field or span, and a certainty level:

| Level | Source |
|---|---|
| C (certain) | A structured field; or a free-text fact that the wording-independent reader and the LLM second opinion agree on, with a verbatim span that code re-parses |
| U (uncertain) | The reader and the LLM disagree; an ambiguous date format; unclear polarity; a place-like token that doesn't map to a country |

**Rule:** U facts may block a clearance or support a confirmation, but never enable a clearance. With no LLM available, the reader's output alone counts as C only where the reader's rule is marked "safe without a second opinion" (the dateline regex, exact listing phrases, structured dates).

### 5.4 [C] Readers that ignore sentence wording

Don't match sentence templates. Dev notes already use about 19k distinct wordings, and the unseen set is reworded. Instead, extract typed tokens and assign their roles from type constraints.

**Token types:** countries plus demonyms and alternative names (gazetteer built from mledoze/countries, ODbL); dates in all formats seen; ages; upper-case personal names; KYC provider and document-type words; polarity cues.

**KYC-channel notes:** the check date is the date equal to the note's `created_at`. The other date is the DOB. The demonym or country is the document country. The upper-case name is the verified name.

**Polarity gate:** a note counts as an approved check only if it has a positive verification cue, no negative cue, and (when LLM is present) the LLM agrees. If polarity is uncertain, "the most recent approved check" is UNKNOWN for that person. Clean notes without LLM may still be C (correction 7).

**Residence notes:** country plus a year or year range means "a place they lived". Any place-like token that can't be mapped to a country makes the customer's country set open, which makes LOCATION_MISMATCH UNKNOWN.

**Profile first paragraph:** "born in YYYY", "born on \<date\>", and age plus event date. A birth cue that can't be parsed makes the hit's DOB UNKNOWN, and blocks the fall-through to snippets.

**Snippets:** age plus the snippet's month and year give 2 possible birth years.

**Runtime LLM (second opinion only):** sees one text unit and returns typed facts, each with a verbatim quote and a polarity. JSON-schema output, temperature 0, fixed seed. Requests are keyed by a hash of the text within a run. Code checks that the quote is in the text and re-parses the value. Any disagreement with the reader makes the fact U.

### 5.5 [D] Checks (three-valued)

Each check returns TRUE, FALSE or UNKNOWN, plus the proof (the facts it used).

- **Type:** person vs company.
- **Time:** customer age at the earliest dated report is under 16 in every reading of the customer's DOB interval; for companies, the incorporation date is after that report; the hit's death date is before `screened_at`.
- **DOB contradiction:** every possible hit birth date is contradicted. Either the customer's birth-year interval is more than 1 year outside it, or both give a month in the same year and the months (or days) differ. One agreeing date prevents it.
- **Location contradiction:** the customer's country set is closed and does not overlap the hit's country set. Name and DOB both agreeing makes this REVIEW instead.
- **Name contradiction:** the verified legal name agrees with none of the hit's names or aliases (P8). Not available when the person has no approved check.
- **Agreement:** name agrees (P8) and DOB agrees. For companies, name agrees and country agrees.

Dates are intervals. `"1988"` means 1988-01-01 to 1988-12-31. Partial dates are never filled in.

**P8 names (pure code):** ignore case, accents, punctuation and anything in brackets; single letters are initials; two parts match when identical, variants, joined/split, or within edit distance 1 (4–6 letters) or 2 (7+); parts under 4 letters must be identical; names agree when at least 2 parts match, or every part of the shorter name matches; placeholders and company legal forms are not parts; an individual with fewer than 2 real parts can be neither confirmed nor cleared on name.

### 5.6 [E] Decision table

The policy is stored as data (`system/namesake/data/policy_table.json`), one row per outcome, each citing its POLICY clause. The engine walks the table; the table is never hard-coded into branches.

Any clearance check TRUE ⇒ `DIFFERENT_ENTITY`, with the code of that check. **Exception (P6 Location):** a TRUE Location check does not count when name and DOB both agree. Evaluate the exception before clearing. Country differs, name and DOB agree ⇒ `REVIEW`, never `DIFFERENT_ENTITY`.

Otherwise, if Location is TRUE but name and DOB agree ⇒ `REVIEW` / `INSUFFICIENT_DATA`.

Otherwise, if agreement is TRUE and no check is TRUE or UNKNOWN-blocking ⇒ `SAME_ENTITY`: `NAME_DOB_LOCATION_MATCH` if countries overlap, else `NAME_DOB_MATCH`; `NAME_LOCATION_MATCH` for companies.

Otherwise ⇒ `REVIEW` / `INSUFFICIENT_DATA`.

Several persons ⇒ aggregate as in 5.1.

### 5.7 [F] Reasons and evidence

Evidence is the minimal set of records that the proof actually used. Reason is written from templates filled with this hit's values and IDs. Every REVIEW names what cannot be settled.

### 5.8 [G] Writer and robustness

Each alert is processed in isolation. Any exception produces a valid `REVIEW` / `INSUFFICIENT_DATA` line with the alert's evidence. Every line is checked against the schema before it is written. Iteration is sorted, ties are broken by ID strings, and `PYTHONHASHSEED=0`.

### 5.8b Traces and the demo UI (interface to `UI_SPEC.md`)

**Engine side.** When `NAMESAKE_TRACE_DIR` is set, `system/` writes one JSON per hit: its own facts (value, source ID, span, certainty), the persons and how they were found (link kind, holders, who fit, merge edges), every check (name, TRUE/FALSE/UNKNOWN, proof facts), the decision, the output line, and for REVIEW the missing fact. `system/` never imports or knows about UI code.

**Adapter.** `tools/report/export_ui_data.py` maps engine traces (+ optional `runs/summary.json`) to page JSON under `ui/public/data/` as specified in `UI_SPEC.md` §6.

**Frontend.** The analyst UI is a Vite + React + TypeScript + Tailwind CSS app in `ui/`. It reads the exported JSON (or a synthetic sample when traces are absent). `demo/` and `runs/` and `ui/public/data/` are git-ignored.

**Run summary.** Test tools write `runs/summary.json`:

```json
{"hits": 819, "unsafe_practice": 0, "practice_labels": 50, "identical_runs": 5, "runs": 5,
 "seconds": 252, "cost_usd": 0.4, "split": {"DIFFERENT_ENTITY": 0, "SAME_ENTITY": 0, "REVIEW": 0}}
```

If the file is missing, the Run page says "No run yet". It never shows placeholder numbers.

### 5.9 LLM access

Endpoint: OpenRouter chat completions only, key in `OPENROUTER_API_KEY`. If organisers confirm a Grok key and `NAMESAKE_ALLOW_XAI=1` is set, an `xai-` prefix may route to the xAI API; otherwise stay on OpenRouter. Settings: `response_format` json_schema, temperature 0, fixed seed, bounded concurrency. Failure (no key, bad key, blocked provider) ⇒ reader-only path. Output is still valid, and U facts degrade to REVIEW. Model chosen by measurement, not by size.

## 6. Acceptance criteria (numbered, testable)

1. `system/run data/screening/dev output/dev.jsonl` exits 0 from any working directory; `validate.py` passes; every line passes the schema.
2. Runtime on dev is under 8 minutes with the LLM and under 2 minutes without it.
3. 0 unsafe clearances on the 50 practice labels, and 0 on the generator-twin set (7.1).
4. Engine vs reference checker (7.2): 0 unexplained disagreements on the 819 dev hits and on the twin set. Every explained one is logged in the register.
5. Reproducibility: 5 runs give identical `(decision, reason_code)` on every hit; a shuffle of every JSONL gives byte-identical output.
6. LLM-dependency rate (the share of decisions that change when the LLM is switched off) is ≤ 3% on dev. It is reported in the README.
7. Rewording invariance on the twin set: 0 flips into `DIFFERENT_ENTITY`, and ≥ 99% of decisions unchanged.
8. Directional tests: every mutation operator (7.1) flips the decision in the expected direction, 100% of the time.
9. On correct practice decisions: reason code 100%, customer record 100%, and evidence ⊆ the label's evidence ∪ the minimal proof.
10. `system/README.md` covers: architecture diagram, both-side resolution, evidence representation, determinism, model/prompts/parameters, measured time and cost, three real cases (a mismatch, a match, a review), and what is unknown.
11. Git history contains no `data/`, no `*.xlsx`, no traces and no keys. `system/run` is committed with the executable bit and LF line endings.
12. `ui/` builds (`tsc --noEmit`, `vite build`) and its Vitest suite covers the `UI_SPEC.md` acceptance checklist.

## 7. Build-time harness (never imported by `system/`)

### 7.1 Generator twin (`tools/twin/`)

Clone real dev alerts and apply mutation operators, one per policy branch. Each mutated case is labelled by the reference checker (7.2), never by the engine. Rewording: every free-text unit is reworded by 3–4 different LLMs; code checks that every entity token is preserved.

### 7.2 Reference checker (`tools/checker/`)

A second implementation of `POLICY.md`, written without reading the engine's code. Every disagreement is triaged as an engine bug, a checker bug, or a policy ambiguity (which goes into the register).

### 7.3 LLM jury (`tools/jury/`), optional

2–3 different models read `POLICY.md` and a hit's full evidence bundle. Used only to find clearances worth a human look. Their opinions alone never change code.

### 7.4 Dashboard (`tools/report/`)

Printed on every run: practice score with a bootstrap confidence interval; unsafe clearances (practice / twin); engine–checker disagreements; rewording invariance; 5-run flip rate; LLM-dependency rate; runtime and cost. Also exports UI data via `export_ui_data.py`.

## 8. Constraints

- `system/` uses the Python 3 standard library only and runs on Python 3.9+. Use `from __future__ import annotations`, no `match`, no runtime `X | Y` unions.
- The model is reached only through the endpoint in 5.9. No other network calls from `system/`.
- `system/` reads only the given folder and writes only the output file (plus traces when enabled).
- Nothing from dev goes into the code: no names, IDs, amounts or wording. The shipped tables (countries, demonyms) are general world data, credited in the README.
- Data is shared only through participant access. The demo UI runs locally and is never deployed with data.
- `ui/` may use npm packages (React, Tailwind, Motion, thesvg, Lucide). It never ships participant data in git.

## 9. Interpretation register (default readings)

| # | Ambiguity | Default | Why |
|---|---|---|---|
| I1 | Hit DOB from dobs vs profile sentence | Both count (union); snippets only when both are empty | P5 wording |
| I2 | Joined/split name match | Counts as one part covering both | P8 says so |
| I3 | Customer name used for agreement | Verified legal name if there is one; otherwise the record's full or preferred names and the screened name | P4 |
| I4 | Death date only in profile text | UNKNOWN (no clearance) | R3; profile text mentions other people's deaths |
| I5 | "Most recent" approved check | `checked_at` for KYC; the note's `created_at` | Data |
| I6 | Conflicting declared DOBs across merged records, no verified DOB | DOB UNKNOWN | R3 |
| I7 | Several persons, same decision | Give that decision; `customer_record_id` = AMBIGUOUS | P3 and labels |
| I8 | Reason code when several apply | Any applicable code; prefer the one whose proof is shortest | Policy: any accepted |
| I9 | Unmappable place in a note | Customer country set open ⇒ LOCATION_MISMATCH UNKNOWN | R3 |
| I10 | Note check with unclear polarity | Not evidence; "most recent approved" = UNKNOWN | R1 |
| I11 | No record fits an unlinked alert | Decide on screened details only; `customer_record_id` = null | Policy P9 |
| I12 | Placeholders "and the like" | Also NULL, NIL, TBD, DUMMY, X, XX, pure digits/punctuation | P8 |
| I13 | Several accepted snippets disagree | Union of their possible years (DOB_MISMATCH needs every year contradicted) | P6 |

Every row is a named constant in `system/namesake/interpret.py`, has a unit test, and is restated in the README with the evidence for it.

## 10. Out of scope

- Training or fine-tuning any model; embeddings; cross-encoders; third-party packages in `system/`.
- External data at runtime from `system/` (Tavily, registries, web).
- Letting an LLM make a decision, choose a reason code, or write the reason text.
- Static `string.Template` HTML as the shipping demo. The demo is the React app in `ui/` per `UI_SPEC.md`.
- Optimising `match_score` thresholds. `match_score` is name similarity, not identity.

## 11. Edge cases that must have tests

- An alert linked to a joint account with no screened details that choose ⇒ both persons decided ⇒ aggregation.
- An unlinked alert where several records fit and they merge into one person ⇒ one person, not AMBIGUOUS.
- A customer with no approved check ⇒ no `NAME_MISMATCH_VERIFIED`.
- A hit with only a year DOB and a customer with a full date in the same year ⇒ agree.
- An age-at-date that spans two years, with the customer in the second year ⇒ agree.
- A company hit: only `dobs` is an incorporation date; profile "established on…" wording is ignored for Time.
- Hit addresses whose last part is "International" or "Europe" ⇒ ignored.
- Country codes vs names vs nationality adjectives ⇒ one canonical key; territories kept separate.
- Truncated profile notes ⇒ parse what's there; nothing is inferred from the cut.
- A malformed record ⇒ that alert alone falls back to REVIEW; the run continues.

## 12. Plan (13:50 → 17:00)

| By | Engine owner | Checker owner | Third person |
|---|---|---|---|
| 14:30 | Loaders and indexes, P8, date intervals, P3 union-find, writer that emits all-REVIEW output; push | Decision table + checker skeleton (reads only POLICY.md) | Country/demonym gazetteer, token extractors |
| 15:15 | Checks + decision table + first full `dev.jsonl`; practice score; push | Checker over 819 hits ⇒ triage disagreements | Twin v1: mutation operators, no rewording |
| 16:00 | Readers + polarity gate + runtime LLM second opinion; reasons and evidence; push | Rewording into the twin; invariance and directional runs | Reason templates; React UI per `UI_SPEC.md` (Case, Queue, Run) |
| 16:40 | Freeze the engine; 5-run and shuffle tests; README with real numbers; final push of `output/dev.jsonl` | Final audit of every clearance | Video |

Cut order if late: first the runtime LLM second opinion, then twin rewording, then the jury. Never cut the reference checker or the unsafe-clearance audit.

## 13. Risks

| Risk | Answer |
|---|---|
| Unseen free text worded differently | Readers that ignore wording; twin rewording; the closed-world rule turns misses into REVIEW |
| Rejected checks written as notes (absent from dev) | Polarity gate plus a twin operator |
| The organisers' key blocks our provider, or is a Grok key | Key-prefix routing behind opt-in; reader-only path stays valid; LLM-dependency ≤ 3% |
| LLM nondeterminism | LLM only gives second opinions; disagreement ⇒ U, which never enables a clearance |
| Misreading POLICY.md | Two independent implementations + register |
| Order dependence | Sorted iteration, ID tie-breaks, shuffle test |
| One bad record crashes the run | Per-alert isolation, writer validation |

## 14. Research basis

Compile the SOP, don't prompt with it: AutoSOP, "Don't Prompt, Graph It" (NeurIPS 2026), 81.3% vs 61.0% on RuleArena. "Compile, Then Page" (arXiv 2607.11346, Jul 2026): compiled SOP text never significantly hurt, and gained up to 16 points.

Rules and LLMs fail differently: OpenSanctions Pairs (arXiv 2603.11051, Feb 2026). Rules over-match; LLMs fail on cross-script names and small date/identifier differences; pairwise matching is near its ceiling, so the gains are in the pipeline and in handling uncertainty.

LLM-written rules at build time: Kumar & Cohen, "Coding LLMs Can Be Harnessed to Learn Interpretable Models from Data" (arXiv 2610.14006, Sep 2026).

Rewording robustness: "Semantic Invariance in Agentic AI" (arXiv 2603.13173, Mar 2026). Scale doesn't predict robustness; Qwen3-30B-A3B was the most stable.

Temperature 0 isn't determinism: MarginGate (arXiv 2605.30218, May 2026). Output depends on batching.

Merging verified with hard vetoes, not blind transitive closure: "Entity Resolution in Practice" (arXiv 2607.26298, Jul 2026). Here the policy defines the merge edges exactly, so we use them as written and add nothing else.

Clustering and dedupe to cut LLM calls: LLM-CER, Zhejiang University (SIGMOD '26 / PVLDB 19).

LLM-labelled data for entity matching: Steiner & Bizer (arXiv 2606.28823, Jun 2026).

Classic techniques: N-version programming (the independent checker); certain answers over incomplete databases (the three-valued proof engine); why-provenance (the minimal evidence).
