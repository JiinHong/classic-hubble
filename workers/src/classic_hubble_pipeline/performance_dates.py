"""Conservative date-heading recognition shared by matching and publication."""

import re
from datetime import date

DATE_BINDING_VERSION = "concert-date-headings-v4"
_DATE = re.compile(
    r"(?:(20\d{2})\s*[./년]\s*)?(\d{1,2})\s*[./월]\s*(\d{1,2})(?!\d)"
)
_ENGLISH_DAY = (
    r"(?:Mon(?:day)?|Tue(?:s(?:day)?)?|Wed(?:nesday)?|Thu(?:r(?:s(?:day)?)?)?"
    r"|Fri(?:day)?|Sat(?:urday)?|Sun(?:day)?|TUR)"
)
_DAY = rf"(?:[월화수목금토일](?:요일)?|{_ENGLISH_DAY})"
_SUFFIX = re.compile(
    rf"\s*[.일]?\s*(?:\(\s*({_DAY})\s*\)|\[\s*({_DAY})\s*\]|({_DAY})\b)",
    re.IGNORECASE,
)
_CONTINUATION = re.compile(r"(?:&|~|[-–—]|,|및|부터)\s*(?=\d)")
_WEEKDAYS = {day: index for index, day in enumerate(("mon", "tue", "wed", "thu", "fri", "sat", "sun"))}
_WEEKDAYS.update({day: index for index, day in enumerate("월화수목금토일")})


def _line_dates(line, fallback_year):
    found, invalid = set(), False
    remaining = line.strip()
    if not _DATE.match(remaining):
        return found, invalid
    while True:
        match = _DATE.match(remaining)
        if not match:
            raise ValueError("Incomplete date heading")
        suffix = _SUFFIX.match(remaining, match.end())
        if not suffix:
            raise ValueError("Unsupported date heading")
        year, month, day = (int(value) if value else None for value in match.groups())
        effective_year = year or fallback_year
        actual_date = date(effective_year or 2000, month, day)
        weekday = next(value for value in suffix.groups() if value).lower()
        weekday_number = _WEEKDAYS.get(weekday[:1] if weekday[0] in "월화수목금토일" else weekday[:3])
        if effective_year and weekday_number is not None and actual_date.weekday() != weekday_number:
            invalid = True
        found.add((year, month, day))
        tail = remaining[suffix.end():]
        continuation = _CONTINUATION.search(tail)
        prefix = tail[:continuation.start()] if continuation else tail
        if _DATE.search(prefix):
            raise ValueError("Unseparated date heading")
        if not continuation:
            return found, invalid
        remaining = tail[continuation.end():]


def date_headings(lines, *, fallback_year=None):
    """Return (date tuples, has_invalid_heading), not corrected source text.

    Only leading headings count, never dates embedded in biography sentences.
    TUR is a literal observed poster typo, not a corrected or inferred date.
    A yearless heading inherits the target year or the sole explicit source year.
    """
    lines = tuple(lines)
    found, invalid = set(), False
    for line in lines:
        try:
            dates, line_invalid = _line_dates(line, fallback_year)
            found.update(dates)
            invalid |= line_invalid
        except ValueError:
            invalid = True
    years = {year for year, _, _ in found if year is not None}
    inferred_year = fallback_year or (next(iter(years)) if len(years) == 1 else None)
    if inferred_year and fallback_year is None:
        # Recheck yearless headings once their source year is known.
        for line in lines:
            try:
                _, line_invalid = _line_dates(line, inferred_year)
                invalid |= line_invalid
            except ValueError:
                invalid = True
    return {(year or inferred_year, month, day) for year, month, day in found}, invalid
