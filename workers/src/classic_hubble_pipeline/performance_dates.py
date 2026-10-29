"""Conservative date-heading recognition shared by matching and publication."""

import re
from datetime import date

DATE_BINDING_VERSION = "concert-date-headings-v20"
_EVENT_DATE_LABEL = re.compile(r"^\s*일\s*시\s*[:：|]?\s*(?=20\d{2})")
_DATE = re.compile(
    r"(?:(20\d{2})(?:\s*[./년]\s*|(?=\d{2}[./월])))?"
    r"(\d{1,2})\s*[./월]\s*(\d{1,2})(?!\d)"
)
_ENGLISH_DAY = (
    r"(?:Mon(?:day)?|Tue(?:s(?:day)?)?|Wed(?:nesday)?|Thu(?:r(?:s(?:day)?)?)?"
    r"|Fri(?:day)?|Sat(?:urday)?|Sun(?:day)?|TH|TUR)"
)
_DAY = rf"(?:[월화수목금토일](?:요일)?|{_ENGLISH_DAY})"
_BRACKET_DAY = rf"(?:{_DAY}|{_ENGLISH_DAY}\.)"
_SUFFIX = re.compile(
    rf"\s*[.일]?\s*(?:\(\s*({_BRACKET_DAY})\s*\)|\[\s*({_BRACKET_DAY})\s*\]|({_DAY})(?:\b|(?=\d{{1,2}}(?::\d{{2}}|\.\d{{2}}\s*(?:AM|PM)|\s*(?:AM|PM|시)))))",
    re.IGNORECASE,
)
_CONTINUATION = re.compile(r"(?:&|~|[-–—]|,|및|부터)\s*(?=\d)(?!\d+\s*번)")
_WEEKDAYS = {day: index for index, day in enumerate(("mon", "tue", "wed", "thu", "fri", "sat", "sun"))}
_WEEKDAYS.update({day: index for index, day in enumerate("월화수목금토일")})
_WEEKDAYS["th"] = 3
_CLOCK_ONLY = re.compile(
    r"\s*(?:\d{1,2}:\d{2}(?:\s*(?:AM|PM))?|\d{1,2}\s*(?:AM|PM))?\s*",
    re.IGNORECASE,
)
_DECIMAL_MERIDIEM_CLOCK = re.compile(
    r"\s*(\d{1,2})\.(\d{2})\s*(AM|PM)(?=\s|$|[&~,–—-])",
    re.IGNORECASE,
)
_FULL_DATE_CLOCK = re.compile(
    r"(20\d{2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})"
    r"(?:\s*\.\s*|\s+|\s*\.?\s*\(\s*\)\s*)"
    r"(\d{1,2})(?::(\d{2}))?(?:\s*(AM|PM))?",
    re.IGNORECASE,
)
_JOINED_CLOCK = re.compile(
    r"(\d{1,2})(?::(\d{2}))?(?:\s*(AM|PM))?(?!\s*(?:AM|PM))(?=\s|$|[&~,가-힣-])",
    re.IGNORECASE,
)
_VENUE_LINE = re.compile(r"[가-힣A-Za-z ·]{0,60}(?:관|홀|아트스페이스)")
_KOREAN_CLOCK = re.compile(r"(?:(오전|오후)\s*)?(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?")
_KOREAN_CLOCK_LIST = re.compile(
    rf"\s*{_KOREAN_CLOCK.pattern}(?:\s*(?:[,·ㆍ./&]|및)\s*{_KOREAN_CLOCK.pattern})*\s*"
)


def _valid_korean_clocks(text):
    if not _KOREAN_CLOCK_LIST.fullmatch(text):
        return False
    return all(
        (1 <= int(match[2]) <= 12 if match[1] else int(match[2]) <= 23)
        and (match[3] is None or int(match[3]) <= 59)
        for match in _KOREAN_CLOCK.finditer(text)
    )


def _bare_date(line):
    text = line.strip()
    match = _DATE.match(text)
    if not match or not match[1] or text[match.end():].strip() not in {"", ".", "일"}:
        return None
    parts = tuple(map(int, match.groups()))
    try:
        date(*parts)
    except ValueError:
        return None
    return parts


def _year_headings(lines):
    """Join a printed year only to adjacent month/day and weekday/clock lines."""
    index = 0
    while index < len(lines):
        line = lines[index]
        year = re.fullmatch(r"(20\d{2})\.?", line.strip())
        if year and index + 2 < len(lines):
            following = lines[index + 1].strip()
            match = _DATE.match(following)
            suffix = _SUFFIX.match(lines[index + 2])
            if (
                match and not match[1]
                and following[match.end():].strip() in {"", ".", "일"}
                and suffix and _valid_heading_clock(lines[index + 2][suffix.end():])
            ):
                yield year[1] + "." + following
                index += 2
                continue
        yield line
        index += 1


