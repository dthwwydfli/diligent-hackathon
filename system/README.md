# Namesake

Sanctions screening: same person or not.

## Architecture

Stub. Filled in issue 13 from measured runs.

```
alerts → resolve customer → Person(s)
hits   → hit facts
       → three-valued checks → decision table → reason + evidence → writer
```

## Both-side resolution

Stub.

## Evidence

Stub.

## Determinism

`PYTHONHASHSEED=0`, sorted iteration, ID tie-breaks.

## Model

LLM off by default. OpenRouter second opinion only when `OPENROUTER_API_KEY` is set.

## Time and cost

Measured in issue 13.

## Cases

Measured in issue 13.

## Unknowns

See SPEC.md interpretation register I1–I13.
