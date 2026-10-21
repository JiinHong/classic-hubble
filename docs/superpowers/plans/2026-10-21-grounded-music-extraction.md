# Grounded Music Extraction

Approved unit 3 of the full-service plan. No LLM provider or API key is configured;
this unit prepares text-only requests and validates externally obtained responses.
It must not pretend to perform model inference or incur model charges.

1. Test and implement a strict, provider-independent response schema. Each field
   references an exact OCR quote and line ID. Preserve page identity. Reject
   invented evidence, foreign work IDs, oversized input and invalid states.
2. Reuse the canonical matcher for review suggestions. Biography/unknown entries
   and incomplete/arranged works cannot become full-work links. All output remains
   unverified, even when a catalogue match is unambiguous.
3. Add prepare/import commands for private R2 OCR evidence. Validate hashes and
   current source/OCR identity. Default to a read-only report; explicit apply
   stores immutable private evidence before private DB metadata. Identity includes
   the response, producer label and canonical catalogue snapshot. Never mutate
   program_items, publish results or trigger notifications.
4. Run negative tests first, full regression tests, a live read-only preparation,
   sequential review, CI and the existing main-branch deployment path.

Remaining prerequisites: choose/connect a text LLM; build a labelled evaluation
set; expand the current four-work catalogue; implement administrator approval and
semantic change publication. Exact quotes do not prove correct musical meaning or
program/biography classification. Prepare does not send data to a provider.

## Verification Progress

- Steps 1-3 implemented. New behavior was first exercised by failing tests.
- Sequential review found and fixed truncated catalogue evidence and separate-key
  matching that broke title/alias matches. Regression tests cover both.
- Local checks: 258 Python tests, 75 web/shared tests, scoped Ruff, ESLint and
  Next.js production build passed. Live read-only prepare processed 224 OCR lines.
- Step 4: CI and production deployment confirmation remain before delivery.
- No private candidate was imported into production for testing; no LLM was called.
