-- Return the start of a single programme with an independently corroborated date, time and venue.
create function public.direct_movement_program_section(r jsonb, detail jsonb, target date) returns integer
language plpgsql immutable security invoker set search_path='' as $$
declare
  ls jsonb:=r->'lines'; s text; m text[]; tm text[]; i int; heading int; anchor int; hh int; mm int; weekday int;
  day_ko text; day_en text; token text; venue text; hall text; venue_seen boolean:=false; tail text;
begin
  if target is null or r->>'status' is distinct from 'text_extracted' or r->>'coverage' is distinct from 'complete'
    or r->>'extraction_status' is distinct from 'items_extracted' or jsonb_typeof(ls) is distinct from 'array'
    or jsonb_array_length(ls) not between 5 and 250 or detail->>'prfpdfrom' is distinct from to_char(target,'YYYY.MM.DD')
    or detail->>'prfpdto' is distinct from detail->>'prfpdfrom' then return null;end if;
  weekday:=extract(isodow from target)::int;day_ko:=substr('월화수목금토일',weekday,1);
  day_en:=(array['MON','TUE','WED','THU','FRI','SAT','SUN'])[weekday];
  m:=regexp_match(detail->>'fcltynm','^([^()]+) \(([^()]+)\)$');
  if m is null then return null;end if;
  venue:=replace(regexp_replace(m[1],' \[[^][]+\]$',''),' ','');hall:=replace(m[2],' ','');
  if coalesce(venue,'')='' or coalesce(hall,'')='' then return null;end if;
  if venue<>hall then venue:=venue||hall;end if;
  for i in 0..jsonb_array_length(ls)-1 loop
    s:=btrim(ls->i->>'text');
    if ls->i->>'page_index' is distinct from '0' or coalesce(s,'')='' then return null;end if;
    if lower(s) in ('program','programme','프로그램') then
      if heading is not null or anchor is null or not venue_seen then return null;end if;
      heading:=i;continue;
    end if;
    if s ~* '(예매|티켓|판매|판매처|예약|프로필|취소|변경|다른 공연|프로그램 해설|공연 이력|ticket|booking|on sale|biograph|profile|program(me)? notes|other concert|cancelled|rescheduled)'
      then return null;end if;
    m:=regexp_match(s,'^(20[0-9]{2}) *\. *([0-9]{1,2}) *\. *([0-9]{1,2})\.? *(\([월화수목금토일]\)|\[[월화수목금토일]\]|MON|TUE|WED|THU|TUR|FRI|SAT|SUN)\.? +(.+)$','i');
    if m is not null then
      if heading is not null or anchor is not null or make_date(m[1]::int,m[2]::int,m[3]::int)<>target then return null;end if;
      token:=upper(translate(m[4],'()[]',''));
      if token<>day_ko and token<>day_en and not(token='TUR' and day_en='THU') then return null;end if;
      tail:=m[5];
      tm:=regexp_match(tail,'^([0-9]{1,2}):([0-9]{2}) *(AM|PM)?( +(.+))?$','i');
      if tm is not null then
        hh:=tm[1]::int;mm:=tm[2]::int;
        if hh>23 or mm>59 or (tm[3] is not null and hh not between 1 and 12) then return null;end if;
        if tm[3] is not null then hh:=hh%12+case upper(tm[3]) when 'PM' then 12 else 0 end;end if;
        tail:=btrim(coalesce(tm[5],''));
      else
        tm:=regexp_match(tail,'^(오전|오후|저녁) *([0-9]{1,2})시( *([0-9]{1,2})분)?( +(.+))?$');
        if tm is null or tm[2]::int not between 1 and 12 or coalesce(tm[4]::int,0)>59 then return null;end if;
        hh:=tm[2]::int%12+case when tm[1]='오전' then 0 else 12 end;mm:=coalesce(tm[4]::int,0);tail:=btrim(coalesce(tm[6],''));
      end if;
      if detail->>'dtguidance' is distinct from day_ko||'요일('||lpad(hh::text,2,'0')||':'||lpad(mm::text,2,'0')||')'
        or (tail<>'' and replace(tail,' ','')<>venue) then return null;end if;
      anchor:=i;venue_seen:=tail<>'';continue;
    end if;
    if anchor is not null and heading is null and replace(s,' ','')=venue then venue_seen:=true;end if;
    if s ~* '([12][0-9]{3} *[년./-] *[0-9]{1,2} *[월./-] *[0-9]{1,2}|[0-9] *월 *[0-9]|(^|[^0-9])([1-9]|0[1-9]|1[012]) *[/\-] *[0-3]?[0-9]([^0-9]|$)|^[[:space:]]*[0-9]{1,2} *\. *[0-9]{1,2}([[:space:]]|$)|(^|[^a-z])(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|aug(ust)?|sep(t(ember)?)?|oct(ober)?|nov(ember)?|dec(ember)?)[ .,]+[0-9]|[0-9]{1,2}(st|nd|rd|th)?[ .]+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))'
      then return null;end if;
  end loop;
  return heading;
