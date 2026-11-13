-- Exercise the public role, including exact aliases, broad composer prefixes,
-- wildcards, whitespace, numeric catalogue fragments, and the long-query fallback.
begin;
set local role anon;
do $test$
declare
  term text;
  old_rows jsonb;
  new_rows jsonb;
begin
  foreach term in array array['베','브람','운명','드','말러','쇼','D','Op','1','12','a_','%','_','  바  ','','---','ㅂ','라흐 피협 2번','베토벤','없는작품'] loop
    select jsonb_agg(to_jsonb(s) - 'ordinality' order by ordinality) into old_rows
    from public.suggest_works(term) with ordinality s;
    select jsonb_agg(to_jsonb(s) - 'ordinality' order by ordinality) into new_rows
    from public.suggest_works_v2(term) with ordinality s;
    if old_rows is distinct from new_rows then raise exception 'suggestion order/content changed: %', term; end if;
  end loop;
end $test$;
do $test$ declare term text; begin
  foreach term in array array['베','베토벤','모차르트터키풍','차이','바흐','쇼','피아노','슈만숲의정경','말러','_','%','--','1','Concerto',''] loop
    if (select array_agg(id order by id) from public.search_work_candidates(term)) is distinct from
       (select array_agg(id order by id) from public.search_work_candidates_v2(term)) then
      raise exception 'candidate set changed: %',term;
    end if;
  end loop;
end $test$;
rollback;
