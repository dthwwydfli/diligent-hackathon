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

LLM off by default. If `OPENROUTER_API_KEY` is set, OpenRouter chat completions may second-guess free-text extracts (`temperature=0`, `seed=0`, JSON schema). Quotes must be substrings; disagreement marks the fact uncertain. Uncertain facts never enable a clearance. No other network calls.

Measured LLM-dependency rate: **0%** on this build (reader-only path; key unset during scoring).

## Time and cost

- Dev (819 hits), no LLM: ~20 seconds on this machine (under the 2-minute internal gate)
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
- Reason code 98%, customer record 100% on right decisions