def _valid_heading_clock(text):
    if not text.strip():
        return True
    if _valid_korean_clocks(text):
        return True
    decimal = _DECIMAL_MERIDIEM_CLOCK.fullmatch(text.strip())
    if decimal:
        return 1 <= int(decimal[1]) <= 12 and int(decimal[2]) <= 59
    match = re.fullmatch(r"\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?\s*", text, re.IGNORECASE)
    if not match or not (match[2] or match[3]):
        return False
    hour = int(match[1])
    return (hour <= 23 and (match[2] is None or int(match[2]) <= 59)
            and (match[3] is None or 1 <= hour <= 12))


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
            if suffix and (
                _CLOCK_ONLY.fullmatch(following[suffix.end():])
                or _valid_korean_clocks(following[suffix.end():])
                or (_DECIMAL_MERIDIEM_CLOCK.fullmatch(following[suffix.end():].strip())
                    and _valid_heading_clock(following[suffix.end():]))
            ):
                yield stripped + " " + following.strip()
                continue
            # A poster may place up to two venue lines between its date and clock.
            if _bare_date(stripped):
                joined = None
                for next_index in range(index + 1, min(len(lines), index + 4)):
                    following = lines[next_index].strip()
                    suffix = _SUFFIX.match(following)
                    if suffix and next_index > index + 1:
                        clock = re.sub(r"^\s*at\s+", "", following[suffix.end():], flags=re.IGNORECASE)
                        if clock.strip() and _valid_heading_clock(clock):
                            joined = stripped + " " + following[:suffix.end()] + " " + clock
                            break
                    if not _VENUE_LINE.fullmatch(following):
                        break
                if joined:
                    yield joined
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
        weekday = next(value for value in suffix.groups() if value).lower().removesuffix(".")
        weekday_number = _WEEKDAYS.get(weekday[:1] if weekday[0] in "월화수목금토일" else weekday[:3])
        if effective_year and weekday_number is not None and actual_date.weekday() != weekday_number:
            invalid = True
        found.add((year, month, day))
        tail = remaining[suffix.end():]
        # AM/PM distinguishes a dotted time from another month/day heading.
        decimal = _DECIMAL_MERIDIEM_CLOCK.match(tail)
        if decimal:
            if not 1 <= int(decimal[1]) <= 12 or int(decimal[2]) > 59:
                raise ValueError("Invalid decimal heading clock")
            tail = tail[decimal.end():]
        # Explicit hour units distinguish a complete time list from later dates.
        if _KOREAN_CLOCK_LIST.fullmatch(tail):
            if not _valid_korean_clocks(tail):
                raise ValueError("Invalid Korean heading clock")
            return found, invalid
        if not decimal and suffix[3] and tail[:1].isdigit():
            clock = _JOINED_CLOCK.match(tail)
            if not clock:
                raise ValueError("Invalid joined heading clock")
            hour, minute = int(clock[1]), int(clock[2]) if clock[2] is not None else None
            if ((minute is None and clock[3] is None) or hour > 23
                    or (minute is not None and minute > 59) or (clock[3] and not 1 <= hour <= 12)):
                raise ValueError("Invalid joined heading clock")
        continuation = _CONTINUATION.search(tail)
        prefix = tail[:continuation.start()] if continuation else tail
        if _DATE.search(prefix):
            raise ValueError("Unseparated date heading")
        if not continuation:
            return found, invalid
        remaining = tail[continuation.end():]


def _without_history_timeline(lines):
    """Exclude a bounded, explicitly labelled year timeline, not arbitrary prose."""
    ignored = set()
    for start, line in enumerate(lines):
        if line.strip().casefold() != "history":
            continue
        for end in range(start + 1, min(len(lines), start + 201)):
            heading = re.sub(r"\s+", "", lines[end]).casefold()
            if heading not in {"program", "programme"}:
                continue
            years = {
                re.sub(r"\s+", "", value)
                for value in lines[start + 1:end]
                if re.fullmatch(r"20\d{2}(?:\s*[-~–]\s*20\d{2})?", value.strip())
            }
            if len(years) >= 2:
                ignored.update(range(start, end))
            break
    return tuple(line for index, line in enumerate(lines) if index not in ignored)


def date_headings(lines, *, fallback_year=None):
    """Return (date tuples, has_invalid_heading), not corrected source text.

    Only leading headings count, never dates embedded in biography sentences.
    TUR is a literal observed poster typo, not a corrected or inferred date.
    A yearless heading inherits the target year or the sole explicit source year.
    """
    # The printed event-date label is structural, not an arbitrary prose prefix.
    lines = tuple(_EVENT_DATE_LABEL.sub("", line) for line in lines)
    lines = _without_history_timeline(lines)
    lines = tuple(_wrapped_headings(tuple(_year_headings(lines))))
    found, invalid, bare_dates = set(), False, set()
    for index, line in enumerate(lines):
        bare = _bare_date(line)
        if bare:
            bare_dates.add(bare)
            invalid |= any(_SUFFIX.match(value.strip()) for value in lines[index + 1:index + 4])
            continue
        try:
            dates, line_invalid = _line_dates(line, fallback_year)
            found.update(dates)
            invalid |= line_invalid
        except ValueError:
            invalid = True
    years = {year for year, _, _ in found | bare_dates if year is not None}
    inferred_year = fallback_year or (next(iter(years)) if len(years) == 1 else None)
    if inferred_year and fallback_year is None:
        # Recheck yearless headings once their source year is known.
        for line in lines:
            if _bare_date(line):
                continue
            try:
                _, line_invalid = _line_dates(line, inferred_year)
                invalid |= line_invalid
            except ValueError:
                invalid = True
    resolved = {(year or inferred_year, month, day) for year, month, day in found}
    # A repeated bare date can corroborate, but never create, an event binding.
    return resolved, invalid or not bare_dates.issubset(resolved)
