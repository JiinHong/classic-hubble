-- A venue programme supplies the set list; the saved poster supplies the event identity only.
create function public.kopis_sejong_vocal(r jsonb,a jsonb,sty text,day date)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare ls text[]; sess text[]; t text; numbered text[]:='{}'; wk int:=extract(isodow from day)::int;
  weekdays text[]:=array['MON','TUE','WED','THU','FRI','SAT','SUN']; k text:=substr('월화수목금토일',wk,1); clock text[];
  n int;i int;lastidx int:=-1;rowp jsonb;seen uuid[]:='{}';slots text[]:='{}';outp jsonb:='[]';
  w public.works;c public.composers;rec jsonb;m text[];num text;ttl text;
  pat text:='^[1-9][0-9]?\. ([A-Za-zÀ-ÖØ-öø-ÿ''’!, .-]{2,120}), S\. ([1-9][0-9]{1,3})(-[12]|, No\. *[1-9])?(?: \([A-Za-zÀ-ÖØ-öø-ÿ. ]+\))?[[:space:]]*[-–][[:space:]]*(?:Ten|Sop|Bar)\. [가-힣]{2,6}$';
begin
  if day is null or a->>'day' is distinct from day::text or coalesce(sty,'')='' or octet_length(sty)>32000
    or jsonb_typeof(a->'session') is distinct from 'array' or jsonb_typeof(a->'rows') is distinct from 'array'
    or jsonb_typeof(a->'held') is distinct from 'object' or jsonb_typeof(a->'sources') is distinct from 'object'
    or (a->'sources')-'venue'<>'{}'::jsonb or coalesce(a#>>'{sources,venue,url}','')!~'^https://www\.sejongpac\.or\.kr/portal/performance/performance/performTicket\.do\?menuNo=200320&performIdx=[1-9][0-9]{0,7}$'
    or coalesce(a#>>'{sources,venue,sha}','')!~'^[a-f0-9]{64}$' or r->>'coverage' is distinct from 'complete'
    or r->>'status' is distinct from 'text_extracted' or r->>'extraction_status' is distinct from 'no_program_identified'
    or r->'items' is distinct from '[]'::jsonb or jsonb_typeof(r->'lines') is distinct from 'array' then return null;end if;
  if jsonb_array_length(r->'lines')<>5 or exists(select from jsonb_array_elements(r->'lines') l where l->>'page_index' is distinct from '0') then return null;end if;
  ls:=array(select l->>'text' from jsonb_array_elements(r->'lines') l);sess:=array(select jsonb_array_elements_text(a->'session'));
  if array_position(ls,null) is not null or array_position(sess,null) is not null or cardinality(sess) not between 5 and 64
    or exists(select from unnest(sess) v where v='' or v~E'[\r\n]') or encode(sha256(convert_to(array_to_string(sess,E'\n'),'UTF8')),'hex') is distinct from a->>'session_sha'
    or ls[3] is distinct from a->>'title' or ls[5]<>'세종체임버홀' or a->>'venue' is distinct from '세종문화회관 ('||ls[5]||')'
    or ls[1]!~'^리스트 (서거|탄생) [1-9][0-9]{0,2}년 기념음악회$' or ls[2]<>'리스트가 사랑한 시인들' then return null;end if;
  clock:=regexp_match(a->>'schedule','^'||k||'요일\((([01][0-9]|2[0-3]):([0-5][0-9]))\)$');
  if clock is null or ls[4] is distinct from format('%s. %s. %s. %s. %s:%s %s',extract(year from day)::int,extract(month from day)::int,extract(day from day)::int,
      weekdays[wk],(clock[2]::int+11)%12+1,clock[3],case when clock[2]::int<12 then 'AM' else 'PM' end)
    or sess[1:4] is distinct from array[ls[3]||' <'||ls[1]||' '||ls[2]||'>','기간 '||to_char(day,'YYYY.MM.DD')||'('||k||')','장소 '||ls[5]||' 위치보기','시간 '||clock[1]] then return null;end if;
  if split_part(sty,E'\n',1)<>'[PROGRAM]' or cardinality(string_to_array(sty,E'\n'))>200 then return null;end if;
  foreach t in array (string_to_array(sty,E'\n'))[2:] loop
    t:=replace(btrim(t,E'\r\t '),chr(8203),'');
    if t='' or t~'^(<[12]부>|Intermiss(i)?on|(이탈리아|프랑스|독일) 시인 [“”가-힣, ]+([[:space:]]*[-–][[:space:]]*Acc\. [가-힣, ]+)?|Acc\. [가-힣, ]+)$' then continue;end if;
    if t!~pat or t=any(numbered) then return null;end if;numbered:=array_append(numbered,t);
  end loop;
  n:=cardinality(numbered);
  if numbered is distinct from sess[5:] or jsonb_array_length(a->'rows') not between 1 and n then return null;end if;
  for rowp in select value from jsonb_array_elements(a->'rows') loop
    if jsonb_typeof(rowp->'position') is distinct from 'number' or coalesce(rowp->>'position','')!~'^(0|[1-9][0-9]?)$' then return null;end if;
    i:=(rowp->>'position')::int;if i<=lastidx or i>=n then return null;end if;lastidx:=i;
    m:=regexp_match(numbered[i+1],pat);if m is null or m[3] is not null then return null;end if;
    num:=m[2];ttl:=replace(m[1],'’','''');
    select * into w from public.works where id=(rowp->>'work_id')::uuid for share;
    if not found or w.id=any(seen) or w.slug is distinct from 'liszt-vocal-s'||num or w.slug is distinct from rowp->>'slug' or w.title is distinct from ttl
      or w.title is distinct from rowp->>'title' or w.catalogue is distinct from 'S. '||num or w.catalogue is distinct from rowp->>'catalogue' then return null;end if;
    select * into c from public.composers where id=w.composer_id for share;
    if not found or c.name is distinct from 'Franz Liszt' or c.name is distinct from rowp->>'composer'
      or exists(select from public.works v where v.composer_id=c.id and v.id<>w.id and (v.title=ttl or v.catalogue=w.catalogue)) then return null;end if;
    select payload into rec from public.provider_records where provider='catalogue_repair' and entity_type='canonical_work' and provider_id=w.slug for share;
    if not found or rec->>'work_id' is distinct from w.id::text or rec->>'composer' is distinct from c.name or rec->>'title' is distinct from ttl
      or rec->>'catalogue' is distinct from w.catalogue or coalesce(rec->>'source_sha256','')!~'^[a-f0-9]{64}$'
      or coalesce(rec->>'source_url','')!~'^https://www\.hyperion-records\.co\.uk/(mw|dw)\.asp\?[A-Za-z0-9_=]+$' then return null;end if;
    seen:=array_append(seen,w.id);slots:=array_append(slots,i::text);
    outp:=outp||jsonb_build_array(jsonb_build_object('position',i,'work_id',w.id,'composer_name',c.name,'display_title',m[1],'performed_scope','unknown','scope_details','[]'::jsonb));
  end loop;
  if exists(select from generate_series(0,n-1) j where (j::text=any(slots))=(a->'held' ? j::text))
     or (select count(*) from jsonb_object_keys(a->'held'))<>n-cardinality(slots) then return null;end if;
  return outp;
exception when data_exception then return null;
end $$;
revoke all on function public.kopis_sejong_vocal(jsonb,jsonb,text,date) from public,anon,authenticated;
grant execute on function public.kopis_sejong_vocal(jsonb,jsonb,text,date) to service_role;

do $migration$
declare def text:=pg_get_functiondef('public.publish_kopis_text_program(uuid,jsonb,jsonb)'::regprocedure);
old text:=$o$  if a->>'style'='iscm_bilingual_session' then$o$;
delta text:=$v$  if a->>'style'='sejong_numbered_liszt_songs' then
    program:=public.kopis_sejong_vocal(env->'reading',a,d->>'sty',p.starts_on);
    if program is null then return '{"status":"vocal_program_unverified","items":0}';end if;
    if p_expected is not null and p_document->>'live_session_sha' is distinct from a->>'session_sha' then return '{"status":"organizer_session_changed","items":0}';end if;
  elsif a->>'style'='iscm_bilingual_session' then$v$;
begin
  if length(def)-length(replace(def,old,''))<>length(old) then raise exception 'Unexpected guarded programme validator';end if;
  execute replace(def,old,delta);
end $migration$;
notify pgrst,'reload schema';
