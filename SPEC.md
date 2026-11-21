# SPEC: Namesake v3, "same person or not"

Track 2 (sanctions screening), Grok Bot London Financial Crime Hackathon, Sat 21 Nov 2026.
Code freeze 17:00 London.

**Status:** spec-anchored. Changes when the system changes. Tests in `tests/` and `tools/` tie them together.

**Source of truth:** `POLICY.md` and the organisers' files (`README.md`, `output.schema.json`, `validate.py`).
Where this spec disagrees with `POLICY.md`, the policy wins.

**Build rule:** write acceptance tests for a component before its code. Fixtures are synthetic. No dev IDs, names, or wording in `system/` or unit tests.

---

## Corrections vs the draft (policy / brief win)

1. **OpenRouter only.** Model calls go through OpenRouter with `OPENROUTER_API_KEY`. No direct xAI route. Bad or missing key → reader-only path.
2. **Location + name/DOB agree → REVIEW.** Location contradiction does not clear when name and DOB agree (`INSUFFICIENT_DATA`).
3. **Company legal forms stripped for companies only.** Placeholders still apply to people.
4. **Edit distance is Levenshtein.** A transposition is two edits. Shorter part's length picks the budget. Under 4 letters must be identical.
5. **Slash dates.** Day > 12 → DMY certain. Both ≤ 12 → uncertain; usable for confirmation only, never to enable a clearance.
6. **Death.** Only `deceased_date` before `screened_at` makes `DECEASED` true. Prose / `life_status` alone → UNKNOWN.
7. **Polarity without LLM.** Clean KYC notes (check date = `created_at`, parseable DOB/country/name, positive cue, no negative cue) are certain. Unclear polarity → UNKNOWN; cannot enable a clearance.
8. **Official time cap is 30 minutes.** Internal targets: under 2 minutes without LLM, under 8 with LLM.

---

## 1. Overview

For every watchlist hit decide `DIFFERENT_ENTITY`, `SAME_ENTITY`, or `REVIEW`, with a reason code, resolved customer record, 2–4 sentence reason, and decisive evidence IDs.

1. Resolve the customer (P2, P3, P4).
2. Resolve the listed person (P5).
3. Apply `POLICY.md` as a three-valued proof engine (P6, P7). Clear only on a certain contradiction.
4. Explain with minimal evidence (P9).

An LLM may help *read* free text. It never decides.

## 2. Scoring rules that drive defaults

| Truth \ We say | DIFFERENT_ENTITY | SAME_ENTITY | REVIEW |
|---|---|---|---|
| DIFFERENT_ENTITY | 0 | 3 | 3 |
| SAME_ENTITY | **60** | 0 | 2 |
| REVIEW | **60** | 2 | 0 |

- **R1.** Clear only on a certain contradiction (certainty C).
- **R2.** Confirm whenever the policy confirms.
- **R3.** Ambiguity that would enable a clearance → take the reading that does not clear.
- **R4.** Prefer preventing unsafe clearances.
- **R5.** Decision flips between runs cost twice (decisions + reproducibility).

## 3. I/O

`system/run <data folder> <output file>` from any cwd.

Reads: `alerts.jsonl`, `hits.jsonl`, `customers.jsonl`, `accounts.jsonl`, `onboarding.jsonl`,
`kyc_checks.jsonl`, `notes.jsonl`, `search_results.jsonl`, `name_variants.json`, `POLICY.md`.
Does not require `practice_labels.jsonl`.

Writes one JSON line per hit validating `output.schema.json`.
Traces only when `NAMESAKE_TRACE_DIR` is set.

## 4. Architecture

```
alerts → [A] resolve customer → Person(s)
hits   → [B] hit facts
notes / profile / snippets → [C] readers (+ optional LLM second opinion)
       → [D] three-valued checks
       → [E] decision table + multi-person aggregation
       → [F] minimal evidence + templated reason
       → [G] writer (always one valid line per hit)
```

## 5. Interpretation register

| # | Ambiguity | Default |
|---|---|---|
| I1 | Hit DOB sources | Union of `dobs` + first-paragraph birth; snippets only if both empty |
| I2 | Joined/split name | One part covering both |
| I3 | Customer name for agreement | Verified legal name if present; else full/preferred + screened |
| I4 | Death only in prose | UNKNOWN |
| I5 | Most recent approved check | KYC `checked_at`; note `created_at` |
| I6 | Conflicting declared DOBs, no verified | DOB UNKNOWN |
| I7 | Several persons, same decision | Emit decision; `customer_record_id` = `AMBIGUOUS` |
| I8 | Several reason codes | Any applicable; prefer shortest proof |
| I9 | Unmappable place in a note | Country set open → LOCATION_MISMATCH UNKNOWN |
| I10 | Unclear note polarity | Not evidence; most-recent-approved UNKNOWN |
| I11 | No record fits | Screened details only; `customer_record_id` = null |
| I12 | Placeholders | Also NULL, NIL, TBD, DUMMY, X, XX, digits/punctuation only |
| I13 | Several accepted snippets | Union of years; DOB_MISMATCH needs every year contradicted |

Named constants live in `system/namesake/interpret.py`. Each has a unit test.

## 6. Acceptance (numbered)

1. `system/run` exits 0 from any cwd; `validate.py` passes; schema OK.
2. Dev under 2 min without LLM; under 8 with LLM.
3. 0 unsafe clearances on practice (50) and twin.
4. Engine vs checker: 0 unexplained disagreements.
5. 5-run identical `(decision, reason_code)`; shuffle → byte-identical output.
6. LLM-dependency ≤ 3% on dev.
7. Rewording: 0 flips into DIFFERENT_ENTITY; ≥ 99% unchanged.
8. Every twin mutation flips in the expected direction.
9. On correct practice decisions: reason code 100%, customer record 100%, evidence ⊆ label ∪ proof.
10. `system/README.md` has architecture, both-side resolution, evidence, determinism, model, time, three cases, unknowns.
11. No `data/`, xlsx, traces, or keys in git. `system/run` is executable + LF.

## 7. Constraints

- `system/` = Python 3.9+ standard library only. `from __future__ import annotations`. No `match`, no runtime `X | Y`.
- Network only via OpenRouter when a key is present.
- Nothing from dev (names, IDs, amounts, wording) in shipped code.
- Gazetteer is general world data (mledoze/countries, ODbL), credited in README.

## 8. Out of scope

Training/fine-tuning, embeddings, third-party packages in `system/`, external runtime data,
LLM decisions, React UI, `match_score` tuning.
