begin;
do $test$
declare c uuid:=gen_random_uuid();w uuid:=gen_random_uuid(); d date:='2026-10-20';
 ls text[]:=array['리스트 서거 140년 기념음악회','리스트가 사랑한 시인들','제29회 한국성악예술학회 정기연주회','2026. 10. 20. TUE. 7:30 PM','세종체임버홀'];
 sec text[];a jsonb;r jsonb;rows jsonb;bad jsonb;sty text;
begin
 insert into public.composers(id,name) values(c,'Franz Liszt');
 insert into public.works(id,composer_id,slug,title,catalogue) values(w,c,'liszt-vocal-s315','Ich liebe dich','S. 315');
 sec:=array[ls[3]||' <'||ls[1]||' '||ls[2]||'>','기간 2026.10.20(화)','장소 세종체임버홀 위치보기','시간 19:30',
  '1. Ich liebe dich, S. 315 (F. Rückert) - Sop. 이소정','2. Freudvoll und Leidvoll, S. 280-1 (J. W. Goethe) - Sop. 이소정'];
 sty:='[PROGRAM]'||E'\n'||array_to_string(sec[5:],E'\n');
 a:=jsonb_build_object('title',ls[3],'venue','세종문화회관 (세종체임버홀)','schedule','화요일(19:30)','day',d,'session',sec,'session_sha',encode(sha256(convert_to(array_to_string(sec,E'\n'),'utf8')),'hex'),
  'sources',jsonb_build_object('venue',jsonb_build_object('url','https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?menuNo=200320&performIdx=37693','sha',repeat('a',64))),
  'rows',jsonb_build_array(jsonb_build_object('position',0,'work_id',w,'slug','liszt-vocal-s315','title','Ich liebe dich','composer','Franz Liszt','catalogue','S. 315')),'held','{"1":"specific_setting"}'::jsonb);
 r:=jsonb_build_object('status','text_extracted','coverage','complete','extraction_status','no_program_identified','items','[]'::jsonb,
  'lines',(select jsonb_agg(jsonb_build_object('page_index',0,'text',v)) from unnest(ls) v));
 if public.kopis_sejong_vocal(r,a,sty,d) is not null then raise exception 'missing catalogue provenance accepted';end if;
 insert into public.provider_records(provider,entity_type,provider_id,payload) values('catalogue_repair','canonical_work','liszt-vocal-s315',
  jsonb_build_object('work_id',w,'composer','Franz Liszt','title','Ich liebe dich','catalogue','S. 315','source_sha256',repeat('b',64),'source_url','https://www.hyperion-records.co.uk/mw.asp?mw=K9_C_Ind_1050_90'));
 rows:=public.kopis_sejong_vocal(r,a,sty,d);
 if jsonb_array_length(rows) is distinct from 1 or rows#>>'{0,work_id}' is distinct from w::text or rows#>>'{0,performed_scope}' is distinct from 'unknown' then raise exception 'lost verified song';end if;
 foreach bad in array array[a||'{"held":{}}',a||'{"day":"2026-10-21"}',a||'{"schedule":"화요일(07:30)"}',jsonb_set(a,'{rows,0,position}','1'),
    jsonb_set(a,'{rows,0,composer}','"F. Rückert"'),jsonb_set(a,'{rows,0,catalogue}','"S. 532"'),jsonb_set(a,'{sources,venue,url}','"https://example.org/"')] loop
  if public.kopis_sejong_vocal(r,bad,sty,d) is not null then raise exception 'wrong date, credit, or work accepted';end if;
 end loop;
 if has_function_privilege('anon','public.kopis_sejong_vocal(jsonb,jsonb,text,date)','execute') or has_function_privilege('authenticated','public.kopis_sejong_vocal(jsonb,jsonb,text,date)','execute') then raise exception 'public write permission';end if;
end $test$;
rollback;
select 'PASS: independently verified vocal identities, protected credits, dates and editions' as result;
