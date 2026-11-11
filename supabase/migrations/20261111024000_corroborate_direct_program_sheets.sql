-- Typed KOPIS data corroborates a complete ordered set of original programme
-- sheets. It cannot substitute for an unread sheet, or replace existing rows.
create function public.direct_sheet_items(r jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare
  lines jsonb:=r->'lines'; ref jsonb; q jsonb; idx int; last_idx int:=-1; cursor_idx int;
  composer text; title text; fragment text; actual text; yr text; forces text; out_items jsonb:='[]';
begin
  if r->>'coverage' is distinct from 'complete' or r->>'status' is distinct from 'text_extracted'
    or jsonb_typeof(lines) is distinct from 'array' or jsonb_array_length(lines) not between 1 and 250
    or exists(select from jsonb_array_elements(lines) l where l->>'page_index' is distinct from '0' or coalesce(l->>'text','')='')
    or jsonb_typeof(r->'items') is distinct from 'array' or jsonb_array_length(r->'items')>50 then return null; end if;
  if r->>'extraction_status'='no_program_identified' and r->'items'='[]'::jsonb then return '[]'::jsonb;end if;
  if r->>'extraction_status' is distinct from 'items_extracted' or r->'items'='[]'::jsonb then return null;end if;
  for ref in select value from jsonb_array_elements(r->'items') loop
    if ref->>'context' is distinct from 'program' or ref->>'scope' is distinct from 'unknown'
      or ref->'key' is distinct from 'null'::jsonb or ref->'catalogue' is distinct from 'null'::jsonb
      or ref->'movements' is distinct from '[]'::jsonb or jsonb_array_length(ref->'composer') is distinct from 1
      or jsonb_typeof(ref->'title') is distinct from 'array' or jsonb_array_length(ref->'title') not between 1 and 5
      then return null;end if;
    q:=ref#>'{composer,0}';
    if coalesce(q->>'line_id','')!~'^L[0-9]{6}$' then return null;end if;
    idx:=substr(q->>'line_id',2)::int; composer:=q->>'quote';
    if idx<=last_idx or coalesce(composer,'')='' or lines->idx->>'text' is distinct from composer then return null;end if;
    cursor_idx:=idx; title:=''; yr:=null;
    for q in select value from jsonb_array_elements(ref->'title') loop
      cursor_idx:=cursor_idx+1;
      if q->>'line_id' is distinct from 'L'||lpad(cursor_idx::text,6,'0') or yr is not null then return null;end if;
      fragment:=q->>'quote';actual:=lines->cursor_idx->>'text';
      if coalesce(fragment,'')='' or actual is null or left(actual,length(fragment))<>fragment then return null;end if;
      if actual<>fragment then
        yr:=substring(substr(actual,length(fragment)+1) from '^ \(([12][0-9]{3}(/[0-9]{2})?)\)$');
        if yr is null then return null;end if;
      end if;
      title:=concat_ws(' ',nullif(title,''),fragment);
    end loop;
    if yr is null then return null;end if;
    forces:=lines->(cursor_idx+1)->>'text';
    if coalesce(forces,'')!~'^for [^()<>]{1,160}$' then return null;end if;
    last_idx:=cursor_idx+1;
    out_items:=out_items||jsonb_build_array(jsonb_build_object('composer',composer,'title',title,'year',yr,'forces',forces));
  end loop;
  return out_items;
exception when data_exception then return null;
end;
$$;

create function public.direct_sheet_work(p_composer text,p_title text) returns uuid
language sql stable security invoker set search_path='' as $$
  select case when count(*)=1 and bool_and(vetted) then (array_agg(id))[1] end
  from (
    select w.id, w.slug not like 'wikidata-%' and w.slug not like 'component-%'
      and (not exists(select from public.work_aliases a where a.work_id=w.id and a.source like 'wikidata:%')
        or exists(select from public.work_aliases a where a.work_id=w.id and a.source='curated')) as vetted
    from public.composers c join public.works w on w.composer_id=c.id
    where (c.name=p_composer or c.name_ko=p_composer)
      and (lower(w.title)=lower(p_title) or lower(w.title_ko)=lower(p_title) or exists(
        select from public.work_aliases a where a.work_id=w.id and a.source like 'verified:https://%'
          and lower(a.alias)=lower(p_title)))
  ) candidates
$$;

create function public.publish_direct_kopis_sheets(p_id uuid,p_sty_sha text,p_documents jsonb,p_expected_items jsonb)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare
  perf public.performances; detail jsonb; src jsonb; ptr jsonb; doc jsonb; reading jsonb; raw text; url text; orig text; row_item jsonb;
  items jsonb:='[]'; refs jsonb:='[]'; sheet jsonb; hashes text[]:='{}'; work_ids uuid[]:='{}'; wid uuid;
  typed text[]; typed_item text[]; sty text; dt text; stamp text; hall text; heading text; ln text; n int:=0; j int:=0;
  src_date timestamptz; key text; current_rows jsonb; hdr_count int;
begin
  select * into perf from public.performances where id=p_id for update;
  if not found or perf.kopis_performance_id is null or perf.starts_on is null or perf.starts_on is distinct from perf.ends_on
    or cardinality(perf.intro_image_urls) not between 2 and 6
    or jsonb_typeof(p_documents) is distinct from 'array' or jsonb_array_length(p_documents) is distinct from cardinality(perf.intro_image_urls)
    then return '{"status":"date_or_source_binding_required","items":0}';end if;
  select payload into detail from public.provider_records where provider='kopis' and entity_type='performance_detail'
    and provider_id=perf.kopis_performance_id for share;
  sty:=detail->>'sty';dt:=to_char(perf.starts_on,'YYYY.MM.DD');hall:=split_part(detail->>'fcltynm',' (',1);
  if sty is null or octet_length(sty)>32000 or coalesce(hall,'')='' or sty is distinct from perf.synopsis
    or encode(sha256(convert_to(sty,'UTF8')),'hex') is distinct from p_sty_sha
    or detail->>'mt20id' is distinct from perf.kopis_performance_id or detail->>'prfnm' is distinct from perf.title
    or detail->>'prfpdfrom' is distinct from dt or detail->>'prfpdto' is distinct from dt
    or detail#>'{styurls,styurl}' is distinct from to_jsonb(perf.intro_image_urls)
    then return '{"status":"stale_kopis_detail","items":0}';end if;
  select array_agg(btrim(v) order by i) into typed from regexp_split_to_table(replace(sty,chr(13),''),chr(10)) with ordinality a(v,i)
    where btrim(v)<>'';
  if typed[1] is distinct from '[Program]' or cardinality(typed) not between 2 and 51 then return '{"status":"unsupported_text_program","items":0}';end if;
  for doc in select value from jsonb_array_elements(p_documents) loop
    j:=j+1;url:=perf.intro_image_urls[j];orig:=doc->>'sha';raw:=doc->>'reading_utf8';
    if doc->>'url' is distinct from url or coalesce(orig,'')!~'^[0-9a-f]{64}$' or orig=any(hashes)
      or raw is null or octet_length(raw) not between 1 and 262144 then return '{"status":"stale_source","items":0}';end if;
    hashes:=array_append(hashes,orig);
    select payload into src from public.provider_records where provider='r2' and entity_type='source_archive'
      and provider_id=encode(sha256(convert_to(url,'UTF8')),'hex') for share;
    select payload into ptr from public.provider_records where provider='codex_vision' and entity_type='direct_reading'
      and provider_id=doc->>'reading_key' for share;
    if src->>'source_url' is distinct from url or src->>'sha256' is distinct from orig or src->>'bucket' is distinct from 'classic-hubble-sources'
      or src->>'object_key' is distinct from 'originals/sha256/'||left(orig,2)||'/'||orig
      or not coalesce(src->'performance_ids' ? p_id::text,false)
      or ptr->>'source_sha256' is distinct from orig or ptr->>'bucket' is distinct from src->>'bucket'
      or ptr->>'source_object_key' is distinct from src->>'object_key' or ptr->>'method' is distinct from 'chat_model_direct_image_reading'
      or ptr->>'pipeline_version' is distinct from 'codex-direct-vision-v1' or ptr->>'status' is distinct from 'text_extracted'
      or ptr->>'coverage' is distinct from 'complete' or ptr->>'reading_sha256' is distinct from encode(sha256(convert_to(raw,'UTF8')),'hex')
      or coalesce(ptr->>'result_sha256','') !~ '^[0-9a-f]{64}$'
      or ptr->>'result_object_key' is distinct from 'extractions/sha256/'||left(ptr->>'result_sha256',2)||'/'||(ptr->>'result_sha256')
      then return '{"status":"stale_source_or_reading","items":0}';end if;
    if p_expected_items is not null then
      src_date:=(doc->>'checked_at')::timestamptz;
      if doc->>'live_sha' is distinct from orig or doc->>'content_type' is distinct from src->>'content_type'
        or src_date is null or src_date not between now()-interval '5 minutes' and now()+interval '1 minute'
        then return '{"status":"live_source_check_required","items":0}';end if;
    end if;
    reading:=raw::jsonb;sheet:=public.direct_sheet_items(reading);
    if reading->>'source_sha256' is distinct from orig or sheet is null then return '{"status":"unsupported_sheet","items":0}';end if;
    if j=1 then
      select count(*),min(v->>'text') into hdr_count,stamp from jsonb_array_elements(reading->'lines') v
        where left(v->>'text',length(dt)+2)=dt||'. ' and substr(v->>'text',length(dt)+3) ~ '^(1[0-2]|[1-9]):[0-5][0-9](AM|PM)$';
      if sheet<>'[]'::jsonb or hdr_count<>1 or not exists(select from jsonb_array_elements(reading->'lines') v
        where replace(v->>'text',' ','')=replace(perf.title,' ',''))
        or not exists(select from jsonb_array_elements(reading->'lines') v
          where replace(split_part(v->>'text','(',1),' ','')=replace(hall,' ',''))
        then return '{"status":"missing_dated_cover","items":0}';end if;
    elsif sheet='[]'::jsonb then return '{"status":"unsupported_sheet","items":0}';
    elsif j=2 then
      heading:=reading#>>'{lines,0,text}';
      if replace(heading,' ','') is distinct from replace('<'||perf.title||'> '||stamp||' '||hall,' ','')
        then return '{"status":"missing_dated_program_header","items":0}';end if;
    end if;
    for ln in select v->>'text' from jsonb_array_elements(reading->'lines') v loop
      if (j=1 and ln=stamp) or (j=2 and ln=heading) then continue;end if;
      if ln ~* '(예매|티켓|판매|예약|프로필|공연일|profile|biography|cancelled|canceled|ticket|booking|programme change|변경|취소|[0-9] *월 *[0-9]|[0-9]{1,2} *[/.-] *[0-9]{1,2} *[([][월화수목금토일]|[12][0-9]{3} *[./-] *[0-9]{1,2} *[./-] *[0-9]{1,2}|(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|aug(ust)?|sep(t(ember)?)?|oct(ober)?|nov(ember)?|dec(ember)?)[ .]+[0-9])'
        or ln ~* '(^|[^0-9])(0?[1-9]|1[012]) *[/\-] *(0?[1-9]|[12][0-9]|3[01])([^0-9]|$)'
        or ln ~* '^[[:space:]]*(0?[1-9]|1[012]) *\. *(0?[1-9]|[12][0-9]|3[01])([[:space:]]|$)'
        or ln ~* '(^|[^0-9])[0-9]{1,2}(st|nd|rd|th)?[ .]+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
        then return '{"status":"conflicting_date_or_context","items":0}';end if;
    end loop;
    for row_item in select value from jsonb_array_elements(sheet) loop
      n:=n+1;
      typed_item:=regexp_match(typed[n+1],'^([^<>]+) <([^<>]+)> (for [^()<>]+) \(([12][0-9]{3}(/[0-9]{2})?)(, (W\.P\.|revised P\.))?\)$');
      if typed_item is null or typed_item[1] is distinct from row_item->>'composer' or typed_item[4] is distinct from row_item->>'year'
        or lower(regexp_replace(typed_item[3],',? and ',', ','g')) is distinct from lower(regexp_replace(row_item->>'forces',',? and ',', ','g'))
        then return '{"status":"ordered_program_disagreement","items":0}';end if;
      wid:=public.direct_sheet_work(typed_item[1],typed_item[2]);
      if wid is null or wid=any(work_ids) or wid is distinct from public.direct_sheet_work(row_item->>'composer',row_item->>'title')
        then return '{"status":"edition_or_identity_unverified","items":0}';end if;
      work_ids:=array_append(work_ids,wid);
      items:=items||jsonb_build_array(jsonb_build_object('work_id',wid,'position',n-1,'display_title',row_item->>'title',
        'composer_name',row_item->>'composer','performed_scope','unknown','scope_details','[]'::jsonb,'source_url',url));
    end loop;
    refs:=refs||jsonb_build_array(jsonb_build_object('url',url,'source_sha256',orig,'reading_id',doc->>'reading_key',
      'reading_sha256',ptr->>'reading_sha256','result_sha256',ptr->>'result_sha256'));
  end loop;
  if n=0 or n<>cardinality(typed)-1 then return '{"status":"incomplete_ordered_program","items":0}';end if;
  if p_expected_items is not null and p_expected_items is distinct from items then return '{"status":"stale_preview","items":0}';end if;
  key:=p_id::text||':'||encode(sha256(convert_to(jsonb_build_array(p_sty_sha,refs,items)::text,'UTF8')),'hex');
  perform 1 from public.program_items where performance_id=p_id for update;
  select coalesce(jsonb_agg(jsonb_build_object('work_id',work_id,'position',position,'display_title',display_title,
    'composer_name',composer_name,'performed_scope',performed_scope,'scope_details',scope_details,'source_url',source_url) order by position),'[]')
    into current_rows from public.program_items where performance_id=p_id;
  if current_rows=items and not exists(select from public.program_items where performance_id=p_id and source_provider is distinct from 'codex_vision')
    and exists(select from public.provider_records where provider='codex_vision' and entity_type='sheet_bundle_publication' and provider_id=key)
    then return jsonb_build_object('status','unchanged','items',n);end if;
  if current_rows<>'[]'::jsonb or perf.program_status in ('partially_confirmed','confirmed') or perf.program_source_url is not null
    or cardinality(perf.program_image_urls)>0 then return '{"status":"existing_program_preserved","items":0}';end if;
  if p_expected_items is null then return jsonb_build_object('status','ready','items',n,'program',items);end if;
  insert into public.provider_records(provider,entity_type,provider_id,payload) values('codex_vision','sheet_bundle_publication',key,
    jsonb_build_object('version','direct-kopis-sheets-v1','performance_id',p_id,'before',current_rows,'before_performance',to_jsonb(perf),
      'sources',refs,'detail_id',perf.kopis_performance_id,'detail_sha256',p_sty_sha,'detail_program',typed,'after',items));
  insert into public.program_items(performance_id,work_id,display_title,composer_name,source_type,position,source_provider,source_url,performed_scope,scope_details)
    select p_id,(i->>'work_id')::uuid,i->>'display_title',i->>'composer_name','ocr',(i->>'position')::int,'codex_vision',i->>'source_url','unknown','[]'
    from jsonb_array_elements(items) i;
  update public.performances set program_status='partially_confirmed',program_source_url=perf.intro_image_urls[2],
    program_image_urls=perf.intro_image_urls,program_source_updated_at=now() where id=p_id;
  return jsonb_build_object('status','published','items',n);
exception when data_exception then return '{"status":"invalid_evidence","items":0}';
end;
$$;
revoke all on function public.direct_sheet_items(jsonb),public.direct_sheet_work(text,text),public.publish_direct_kopis_sheets(uuid,text,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.direct_sheet_items(jsonb),public.direct_sheet_work(text,text),public.publish_direct_kopis_sheets(uuid,text,jsonb,jsonb) to service_role;
notify pgrst,'reload schema';
