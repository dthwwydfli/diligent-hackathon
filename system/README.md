# Namesake

Track 2 — same person or not. Python 3.9+ standard library only.

## Architecture

```
alerts ──► resolve customer ──► Person(s) + verified facts
hits   ──► hit facts (fields, profile, accepted snippets)
notes  ──► token readers (optional LLM second opinion)
           │
           ▼
     three-valued checks ──► policy_table.json walk ──► reason + evidence ──► writer
```

`system/run <data folder> <output file>` works from any working directory.

## Both-side resolution

**Customer.** Follow `account_ref` / `login_handle` / `email`. Merge records that share a phone and the same full DOB, or the same document number on approved checks (transitive). Verified name/DOB/document country come from the latest approved KYC row or a KYC-channel note that passes the polarity gate.

**Hit.** Names from `name` / aliases / `best_matching_name`. DOBs from `dobs`, then the first paragraph of `profile_notes`, then accepted search snippets (sorted-name query + exact listing phrase + a country tied to the hit). Dated reports use the exact `According to …; <Month D, YYYY>:` form only.

## Evidence

Each output line cites the record IDs the proof used (customer / KYC / note / hit / search result). Not everything looked at.

## Determinism

- Sorted hit iteration, ID string tie-breaks
- `PYTHONHASHSEED=0` recommended
- Shuffle of every JSONL → byte-identical output (tested)

## Model

`OPENROUTER_API_KEY` unset → reader-only path, no network. With the key set, `LLMClient.second_opinion` runs on:

1. KYC-channel notes in `resolve._approved_checks_for_records` — vetoes rejected/failed/expired checks the reader mistook for approved, and fills missing name/DOB/country as uncertain.
2. Accepted search snippets in `hitfacts.accepted_snippet_years` — fills a missing age as uncertain.

Model: `qwen/qwen3-32b` (override with `NAMESAKE_MODEL`). `temperature=0`, `seed=0`, JSON schema, `provider.require_parameters: true`. Quotes must be substrings of the source text. The LLM never decides; uncertain facts never enable a clearance. The LLM can't cause a clearance; L4-style with/without-key diffs stay rules-only for DIFFERENT_ENTITY.

Committed `output/dev.jsonl` was regenerated with the key unset, so an organiser rerun without a key matches. One live OpenRouter call with the key set returned valid schema JSON (`qwen/qwen3-32b`). Measured LLM-dependency on the committed run: **0%** (reader-only).

## Time and cost

- Dev (819 hits), no LLM: ~21 seconds on this machine (under the 2-minute internal gate)
- Cost: $0 without a key

## Cases

| Kind | Hit | Decision | Why |
|---|---|---|---|
| Mismatch | `H-FF82BD` | `LOCATION_MISMATCH` | Closed customer country set does not overlap the hit |
| Match | `H-FC94A0` | `NAME_DOB_LOCATION_MATCH` | Name, DOB, and country agree; nothing contradicts |
| Review | `H-FF3096` | `INSUFFICIENT_DATA` | No certain contradiction and not enough agreement |

## Unknowns

Interpretation register I1–I13 in `SPEC.md` / `system/namesake/interpret.py`. Notable defaults: death only from `deceased_date` (I4); unmappable place opens the country set (I9); unclear note polarity is not an approved check (I10).

## Data credit

Country / demonym table derived from [mledoze/countries](https://github.com/mledoze/countries) (ODbL). Shipped under `system/namesake/data/countries.json`.

## Practice score (measured)

- 50/50 right decisions, **0 unsafe clearances**
- Decision score **100.0**
- Reason code 100%, customer record 100% on right decisions