exception when data_exception then return null;
end $$;

-- Render the literal fields again from the signed reading's line references.
create function public.direct_movement_citations(r jsonb, ref jsonb, start_line int) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare
  ls jsonb:=r->'lines'; field text; groups jsonb; spans jsonb; q jsonb; v text; s text; i int;
  parts text[]; rendered jsonb; result jsonb:='{}'; prev_move int:=-1; title_line int; next_title int; pos int;
begin
  if start_line is null or ref->>'context' is distinct from 'program' or jsonb_typeof(ref->'movements') is distinct from 'array'
    or jsonb_array_length(ref->'movements') not between 1 and 50 then return null;end if;
  foreach field in array array['composer','title','catalogue','key','movements'] loop
    if field='key' and ref->field='null'::jsonb then result:=result||jsonb_build_object(field,null);continue;end if;
    groups:=case when field='movements' then ref->field else jsonb_build_array(ref->field) end;
    rendered:='[]';
    for spans in select value from jsonb_array_elements(groups) loop
      if jsonb_typeof(spans) is distinct from 'array' or jsonb_array_length(spans) not between 1 and 8 then return null;end if;
      parts:='{}';
      for q in select value from jsonb_array_elements(spans) loop
        if coalesce(q->>'line_id','')!~'^L[0-9]{6}$' then return null;end if;
        i:=substr(q->>'line_id',2)::int; v:=q->>'quote'; s:=ls->i->>'text';
        pos:=strpos(s,v);
        if i<=start_line or coalesce(v,'')='' or s is null or pos=0
          or (v~'^[a-zA-Z0-9]' and pos>1 and substring(s from pos-1 for 1) ~ '[a-zA-Z0-9]')
          or (v~'[a-zA-Z0-9]$' and substring(s from pos+length(v) for 1) ~ '[a-zA-Z0-9]')
          then return null;end if;
        if field='title' then
          title_line:=i;
          select min(substr(w->>'line_id',2)::int) into next_title
          from jsonb_array_elements(r->'items') other cross join lateral jsonb_array_elements(other->'title') w
          where other<>ref and other->>'context'='program' and w->>'line_id'~'^L[0-9]{6}$' and substr(w->>'line_id',2)::int>=i;
        end if;
        if field='movements' then
          if i<title_line or i<prev_move or (next_title is not null and i>=next_title) then return null;end if;prev_move:=i;
        end if;
        if not v=any(parts) then parts:=array_append(parts,v);end if;
      end loop;
      rendered:=rendered||jsonb_build_array(array_to_string(parts,' '));
    end loop;
    result:=result||jsonb_build_object(field,case when field='movements' then rendered else rendered->0 end);
  end loop;
  return result;
exception when data_exception then return null;
end $$;

create function public.direct_printed_composer(printed text,full_name text,korean text) returns boolean
language plpgsql immutable security invoker set search_path='' as $$
declare
  p text[]; f text[]; i int; n int;
