"""Conservative date-heading recognition shared by matching and publication."""

import re
from datetime import date

DATE_BINDING_VERSION = "concert-date-headings-v10"
_DATE = re.compile(
    r"(?:(20\d{2})(?:\s*[./년]\s*|(?=\d{2}[./월])))?"
    r"(\d{1,2})\s*[./월]\s*(\d{1,2})(?!\d)"
)
_ENGLISH_DAY = (
    r"(?:Mon(?:day)?|Tue(?:s(?:day)?)?|Wed(?:nesday)?|Thu(?:r(?:s(?:day)?)?)?"
    r"|Fri(?:day)?|Sat(?:urday)?|Sun(?:day)?|TH|TUR)"
)
_DAY = rf"(?:[월화수목금토일](?:요일)?|{_ENGLISH_DAY})"
_SUFFIX = re.compile(
    rf"\s*[.일]?\s*(?:\(\s*({_DAY})\s*\)|\[\s*({_DAY})\s*\]|({_DAY})(?:\b|(?=\d{{1,2}}:\d{{2}})))",
    re.IGNORECASE,
)
_CONTINUATION = re.compile(r"(?:&|~|[-–—]|,|및|부터)\s*(?=\d)")
_WEEKDAYS = {day: index for index, day in enumerate(("mon", "tue", "wed", "thu", "fri", "sat", "sun"))}
_WEEKDAYS.update({day: index for index, day in enumerate("월화수목금토일")})
_WEEKDAYS["th"] = 3
_CLOCK_ONLY = re.compile(
    r"\s*(?:\d{1,2}:\d{2}(?:\s*(?:AM|PM))?|\d{1,2}\s*(?:AM|PM))?\s*",
    re.IGNORECASE,
)
_FULL_DATE_CLOCK = re.compile(
    r"(20\d{2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})"
    r"(?:\s*\.\s*|\s+|\s*\.?\s*\(\s*\)\s*)"
    r"(\d{1,2})(?::(\d{2}))?(?:\s*(AM|PM))?",
    re.IGNORECASE,
)
_JOINED_CLOCK = re.compile(
    r"(\d{1,2}):(\d{2})(?:\s*(AM|PM))?(?!\s*(?:AM|PM))(?=\s|$|[&~,가-힣-])",
    re.IGNORECASE,
)


def _wrapped_headings(lines):
    """Recognize adjacent date/weekday lines without changing source evidence."""
    for index, line in enumerate(lines):
        stripped = line.strip()
        if _FULL_DATE_CLOCK.fullmatch(stripped) and index + 1 < len(lines):
            following = lines[index + 1]
            suffix = _SUFFIX.match(following)
            if suffix:
                # This extra layout is unsupported; keep the weekday visible
                # to validation instead of accepting a possible contradiction.
                yield stripped + " " + following.strip()
                continue
        match = _DATE.match(stripped)
        if (
            match and match[1] and stripped[match.end():].strip() in {"", ".", "일"}
            and index + 1 < len(lines)
        ):
            following = lines[index + 1]
            suffix = _SUFFIX.match(following)
            if suffix and _CLOCK_ONLY.fullmatch(following[suffix.end():]):
                yield stripped + " " + following.strip()
                continue
        yield line


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
            clock = _FULL_DATE_CLOCK.fullmatch(remaining)
            if clock:
                year, month, day, hour = map(int, clock.groups()[:4])
                minute, meridiem = clock[5], clock[6]
                date(year, month, day)
                if ((minute is None and meridiem is None)
                        or hour > 23 or (minute is not None and int(minute) > 59)
                        or (meridiem and not 1 <= hour <= 12)):
                    raise ValueError("Invalid heading clock")
                found.add((year, month, day))
                return found, invalid
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
        if suffix[3] and tail[:1].isdigit():
            clock = _JOINED_CLOCK.match(tail)
            if not clock:
                raise ValueError("Invalid joined heading clock")
            hour, minute = int(clock[1]), int(clock[2])
            if hour > 23 or minute > 59 or (clock[3] and not 1 <= hour <= 12):
                raise ValueError("Invalid joined heading clock")
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
    lines = tuple(_wrapped_headings(tuple(lines)))
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
