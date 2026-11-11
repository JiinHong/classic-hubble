-- A festival cover verifies the festival only. Both dated organizer and KOPIS
-- session texts must agree before the existing guarded publisher can write.
create function public.kopis_festival_session(r jsonb,a jsonb,sty text,day date)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare s text[]; ls text[]; t text[]; n int; i int; h text[]; start_m text[]; end_m text[]; st date; en date;
  wk text[]:=array['Mon','Tue','Wed','Thu','Fri','Sat','Sun']; dw int:=extract(isodow from day)::int;
  date_text text; hm text[]; yr int:=extract(year from day)::int; f int; ord text; k text[]; e text[]; x jsonb;
  w public.works; c public.composers; ko text; eng text; outp jsonb:='[]'; seen uuid[]:='{}';
begin
  if day is null or a->>'day' is distinct from day::text or jsonb_typeof(a->'rows') is distinct from 'array'
    or jsonb_typeof(a->'session') is distinct from 'array' or jsonb_typeof(r->'lines') is distinct from 'array'
    or r->>'coverage' is distinct from 'complete' or r->>'status' is distinct from 'text_extracted'
    or r->>'extraction_status' is distinct from 'no_program_identified' or r->'items' is distinct from '[]'::jsonb then return null;end if;
  n:=jsonb_array_length(a->'rows');
  if n not between 1 and 30 or jsonb_array_length(a->'session')<>10+2*n or jsonb_array_length(r->'lines')<>5
    or exists(select from jsonb_array_elements(r->'lines') l where l->>'page_index' is distinct from '0')
    or jsonb_typeof(a->'sources') is distinct from 'object' or (a->'sources')-'session'<>'{}'::jsonb
    or a#>>'{sources,session,url}' is distinct from 'https://www.iscm-korea.com/'||yr||'-PMF'
    or coalesce(a#>>'{sources,session,sha}','')!~'^[a-f0-9]{64}$' then return null;end if;
  s:=array(select jsonb_array_elements_text(a->'session'));ls:=array(select v->>'text' from jsonb_array_elements(r->'lines') v);
  if coalesce(sty,'')='' or octet_length(sty)>32000 or exists(select from unnest(s) z where z is null or z='' or z~E'[\n\r]')
     or encode(sha256(convert_to(array_to_string(s,E'\n'),'UTF8')),'hex') is distinct from a->>'session_sha' then return null;end if;
  t:=array(select btrim(regexp_replace(v,'[[:space:]]+',' ','g')) from unnest(string_to_array(sty,E'\n')) v where btrim(v,E' \t\r')<>'');
  h:=regexp_match(a->>'title','^(제([1-9][0-9]?)회 범음악제), 콘서트 [1-9][0-9]?\. (.+)$');
  start_m:=regexp_match(ls[2],'^([0-9]{4})\. ([0-9]{1,2})\. ([0-9]{1,2}) ([A-Z][a-z]{2})\.$');
  end_m:=regexp_match(ls[3],'^- ([0-9]{1,2})\. ([0-9]{1,2}) ([A-Z][a-z]{2})\.$');
  if h is null or start_m is null or end_m is null then return null;end if;
  st:=make_date(start_m[1]::int,start_m[2]::int,start_m[3]::int);en:=make_date(start_m[1]::int,end_m[1]::int,end_m[2]::int);
  f:=h[2]::int;ord:=case when f%100 between 11 and 13 then 'th' when f%10=1 then 'st' when f%10=2 then 'nd' when f%10=3 then 'rd' else 'th' end;
  if day not between st and en or wk[extract(isodow from st)::int]<>start_m[4] or wk[extract(isodow from en)::int]<>end_m[3]
    or ls[1] is distinct from h[1] or ls[4] is distinct from 'The '||f||ord||' PAN Music Festival'
    or ls[5] is distinct from '※ 상세 일정은 범음악제 홈페이지(QR) 참조 바랍니다.' then return null;end if;
  if s[1]<>yr||' PAN Music Festival' or not starts_with(s[2],'PAN Music Festival ') or right(s[2],length(h[3])+3)<>' - '||h[3]
    or not starts_with(s[3],'PMF Ensemble - ') or s[6+2*n]<>'장소 Venue' or s[9+2*n]<>'일시 Date'
    or a->>'venue' is distinct from s[7+2*n]||' ('||s[7+2*n]||')'
    or cardinality(t)<>3+2*n or t[1:3] is distinct from array['[PROGRAM]',s[4],s[5]] then return null;end if;
  hm:=regexp_match(a->>'schedule','^'||substr('월화수목금토일',dw,1)||'요일\((([01][0-9]|2[0-3]):[0-5][0-9])\)$');
  date_text:=yr||'년 '||extract(month from day)::int||'월 '||extract(day from day)::int||'일 ('||wk[dw]||') '||hm[1];
  if hm is null or s[10+2*n] is distinct from date_text then return null;end if;
  for i in 0..n-1 loop
    x:=a->'rows'->i;
    k:=regexp_match(t[4+2*i],'^([가-힣]{2,6}) - ([^<>]+) <([^<>]+)>(?: \(([0-9]{4})\))?$');
    e:=regexp_match(t[5+2*i],'^([A-Za-z][A-Za-z .''-]+) <([^<>]+)> ((?:for|on|für) [^<>]+)$');
    if k is null or e is null or coalesce(x->>'year','')!~'^[0-9]{4}$' or (k[4] is not null and k[4]<>x->>'year')
      or (t[4+2*i]||' '||t[5+2*i])~*'편곡|발췌|모음곡 중|\m(arranged|excerpt)\M' then return null;end if;
    if s[6+2*i] is distinct from k[1]||' '||k[2]||' < '||k[3]||' > ('||(x->>'year')||')'
      or s[7+2*i] is distinct from e[1]||' < '||e[2]||' > '||e[3] then return null;end if;
    ko:=k[2]||' '||k[3];eng:=e[2]||' '||e[3];
    select * into w from public.works where id=(x->>'work_id')::uuid for share;
    if not found or w.id=any(seen) or w.catalogue is not null or w.slug is distinct from x->>'slug' or w.title is distinct from eng
      or w.title_ko is distinct from ko or x->>'title' is distinct from eng or x->>'title_ko' is distinct from ko then return null;end if;
    select * into c from public.composers where id=w.composer_id for share;
    if not found or c.name is distinct from e[1] or c.name_ko is distinct from k[1] or c.name is distinct from x->>'composer' or c.name_ko is distinct from x->>'credit_ko'
      or exists(select from public.works w2 where w2.composer_id=c.id and w2.id<>w.id and (w2.title=eng or w2.title_ko=ko)) then return null;end if;
    seen:=array_append(seen,w.id);outp:=outp||jsonb_build_array(jsonb_build_object('position',i,'work_id',w.id,'display_title',ko,'composer_name',c.name,'performed_scope','unknown','scope_details','[]'::jsonb));
  end loop;return outp;
exception when data_exception then return null;
end $$;
revoke all on function public.kopis_festival_session(jsonb,jsonb,text,date) from public,anon,authenticated;
grant execute on function public.kopis_festival_session(jsonb,jsonb,text,date) to service_role;

do $migration$
declare
 def text:=pg_get_functiondef('public.publish_kopis_text_program(uuid,jsonb,jsonb)'::regprocedure);
 old text:=$old$  if public.kopis_text_cover(env->'reading',a,p.starts_on) is not true then return '{"status":"cover_binding_unverified","items":0}';end if;
  program:=public.kopis_text_program_items(d->>'sty',a);if program is null then return '{"status":"work_evidence_unverified","items":0}';end if;$old$;
 delta text:=$body$  if a->>'style'='iscm_bilingual_session' then
    program:=public.kopis_festival_session(env->'reading',a,d->>'sty',p.starts_on);
    if program is null then return '{"status":"festival_session_unverified","items":0}';end if;
    if p_expected is not null and p_document->>'live_session_sha' is distinct from a->>'session_sha' then return '{"status":"organizer_session_changed","items":0}';end if;
  else
$body$;
begin
 if length(def)-length(replace(def,old,''))<>length(old) then raise exception 'Unexpected typed programme validator';end if;
 execute replace(def,old,delta||old||E'\n  end if;');
end $migration$;
notify pgrst,'reload schema';