begin
  if coalesce(btrim(printed),'')='' then return false;end if;
  if lower(btrim(printed))=lower(full_name) or lower(btrim(printed))=lower(korean) then return true;end if;
  p:=regexp_split_to_array(lower(btrim(printed)),'[[:space:]]+');f:=regexp_split_to_array(lower(btrim(full_name)),'[[:space:]]+');n:=cardinality(p);
  if n<2 or n is distinct from cardinality(f) or p[n] is distinct from f[n] then return false;end if;
  for i in 1..n-1 loop
    if p[i]<>f[i] and not(p[i]~'^[a-z]\.$' and left(p[i],1)=left(f[i],1)) then return false;end if;
  end loop;
  return true;
end $$;

create function public.publish_direct_movement_program(p_id uuid,p_document jsonb,p_candidates jsonb,p_expected jsonb)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare
  p public.performances; detail jsonb; src jsonb; ptr jsonb; raw text; env jsonb; r jsonb; frozen jsonb; header int;
  orig text; url text; key text; rd_sha text; checked timestamptz; c jsonb; ref jsonb; e jsonb; fields jsonb;
  idx int; prev int:=-1; wid uuid; work public.works; author public.composers; opus text; scope text; n int;
  items jsonb:='[]'; current_rows jsonb; history jsonb;
