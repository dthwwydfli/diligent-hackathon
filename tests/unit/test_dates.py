"""Issue 2: date intervals. Expected values from POLICY P5/P6/P7, written before impl."""

from __future__ import annotations

from namesake.dates import (
    age_at_date_years,
    all_hit_dobs_contradicted,
    dob_contradicts,
    intervals_agree,
    parse_date,
    under_16_at,
    year_interval,
)


def test_iso_full() -> None:
    """ISO YYYY-MM-DD → certain day interval."""
    iv = parse_date("1988-03-14")
    assert iv is not None
    assert iv.certain
    assert iv.y_lo == 1988 and iv.m_lo == 3 and iv.d_lo == 14


def test_year_only() -> None:
    """P7: a birth year alone can agree with a full date."""
    year = parse_date("1988")
    full = parse_date("1988-03-14")
    assert year is not None and full is not None
    assert intervals_agree(full, year)
    assert intervals_agree(year, full)


def test_policy_age_example() -> None:
    """P5: aged 45 in March 2019 → 1973 or 1974."""
    assert age_at_date_years(45, 2019, 3) == [1973, 1974]


def test_slash_day_gt_12_certain_dmy() -> None:
    """SPEC: day > 12 forces DMY certain."""
    iv = parse_date("19/05/2004")
    assert iv is not None
    assert iv.certain
    assert (iv.y_lo, iv.m_lo, iv.d_lo) == (2004, 5, 19)


def test_slash_both_le_12_uncertain() -> None:
    """SPEC: both parts ≤ 12 → uncertain; read as DMY for confirmation only."""
    iv = parse_date("05/03/2004")
    assert iv is not None
    assert not iv.certain
    assert (iv.y_lo, iv.m_lo, iv.d_lo) == (2004, 3, 5)


def test_english_month_forms() -> None:
    assert parse_date("February 17, 1990") is not None
    assert parse_date("27 September 1991") is not None
    assert parse_date("March 2019") is not None


def test_dob_contradict_year_gap() -> None:
    """P6: customer year more than 1 outside hit → contradicted."""
    cust = parse_date("1988-03-14")
    hit = parse_date("1952")
    assert cust and hit
    assert dob_contradicts(cust, hit)


def test_within_one_year_blocks_contradiction_not_agreement() -> None:
    """P6: ±1 year is not a contradiction. P7: agreement needs the customer's year in the hit set."""
    cust = parse_date("1977-01-11")
    hit = year_interval(1976)
    assert cust
    assert not dob_contradicts(cust, hit)
    assert not intervals_agree(cust, hit)
    # Age-span set containing the customer year does agree
    assert intervals_agree(cust, year_interval(1977))


def test_same_year_different_month_contradicts() -> None:
    """P6: both give a month in the same year and months differ."""
    cust = parse_date("1988-03-14")
    hit = parse_date("1988-11")
    assert cust and hit
    assert dob_contradicts(cust, hit)
    assert not intervals_agree(cust, hit)


def test_one_agreeing_date_blocks_mismatch() -> None:
    """P6: one agreeing date prevents DOB_MISMATCH."""
    cust = parse_date("1977-01-11")
    hits = [parse_date("1950"), parse_date("1977")]
    assert cust and all(hits)
    assert not all_hit_dobs_contradicted(cust, hits)  # type: ignore[arg-type]


def test_every_hit_year_contradicted() -> None:
    cust = parse_date("1990-01-01")
    hits = [parse_date("1950"), parse_date("1960")]
    assert cust and all(hits)
    assert all_hit_dobs_contradicted(cust, hits)  # type: ignore[arg-type]


def test_under_16_every_reading() -> None:
    """P6 Time: under 16 at earliest report in every DOB reading."""
    # Born 2010, report 2020 → age 10, under 16
    cust = parse_date("2010-06-01")
    report = parse_date("2020-09-10")
    assert cust and report
    assert under_16_at(cust, report)
    # Born 1990, report 2020 → not under 16
    adult = parse_date("1990-06-01")
    assert adult and not under_16_at(adult, report)


def test_uncertain_slash_not_used_to_clear_years() -> None:
    """R1/SPEC: uncertain slash may support confirmation, never enable clearance alone.
    Certainty flag is False so callers can refuse clearance on it.
    """
    iv = parse_date("03/05/2001")
    assert iv is not None
    assert iv.certain is False
