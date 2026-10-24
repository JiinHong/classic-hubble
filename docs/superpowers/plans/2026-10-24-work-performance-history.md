# Work Performance History Implementation Plan

**Goal:** Show connected upcoming and historical performances on work pages.

**Design:** Keep the existing upcoming-only selection contract for search and
watchlists. Opt the work detail query into all linked performances, then split
using the existing Seoul-date/status eligibility rule. The complementary list
is labelled "past/closed performances" because closed includes cancellations.
Sort that list by end date, then start date/time, newest first. Reuse existing
cards, preserve status/provenance, and opt into year-bearing dates on this page.
No database writes, OCR, matching or dependency changes.

## Tasks
- [x] Add failing query tests for history, Seoul midnight, ongoing series,
  closed future events, pagination, missing works and database failures.
- [x] Add failing page tests for both sections, counts, navigation and empties;
  test optional year-bearing card dates without changing existing defaults.
- [x] Implement opt-in history, partitioning and the two page sections.
- [x] Run web/shared tests, lint and production build; review the scoped diff.
- [ ] Verify the reported work in desktop/mobile browser views, then follow
  the existing GitHub/Vercel release path and verify the live work page.

## Verification
- Initial red run: 8 failures reproduced the missing history and year display.
- Full suite: 191 web tests and 19 shared tests pass; lint/build pass.
- Main-thread review: default selection unchanged, source programmes preserved,
  no client-side data-fetch waterfall or database writes added.
- Local browser: reported work shows upcoming 0 and past/closed 1, with the
  2024-11-24 PF253175 recital. Desktop 1280x900 and mobile 390x844 inspected;
  mobile content width equals viewport, poster loads, no overlapping text.
