-- Read-only integration check on a production-sized catalog. Inspect the RPC's
-- SQL body: EXPLAIN of the wrapper alone only reports "Function Scan".
begin;
set local role anon;
set local search_path='';
do $test$
declare
  query text; plan jsonb; scans text[];
begin
  select prosrc into strict query from pg_catalog.pg_proc
    where oid='public.concert_search_page(text,text,uuid[],text,integer)'::regprocedure;
  query:=regexp_replace(query,'\msearch_term\M','$1','g');
  query:=regexp_replace(query,'\mcity_name\M','$2','g');
  query:=regexp_replace(query,'\mmatched_work_ids\M','$3','g');
  query:=regexp_replace(query,'\mperiod_filter\M','$4','g');
  query:=regexp_replace(query,'\mpage_offset\M','$5','g');
  execute 'explain (analyze,format json) '||query into plan
    using '루트비히 판 베토벤'::text,'전체'::text,'{}'::uuid[],'all'::text,0;
  with recursive nodes(n) as (
    select plan->0->'Plan'
    union all select child from nodes cross join lateral jsonb_array_elements(n->'Plans') child
  )
  select array_agg(distinct n->>'Relation Name') into scans from nodes
  where n->>'Node Type'='Seq Scan' and n->>'Relation Name' in ('performances','works')
    and (n->>'Actual Loops')::int>0
    and (n->>'Actual Rows')::int+coalesce((n->>'Rows Removed by Filter')::int,0)>1000;
  if scans is not null then raise exception 'Selective composer query scanned full catalog tables: %',scans; end if;
end $test$;
rollback;
