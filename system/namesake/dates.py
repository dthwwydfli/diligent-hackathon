"""Date intervals. Partial dates are never filled in (POLICY: unknown stays unknown)."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from typing import List, Optional

MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


@dataclass(frozen=True)
class DateInterval:
    """Inclusive calendar interval. Missing month/day widen the range."""

    y_lo: int
    m_lo: int
    d_lo: int
    y_hi: int
    m_hi: int
    d_hi: int
    certain: bool = True
    source: str = ""

    def years(self) -> List[int]:
        return list(range(self.y_lo, self.y_hi + 1))


def _month_last(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def year_interval(year: int, certain: bool = True, source: str = "") -> DateInterval:
    return DateInterval(year, 1, 1, year, 12, 31, certain=certain, source=source)


def month_interval(year: int, month: int, certain: bool = True, source: str = "") -> DateInterval:
    return DateInterval(
        year, month, 1, year, month, _month_last(year, month), certain=certain, source=source
    )


def day_interval(
    year: int, month: int, day: int, certain: bool = True, source: str = ""
) -> DateInterval:
    return DateInterval(year, month, day, year, month, day, certain=certain, source=source)


def _valid_ymd(y: int, m: int, d: int) -> bool:
    if not (1 <= m <= 12):
        return False
    try:
        return 1 <= d <= _month_last(y, m)
    except Exception:
        return False


def precise_month(iv: DateInterval) -> Optional[int]:
    if iv.y_lo != iv.y_hi:
        return None
    if iv.m_lo == 1 and iv.d_lo == 1 and iv.m_hi == 12 and iv.d_hi == 31:
        return None
    if iv.m_lo == iv.m_hi:
        return iv.m_lo
    return None


def precise_day(iv: DateInterval) -> Optional[int]:
    mo = precise_month(iv)
    if mo is None or iv.y_lo != iv.y_hi:
        return None
    last = _month_last(iv.y_lo, mo)
    if iv.d_lo == 1 and iv.d_hi == last:
        return None
    if iv.d_lo == iv.d_hi:
        return iv.d_lo
    return None


def parse_date(raw: Optional[str], source: str = "") -> Optional[DateInterval]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    tag = source or text

    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if _valid_ymd(y, mo, d):
            return day_interval(y, mo, d, source=tag)

    m = re.fullmatch(r"(\d{4})-(\d{2})", text)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return month_interval(y, mo, source=tag)

    m = re.fullmatch(r"(\d{4})", text)
    if m:
        return year_interval(int(m.group(1)), source=tag)

    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _parse_slash(a, b, y, tag)

    m = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", text)
    if m:
        mo = MONTHS.get(m.group(1).lower())
        if mo:
            d, y = int(m.group(2)), int(m.group(3))
            if _valid_ymd(y, mo, d):
                return day_interval(y, mo, d, source=tag)

    m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if m:
        mo = MONTHS.get(m.group(2).lower())
        if mo:
            d, y = int(m.group(1)), int(m.group(3))
            if _valid_ymd(y, mo, d):
                return day_interval(y, mo, d, source=tag)

    m = re.fullmatch(r"([A-Za-z]+)\s+(\d{4})", text)
    if m:
        mo = MONTHS.get(m.group(1).lower())
        if mo:
            return month_interval(int(m.group(2)), mo, source=tag)

    return None


def _parse_slash(a: int, b: int, y: int, source: str) -> Optional[DateInterval]:
    # DMY preferred (UK-style data). Day > 12 forces DMY certain.
    if a > 12 and 1 <= b <= 12 and _valid_ymd(y, b, a):
        return day_interval(y, b, a, certain=True, source=source)
    if b > 12 and 1 <= a <= 12 and _valid_ymd(y, a, b):
        # Only MDY is calendar-valid; treat as certain MDY.
        return day_interval(y, a, b, certain=True, source=source)
    if 1 <= a <= 12 and 1 <= b <= 12 and _valid_ymd(y, b, a):
        # Both ≤ 12: uncertain. Read as DMY for confirmation only (SPEC).
        return day_interval(y, b, a, certain=False, source=source)
    return None


def find_dates(text: str) -> List[DateInterval]:
    """Every date written in the text, in left-to-right order.

    Longer forms win over a date inside them: "October 1997, day 28"
    is one day, not the month of October 1997.
    """
    if not text:
        return []
    specs = [
        (
            re.compile(
                r"\b([A-Za-z]+)\s+((?:19|20)\d{2}),?\s+day\s+(\d{1,2})\b",
                re.I,
            ),
            "month_year_day",
        ),
        (
            re.compile(
                r"\b(\d{1,2})(?:st|nd|rd|th)?\s+of\s+([A-Za-z]+),?\s+((?:19|20)\d{2})\b",
                re.I,
            ),
            "day_of_month",
        ),
        (
            re.compile(
                r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+((?:19|20)\d{2})\b",
                re.I,
            ),
            "day_month",
        ),
        (
            re.compile(
                r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+((?:19|20)\d{2})\b",
                re.I,
            ),
            "month_day",
        ),
        (re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"), "raw"),
        (re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b"), "raw"),
        (
            re.compile(r"\b([A-Za-z]+)\s+((?:19|20)\d{2})\b", re.I),
            "month_year",
        ),
    ]
    spans: List[tuple] = []
    for cre, kind in specs:
        for match in cre.finditer(text):
            if any(not (match.end() <= start or match.start() >= end) for start, end, _ in spans):
                continue
            interval = _interval_from_date_match(kind, match)
            if interval is not None:
                spans.append((match.start(), match.end(), interval))
    spans.sort(key=lambda item: item[0])
    return [interval for _, _, interval in spans]


def _interval_from_date_match(kind: str, match: re.Match) -> Optional[DateInterval]:
    if kind == "raw":
        return parse_date(match.group(0))
    if kind == "month_year_day":
        month = MONTHS.get(match.group(1).lower())
        year = int(match.group(2))
        day = int(match.group(3))
        if month and _valid_ymd(year, month, day):
            return day_interval(year, month, day)
        return None
    if kind == "day_of_month" or kind == "day_month":
        day = int(match.group(1))
        month = MONTHS.get(match.group(2).lower())
        year = int(match.group(3))
        if month and _valid_ymd(year, month, day):
            return day_interval(year, month, day)
        return None
    if kind == "month_day":
        month = MONTHS.get(match.group(1).lower())
        day = int(match.group(2))
        year = int(match.group(3))
        if month and _valid_ymd(year, month, day):
            return day_interval(year, month, day)
        return None
    if kind == "month_year":
        month = MONTHS.get(match.group(1).lower())
        year = int(match.group(2))
        if month:
            return month_interval(year, month)
    return None


def same_calendar_day(left: DateInterval, right: DateInterval) -> bool:
    """True when both intervals are the same precise day."""
    return (
        precise_day(left) is not None
        and precise_day(right) is not None
        and (left.y_lo, left.m_lo, left.d_lo) == (right.y_lo, right.m_lo, right.d_lo)
    )


def age_at_date_years(age: int, event_year: int, event_month: Optional[int] = None) -> List[int]:
    """Aged N at a date → two possible birth years (P5: aged 45 in March 2019 → 1973 or 1974)."""
    del event_month  # month does not change the two-year span the policy states
    return sorted({event_year - age, event_year - age - 1})


def intervals_agree(customer: DateInterval, hit: DateInterval) -> bool:
    """P7: customer's birth year is one of the hit's possible years;
    every part both give (month, day) is equal.
    """
    shared = set(customer.years()) & set(hit.years())
    if not shared:
        return False
    c_month = precise_month(customer)
    h_month = precise_month(hit)
    if c_month is not None and h_month is not None and c_month != h_month:
        return False
    c_day = precise_day(customer)
    h_day = precise_day(hit)
    if c_day is not None and h_day is not None and c_day != h_day:
        return False
    return True


def dob_contradicts(customer: DateInterval, hit: DateInterval) -> bool:
    """P6: customer's birth-year interval is more than 1 year outside the hit date,
    or both give a month in the same year and the months (or days) differ.
    """
    year_close = False
    for cy in customer.years():
        for hy in hit.years():
            if abs(cy - hy) <= 1:
                year_close = True
                break
        if year_close:
            break
    if not year_close:
        return True

    shared = set(customer.years()) & set(hit.years())
    c_month = precise_month(customer)
    h_month = precise_month(hit)
    if shared and c_month is not None and h_month is not None and c_month != h_month:
        return True
    c_day = precise_day(customer)
    h_day = precise_day(hit)
    if (
        shared
        and c_month is not None
        and h_month is not None
        and c_month == h_month
        and c_day is not None
        and h_day is not None
        and c_day != h_day
    ):
        return True
    return False


def all_hit_dobs_contradicted(customer: DateInterval, hit_dobs: List[DateInterval]) -> bool:
    """DOB_MISMATCH needs every hit birth date contradicted; one agreeing date prevents it."""
    if not hit_dobs:
        return False
    for hit in hit_dobs:
        if intervals_agree(customer, hit):
            return False
        if not dob_contradicts(customer, hit):
            return False
    return True


def under_16_at(customer: DateInterval, report: DateInterval) -> bool:
    """Under 16 at the report in every reading of the customer's DOB interval."""
    # Maximise age: earliest birth, latest report day.
    ry, rm, rd = report.y_hi, report.m_hi, report.d_hi
    by, bm, bd = customer.y_lo, customer.m_lo, customer.d_lo
    age = ry - by
    if (rm, rd) < (bm, bd):
        age -= 1
    return age < 16


def format_interval(iv: DateInterval) -> str:
    if precise_day(iv) is not None:
        return f"{iv.y_lo:04d}-{iv.m_lo:02d}-{iv.d_lo:02d}"
    if precise_month(iv) is not None:
        return f"{iv.y_lo:04d}-{iv.m_lo:02d}"
    if iv.y_lo == iv.y_hi:
        return str(iv.y_lo)
    return f"{iv.y_lo}–{iv.y_hi}"
