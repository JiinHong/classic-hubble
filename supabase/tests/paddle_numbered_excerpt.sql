begin;
create function pg_temp.range_ref(parts text[]) returns jsonb language sql as $$
  select jsonb_build_object('context','program','scope','excerpt','key',null,'catalogue',null,
    'composer','[{"line_id":"L000029","quote":"프랑시스 풀랑크"}]'::jsonb,
    'title',jsonb_build_array(jsonb_build_object('line_id','L000030','quote','즉흥곡 '||array_to_string(parts,','))),
    'movements',(select jsonb_agg(jsonb_build_array(jsonb_build_object('line_id','L000030','quote',v)) order by i)
                 from unnest(parts) with ordinality u(v,i)))
$$;
do $$
declare
  c uuid; w uuid; r jsonb; bad jsonb; phrase text; family text := '프랑시스 풀랑크';
  provenance text := 'verified:https://catalogue.bnf.fr/ark:/12148/cb139840284';
begin
  if has_function_privilege('anon','public.paddle_numbered_excerpt(jsonb,text,text)','execute')
    or has_function_privilege('authenticated','public.paddle_numbered_excerpt(jsonb,text,text)','execute')
  then raise exception 'TEST: resolver is not private'; end if;
  select id into w from public.works where slug='poulenc-quinze-improvisations';
  if w is null then
    insert into public.composers(name,name_ko) values ('Francis Poulenc',family) returning id into c;
    insert into public.works(slug,title,composer_id) values
      ('poulenc-quinze-improvisations','Les Quinze Improvisations',c) returning id into w;
    insert into public.work_aliases(work_id,alias,source) values(w,'Fifteen Improvisations for piano',provenance);
  end if;
  foreach r in array array[pg_temp.range_ref(array['제7번~제12번']),pg_temp.range_ref(array['제1번~제6번','제13번~제15번'])] loop
    phrase := r#>>'{title,0,quote}';
    if public.paddle_numbered_excerpt(r,family,phrase) is distinct from w then raise exception 'TEST: missing parent'; end if;
    foreach bad in array array[
      r||'{"scope":"full_work"}',r||'{"context":"biography"}',r||'{"movements":[]}',r||'{"catalogue":[]}',r-'key',
      jsonb_set(r,'{movements,0,0,line_id}','"L000032"'),jsonb_set(r,'{composer,0,line_id}','"L000018"'),
      jsonb_set(r,'{movements,0,0,quote}','"제4번~제5번"'),jsonb_set(r,'{composer,0,quote}','"클로드 드뷔시"')
    ] loop
      if public.paddle_numbered_excerpt(bad,family,phrase) is not null then raise exception 'TEST: forged selection'; end if;
    end loop;
    if public.paddle_numbered_excerpt(r,family,phrase||' 연주하지 않음') is not null
      or public.paddle_numbered_excerpt(r,'이전 공연: '||family,phrase) is not null then raise exception 'TEST: partial line'; end if;
  end loop;
  foreach r in array array[
    pg_temp.range_ref(array['제1번~제6번']),pg_temp.range_ref(array['제12번~제7번']),
    pg_temp.range_ref(array['제7번~제16번']),pg_temp.range_ref(array['제1번~제15번']),
    pg_temp.range_ref(array['제7번~제12번','제12번~제15번']),pg_temp.range_ref(array['제13번~제15번','제1번~제6번']),
    pg_temp.range_ref(array['제0번~제12번']),pg_temp.range_ref(array['제7번~제12번 중 일부'])
  ] loop
    if public.paddle_numbered_excerpt(r,family,r#>>'{title,0,quote}') is not null then raise exception 'TEST: unsupported ranges'; end if;
  end loop;
  delete from public.work_aliases where work_id=w and source=provenance;
  r := pg_temp.range_ref(array['제7번~제12번']);
  if public.paddle_numbered_excerpt(r,family,r#>>'{title,0,quote}') is not null then raise exception 'TEST: missing authority'; end if;
end;
$$;
rollback;
select 'PASS: numbered selections require exact adjacent source lines and verified collection membership' as result;
