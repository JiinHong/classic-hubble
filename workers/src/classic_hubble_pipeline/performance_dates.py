"""Conservative date-heading recognition shared by matching and publication."""

import re
from datetime import date

DATE_BINDING_VERSION = "concert-date-headings-v2"
_DATE = re.compile(
    r"(?:(20\d{2})\s*[./년]\s*)?(\d{1,2})\s*[./월]\s*(\d{1,2})(?!\d)"
)
_ENGLISH_DAY = (
    r"(?:Mon(?:day)?|Tue(?:s(?:day)?)?|Wed(?:nesday)?|Thu(?:r(?:s(?:day)?)?)?"
    r"|Fri(?:day)?|Sat(?:urday)?|Sun(?:day)?|TUR)"
)
_DAY = rf"(?:[월화수목금토일](?:요일)?|{_ENGLISH_DAY})"
_SUFFIX = re.compile(
    rf"\s*[.일]?\s*(?:\(\s*{_DAY}\s*\)|\[\s*{_DAY}\s*\]|{_ENGLISH_DAY}\b)",
    re.IGNORECASE,
)
_CONTINUATION = re.compile(r"(?:&|~|[-–—]|,|및|부터)\s*(?=\d)")


def _line_dates(line, fallback_year):
    found = set()
    remaining = line.strip()
    if not _DATE.match(remaining):
        return found
    while True:
        match = _DATE.match(remaining)
        if not match:
            raise ValueError("Incomplete date heading")
        suffix = _SUFFIX.match(remaining, match.end())
        if not suffix:
            raise ValueError("Unsupported date heading")
        year, month, day = (int(value) if value else None for value in match.groups())
        date(year or fallback_year or 2000, month, day)
        found.add((year, month, day))
        tail = remaining[suffix.end():]
        continuation = _CONTINUATION.search(tail)
        prefix = tail[:continuation.start()] if continuation else tail
        if _DATE.search(prefix):
            raise ValueError("Unseparated date heading")
        if not continuation:
            return found
        remaining = tail[continuation.end():]


def date_headings(lines, *, fallback_year=None):
    """Return (date tuples, has_invalid_heading), not corrected source text.

    Only leading headings count, never dates embedded in biography sentences.
    TUR is a literal observed poster typo, not a corrected or inferred date.
    A yearless heading inherits the target year or the sole explicit source year.
    """
    found, invalid = set(), False
    for line in lines:
        try:
            found.update(_line_dates(line, fallback_year))
        except ValueError:
            invalid = True
    years = {year for year, _, _ in found if year is not None}
    inferred_year = fallback_year or (next(iter(years)) if len(years) == 1 else None)
    return {(year or inferred_year, month, day) for year, month, day in found}, invalid
