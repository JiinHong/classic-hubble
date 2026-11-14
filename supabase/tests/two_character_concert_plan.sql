-- A two-character needle must not scan the entire trigram index.
begin;
set local role anon;
set local jit = off;
do $test$
declare body text; plan jsonb;
begin
  select prosrc into strict body from pg_proc where oid =
    'public.concert_search_page(text,text,uuid[],text,integer)'::regprocedure;
  body := replace(replace(replace(replace(replace(body, 'search_term', '$1'),
    'city_name','$2'),'matched_work_ids','$3'),'period_filter','$4'),'page_offset','$5');
  execute 'explain (analyze,format json) ' || body into plan
    using '슈만 헌정'::text,'전체'::text,'{}'::uuid[],'upcoming'::text,0;
  if exists(with recursive nodes(n) as (
    select plan->0->'Plan' union all
    select child from nodes cross join lateral jsonb_array_elements(n->'Plans') child
  ) select from nodes where n->>'Index Name' like '%literal_trgm'
    and (n->>'Actual Loops')::int>0)
  then raise exception 'two-character search used a trigram scan'; end if;
end $test$;
rollback;
