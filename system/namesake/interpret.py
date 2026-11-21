"""Interpretation register — one named constant per SPEC row I1–I13."""

from __future__ import annotations

# I1: Hit DOB is union of structured dobs + first-paragraph birth facts.
# Snippets only when both are empty. Unparsed birth cue blocks snippets.
I1_HIT_DOB_UNION = "I1_HIT_DOB_UNION"

# I2: Joined/split name parts count as one part covering both tokens.
I2_JOINED_SPLIT_ONE_PART = "I2_JOINED_SPLIT_ONE_PART"

# I3: Agreement uses verified legal name when present; else full/preferred + screened.
# Login name finds the record; it does not confirm identity.
I3_VERIFIED_NAME_PREFERRED = "I3_VERIFIED_NAME_PREFERRED"

# I4: Death date only in profile prose → UNKNOWN (never enables DECEASED clearance).
I4_DEATH_PROSE_UNKNOWN = "I4_DEATH_PROSE_UNKNOWN"

# I5: Most recent approved check ordered by KYC checked_at / note created_at.
I5_MOST_RECENT_APPROVED = "I5_MOST_RECENT_APPROVED"

# I6: Conflicting declared DOBs across merged records with no verified DOB → UNKNOWN.
I6_CONFLICTING_DECLARED_DOB = "I6_CONFLICTING_DECLARED_DOB"

# I7: Several persons, same decision → emit it; customer_record_id = AMBIGUOUS.
I7_MULTI_PERSON_SAME_DECISION = "I7_MULTI_PERSON_SAME_DECISION"

# I8: Several applicable reason codes → any accepted; prefer shortest proof.
I8_SHORTEST_PROOF_CODE = "I8_SHORTEST_PROOF_CODE"

# I9: Unmappable place opens customer country set → LOCATION_MISMATCH UNKNOWN.
I9_UNMAPPABLE_PLACE_OPENS = "I9_UNMAPPABLE_PLACE_OPENS"

# I10: Unclear note polarity is not an approved check.
I10_UNCLEAR_POLARITY = "I10_UNCLEAR_POLARITY"

# I11: No record fits → decide on screened details; customer_record_id = null.
I11_NO_RECORD_NULL = "I11_NO_RECORD_NULL"

# I12: Extra placeholders beyond the policy's listed set.
I12_PLACEHOLDER_EXTRA = frozenset(
    {
        "NA",
        "N/A",
        "TEST",
        "UNKNOWN",
        "XXX",
        "NONE",
        "NULL",
        "NIL",
        "TBD",
        "DUMMY",
        "X",
        "XX",
    }
)

# I13: Several accepted snippets → union of years; DOB_MISMATCH needs every year contradicted.
I13_SNIPPET_YEAR_UNION = "I13_SNIPPET_YEAR_UNION"