begin
  select * into p from public.performances where id=p_id for update;
  if not found or p.kopis_performance_id is null or p.starts_on is null or p.starts_on is distinct from p.ends_on
    or cardinality(p.intro_image_urls) is distinct from 1 then return '{"status":"date_or_source_binding_required","items":0}';end if;
  url:=p.intro_image_urls[1];orig:=p_document->>'sha';raw:=p_document->>'envelope_utf8';
  if p_document->>'url' is distinct from url or coalesce(orig,'') !~ '^[0-9a-f]{64}$' or raw is null or octet_length(raw) not between 1 and 524288
    then return '{"status":"stale_source","items":0}';end if;
  select payload into detail from public.provider_records where provider='kopis' and entity_type='performance_detail' and provider_id=p.kopis_performance_id for share;
  if detail->>'mt20id' is distinct from p.kopis_performance_id or detail->>'prfnm' is distinct from p.title
    or (detail#>'{styurls,styurl}' is distinct from to_jsonb(url) and detail#>'{styurls,styurl}' is distinct from to_jsonb(p.intro_image_urls))
    then return '{"status":"stale_kopis_detail","items":0}';end if;
  select payload into src from public.provider_records where provider='r2' and entity_type='source_archive'
    and provider_id=encode(sha256(convert_to(url,'UTF8')),'hex') for share;
  select payload into ptr from public.provider_records where provider='codex_vision' and entity_type='direct_reading'
    and provider_id=p_document->>'reading_key' for share;
  rd_sha:=encode(sha256(convert_to(raw,'UTF8')),'hex');
  if src->>'source_url' is distinct from url or src->>'sha256' is distinct from orig or src->>'bucket' is distinct from 'classic-hubble-sources'
    or src->>'object_key' is distinct from 'originals/sha256/'||left(orig,2)||'/'||orig or not coalesce(src->'performance_ids' ? p_id::text,false)
    or ptr->>'result_sha256' is distinct from rd_sha or ptr->>'result_object_key' is distinct from 'extractions/sha256/'||left(rd_sha,2)||'/'||rd_sha
    or ptr->>'bucket' is distinct from src->>'bucket' or ptr->>'source_object_key' is distinct from src->>'object_key'
    or ptr->>'source_sha256' is distinct from orig or ptr->>'pipeline_version' is distinct from 'codex-direct-vision-v1'
    or ptr->>'method' is distinct from 'chat_model_direct_image_reading' or ptr->>'coverage' is distinct from 'complete' or ptr->>'status' is distinct from 'text_extracted'
    then return '{"status":"stale_original_or_reading","items":0}';end if;
  if p_expected is not null then
    checked:=(p_document->>'checked_at')::timestamptz;
    if p_document->>'live_sha' is distinct from orig or p_document->>'content_type' is distinct from src->>'content_type'
      or checked is null or checked not between now()-interval '5 minutes' and now()+interval '1 minute' then return '{"status":"live_source_check_required","items":0}';end if;
  end if;
  env:=raw::jsonb;r:=env->'reading';frozen:=env->'matching';header:=public.direct_movement_program_section(r,detail,p.starts_on);
  if header is null or env->>'source_sha256' is distinct from orig or r->>'source_sha256' is distinct from orig
    or env->'reading_sha256' is distinct from ptr->'reading_sha256' or env->'method' is distinct from ptr->'method'
    or env->'pipeline_version' is distinct from ptr->'pipeline_version' or env->'source_object_key' is distinct from src->'object_key' or env->'bucket' is distinct from src->'bucket'
    or frozen->>'validation_status' is distinct from 'complete' or frozen->'warnings' is distinct from '[]'::jsonb
    or frozen->'source_warnings' is distinct from '[]'::jsonb or frozen->'rejected_items' is distinct from '[]'::jsonb
    then return '{"status":"date_or_reading_binding_required","items":0}';end if;
  if jsonb_typeof(p_candidates) is distinct from 'array' or jsonb_array_length(p_candidates) not between 1 and 50 then return '{"status":"no_verified_movements","items":0}';end if;
  for c in select value from jsonb_array_elements(p_candidates) loop
    idx:=(c->>'index')::int;wid:=(c->>'work_id')::uuid;scope:=c->>'scope';
    if idx is null or idx<=prev or idx>=jsonb_array_length(r->'items') or wid is null or coalesce(scope,'') not in ('unknown','movement','excerpt') then return '{"status":"invalid_candidates","items":0}';end if;
    prev:=idx;ref:=r->'items'->idx;
    select count(*),(jsonb_agg(v)->0) into n,e from jsonb_array_elements(frozen->'items') v where v->>'source_index'=idx::text and not v?'derived_from';
    fields:=public.direct_movement_citations(r,ref,header);
    if n<>1 or fields is null or e->'evidence' is distinct from ref or e->'fields' is distinct from fields or e->>'context' is distinct from 'program'
      or e->>'identity_reason' is distinct from 'composer_and_catalogue' or e->>'reason' is distinct from 'scope_requires_review'
      or e->>'scope' is distinct from scope or e->>'scoped_work_id' is distinct from wid::text or e->>'suggested_work_id' is not null
      or e->'candidate_ids' is distinct from jsonb_build_array(wid)
      then return '{"status":"unsupported_or_changed_selection","items":0}';end if;
    opus:=regexp_replace(upper(regexp_replace(fields->>'catalogue','[ .]','','g')),'^KV','K');
    select * into work from public.works where id=wid for share;
    if not found or coalesce(opus,'')!~'^(OP|K)[1-9][0-9]{0,3}$'
      or regexp_replace(upper(regexp_replace(work.catalogue,'[ .]','','g')),'^KV','K') is distinct from opus
      then return '{"status":"ambiguous_or_stale_catalogue","items":0}';end if;
    select * into author from public.composers where id=work.composer_id for share;
    if not found or not public.direct_printed_composer(fields->>'composer',author.name,author.name_ko)
      or exists(select from public.composers other join public.works w on w.composer_id=other.id
          where w.id<>wid and regexp_replace(upper(regexp_replace(w.catalogue,'[ .]','','g')),'^KV','K')=opus
            and public.direct_printed_composer(fields->>'composer',other.name,other.name_ko))
      then return '{"status":"ambiguous_or_stale_catalogue","items":0}';end if;
    items:=items||jsonb_build_array(jsonb_build_object('position',idx,'work_id',wid,'composer_name',fields->>'composer',
      'display_title',concat_ws(' ',fields->>'title',fields->>'catalogue'),'performed_scope',scope,'scope_details',fields->'movements','source_url',url));
  end loop;
  if p_expected is not null and p_expected is distinct from items then return '{"status":"stale_preview","items":0}';end if;
  key:=p_id::text||':'||encode(sha256(convert_to(jsonb_build_array(orig,rd_sha,items)::text,'UTF8')),'hex');
  perform 1 from public.program_items where performance_id=p_id for update;
  select coalesce(jsonb_agg(jsonb_build_object('position',position,'work_id',work_id,'composer_name',composer_name,'display_title',display_title,
    'performed_scope',performed_scope,'scope_details',scope_details,'source_url',source_url) order by position),'[]')
    into current_rows from public.program_items where performance_id=p_id;
  if current_rows=items and not exists(select from public.program_items where performance_id=p_id and source_provider is distinct from 'codex_vision')
    and exists(select from public.provider_records where provider='codex_vision' and entity_type='movement_program_publication' and provider_id=key)
    then return jsonb_build_object('status','unchanged','items',jsonb_array_length(items));end if;
  if current_rows<>'[]'::jsonb or p.program_status is distinct from 'unknown' or p.program_source_url is not null or cardinality(p.program_image_urls)>0
    then return '{"status":"existing_program_preserved","items":0}';end if;
  if p_expected is null then return jsonb_build_object('status','ready','items',jsonb_array_length(items),'program',items);end if;
  history:=jsonb_build_object('version','direct-cited-movements-v1','performance_id',p_id,'before',current_rows,'before_performance',to_jsonb(p),
    'after',items,'source_sha256',orig,'reading_id',p_document->>'reading_key','envelope_sha256',rd_sha,'reading_sha256',ptr->>'reading_sha256',
    'source_indices',p_candidates,'header_index',header,'date',p.starts_on,'venue',detail->>'fcltynm','schedule',detail->>'dtguidance','checked_at',checked);
  insert into public.provider_records(provider,entity_type,provider_id,payload)values('codex_vision','movement_program_publication',key,history);
  insert into public.program_items(performance_id,position,work_id,composer_name,display_title,performed_scope,scope_details,source_url,source_type,source_provider)
    select p_id,(v->>'position')::int,(v->>'work_id')::uuid,v->>'composer_name',v->>'display_title',v->>'performed_scope',v->'scope_details',url,'ocr','codex_vision' from jsonb_array_elements(items) v;
  update public.performances set program_status='partially_confirmed',program_source_url=url,program_image_urls=p.intro_image_urls,program_source_updated_at=checked where id=p_id;
  return jsonb_build_object('status','published','items',jsonb_array_length(items));
exception when data_exception then return '{"status":"invalid_evidence","items":0}';
end $$;
revoke all on function public.direct_movement_program_section(jsonb,jsonb,date),public.direct_movement_citations(jsonb,jsonb,int),public.direct_printed_composer(text,text,text),public.publish_direct_movement_program(uuid,jsonb,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.direct_movement_program_section(jsonb,jsonb,date),public.direct_movement_citations(jsonb,jsonb,int),public.direct_printed_composer(text,text,text),public.publish_direct_movement_program(uuid,jsonb,jsonb,jsonb) to service_role;
-- A legacy re-match may not replace the preserved scopes with anonymous full-work rows.
do $migration$
declare
  definition text:=pg_get_functiondef('public.publish_direct_vision_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb)'::regprocedure);
  anchor text:='  if jsonb_build_object(''id'', v_performance.id, ''title'', v_performance.title,';
  guard text:=$guard$  if exists(select from public.program_items where performance_id=p_performance_id and source_provider='codex_vision' and performed_scope is not null)
  then return jsonb_build_object('status','existing_program_preserved','items',0);end if;
$guard$;
begin
  if strpos(definition,guard)>0 then return;end if;
  if length(definition)-length(replace(definition,anchor,''))<>length(anchor) then raise exception 'Unexpected direct publication guard';end if;
  execute replace(definition,anchor,guard||anchor);
end $migration$;
notify pgrst,'reload schema';
