# Classic Hubble Product Plan

## MVP Positioning

Classic Hubble is a work-first discovery layer for classical concert booking. Users search for a composition, follow it, and receive alerts when the work appears in a new concert program.

## First Release Scope

- Work search: canonical works, Korean aliases, shorthand aliases, and composer names.
- Performance discovery: date, venue, booking status, price range, poster, artists, and booking URL.
- Program confidence: official, verified, OCR, estimated, and unknown states.
- Watchlist: logged-in users can follow works and choose email or web push.
- Admin review: low-confidence image/OCR matches enter a review queue.

## Data Pipeline

1. KOPIS sync stores raw performance and facility payloads.
2. Venue/NOL/detail pages enrich poster URLs and program images where allowed.
3. OCR/LLM extraction converts images into candidate program text.
4. Normalization matches candidates against the work alias database.
5. Low-confidence candidates are held for admin review.
6. Notification jobs compare approved program items with user watchlists.

## Product Details

- Search should accept colloquial Korean abbreviations such as `라흐 피협 2번`.
- Program items must always expose a confidence label.
- Booking links should keep the original ticketing source visible.
- Anonymous users can browse; login is required only when saving watchlists or receiving alerts.
- Admin review should show image, extracted text, suggested work, confidence, and approve/hold actions.

## Design Direction

The layout follows a ticketing-service mental model: search first, quick filters, dense cards, and a right rail for operational status. It should not visually clone NOL branding, colors, icons, or proprietary UI assets.
