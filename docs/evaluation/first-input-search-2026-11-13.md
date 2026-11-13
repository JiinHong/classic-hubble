# First-input search, 2026-11-13

Chrome used a new anonymous context per interaction, blocked service workers, disabled
the HTTP cache and issued Page.reload(ignoreCache=true). Navigation type had to be
reload. Times start at the matching input event (or Enter), not at page navigation,
and end one animation frame after a visible option (or completed results link).
The early-input test delayed scripts until after typing. It tests correctness under
that ordering, not the frequency of a production slow connection.

## Results before rollout

The baseline production site lost both early drafts (no request); the new local
production build retained both. First suggestions on the same Mac against the
same remote database, before/after: 쇼 3376/33 ms, 베토벤 545/18 ms, 라흐 피협 2번
429/48 ms, 차이 1373/52 ms, 바흐 1562/52 ms, 운명 1142/50 ms. Their visible option
labels and order matched. This group intentionally exercises the prepared list,
not a representative sample of all queries.

For submitted work search, A/B used the same optimized web build with two local
ports and the app's result cache disabled in both arms. Each of 11 terms was
submitted twice per arm on hard reload. Run order alternated, then term order
was reversed. Enter to first completed result: median 288 vs 224.5 ms; 16/22
pairs faster. Every total and every returned work slug and upcoming-show count
matched. Database page/connection caches were not flushed. The trial override
and trial database function were removed.

## Keeping the cache small

Run `pnpm --filter web refresh:suggestions` after editorial or ranking changes.
It fetches only public top-eight suggestions; there are no user histories, tokens,
upcoming counts or whole-catalog downloads. The build includes 45 exact keys
(5460 bytes gzipped as JSON). Treat these as provisional: a successful live
response, even an empty one, supersedes them. On a nonprepared key, narrow a
compatible visible list or use the ordinary lookup.

Short server lookups compute the best match while reading prefix hits rather
than normalizing every alias of every candidate. Three-character and longer
suggestions still use the original function. Submitted search retains the shared
TypeScript ranker; the SQL companion changes only how candidate IDs are found.
Run `supabase/tests/short_suggestion_parity.sql` for ordered anonymous-role checks.
Prior functions remain deployable, allowing an app rollback without dropping
catalog data, indexes, or old APIs.
