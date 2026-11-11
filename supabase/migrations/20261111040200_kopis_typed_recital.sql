-- Keep the official programme and an independently observed, programme-free cover distinct.
create function public.kopis_typed_lieder_lines(sty text) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare ls text[]; s text; m text[]; i int; grp boolean:=false; in_grp int:=0; songs jsonb:='[]';
begin
  if sty is null or octet_length(sty)>32000 then return null;end if;
  ls:=string_to_array(replace(sty,E'\r\n',E'\n'),E'\n');
  if cardinality(ls) not between 3 and 200 or btrim(ls[1]) is distinct from '[PROGRAM]' then return null;end if;
  for i in 2..cardinality(ls) loop
    s:=btrim(ls[i]);if s='' then continue;end if;
    if s ~ '^(M\.Sop|Sop|Ten)\. [가-힣]{2,6} · Kl\. [가-힣]{2,6}$' then
      if grp and in_grp=0 then return null;end if;grp:=true;in_grp:=0;
    elsif s='— Pause —' then
      if not grp or in_grp=0 then return null;end if;grp:=false;in_grp:=0;
    else
      m:=regexp_match(s,'^([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ ''!?,.()-]{0,150}), D ([1-9][0-9]{0,3})(?: No\. ([1-9][0-9]?))?$');
      if not grp or m is null or jsonb_array_length(songs)>=60 then return null;end if;
      songs:=songs||jsonb_build_array(jsonb_build_object('position',jsonb_array_length(songs),'line',i-1,'literal',s,'title',m[1],'number',m[2],'member',m[3]));
      in_grp:=in_grp+1;
    end if;
  end loop;
  if not grp or in_grp=0 then return null;end if;return songs;
end $$;

create function public.kopis_lieder_cover(r jsonb,d jsonb,day date) returns boolean
language plpgsql immutable security invoker set search_path='' as $$
declare ls jsonb:=r->'lines'; l jsonb; s text; venue text[]; name text[]; m text[]; wk int; hh int;
  header int:=0; subject int:=0; credit int:=0; clock_count int:=0; hall_count int:=0;
begin
  if day is null or d->>'prfpdfrom' is distinct from to_char(day,'YYYY.MM.DD') or d->>'prfpdto' is distinct from d->>'prfpdfrom'
    or r->>'coverage' is distinct from 'complete' or r->>'status' is distinct from 'text_extracted' or r->>'extraction_status' is distinct from 'no_program_identified'
    or r->'items' is distinct from '[]'::jsonb or jsonb_typeof(ls) is distinct from 'array' or jsonb_array_length(ls) not between 5 and 16 then return false;end if;
  name:=regexp_match(d->>'prfnm','^제([1-9][0-9]{0,2})회 한국슈베르트협회 정기연주회: ([^:]+)$');
  venue:=regexp_match(d->>'fcltynm','^([^][()]+)(?: \[[^][]+\])? \(([^()]+)\)$');
  if name is null or venue is null then return false;end if;
  wk:=extract(isodow from day)::int;
  for l in select value from jsonb_array_elements(ls) loop
    s:=l->>'text';if l->>'page_index' is distinct from '0' or coalesce(s,'')='' then return false;end if;
    if s='한국슈베르트협회 '||name[1]||'회 정기연주회' then header:=header+1;
    elsif s=name[2] then subject:=subject+1;
    elsif s in ('슈베르트 가곡 속에서 비춰진 소녀들의 모습을 모아놓은 작품들','Lieder von Franz Schubert') then credit:=credit+1;
    elsif s='Das Mädchen im Schubertslieder' then continue;
    elsif replace(s,' ','')=replace(venue[1]||venue[2],' ','') then hall_count:=hall_count+1;
    else
      m:=regexp_match(s,'^(20[0-9]{2})\. *([0-9]{1,2})\. *([0-9]{1,2})\.? +(MON|TUE|WED|THU|FRI|SAT|SUN) +([1-9]|1[012]):([0-5][0-9]) +(AM|PM)$');
      if m is null or make_date(m[1]::int,m[2]::int,m[3]::int)<>day or m[4]<>(array['MON','TUE','WED','THU','FRI','SAT','SUN'])[wk] then return false;end if;
      hh:=m[5]::int%12+case m[7] when 'PM' then 12 else 0 end;
      if d->>'dtguidance' is distinct from substr('월화수목금토일',wk,1)||'요일('||lpad(hh::text,2,'0')||':'||m[6]||')' then return false;end if;
      clock_count:=clock_count+1;
    end if;
  end loop;
  return header=1 and subject=1 and credit=1 and hall_count=1 and clock_count=1;
exception when data_exception then return false;
end $$;

create function public.publish_kopis_typed_recital(p_id uuid,p_document jsonb,p_candidates jsonb,p_expected jsonb)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare
  p public.performances; d jsonb; src jsonb; ptr jsonb; env jsonb; a jsonb; proof jsonb; ref jsonb; c jsonb; w public.works;
  cover text; sha text:=p_document->>'sha'; raw text:=p_document->>'envelope_utf8'; rd text; k text:=p_document->>'authority_key'; txt text; h text;
  url text; songs jsonb; pos int; last_pos int:=-1; s jsonb; wid uuid; num text; title text; composer text; idx int;
  program jsonb:='[]'; current_rows jsonb; audit_key text; checked timestamptz; now_detail jsonb; before_audit jsonb;
begin
  select * into p from public.performances where id=p_id for update;
  if not found or coalesce(p.kopis_performance_id,'')!~'^PF[0-9]+$' or p.starts_on is null or p.starts_on is distinct from p.ends_on
    or cardinality(p.intro_image_urls) is distinct from 1 then return '{"status":"date_or_source_binding_required","items":0}';end if;
  cover:=p.intro_image_urls[1];url:='https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id='||p.kopis_performance_id;
  if p_document->>'url' is distinct from cover or coalesce(sha,'')!~'^[a-f0-9]{64}$' or coalesce(k,'')!~'^[a-f0-9]{64}$'
    or raw is null or octet_length(raw) not between 1 and 524288 then return '{"status":"stale_source","items":0}';end if;
  select payload into d from public.provider_records where provider='kopis' and entity_type='performance_detail' and provider_id=p.kopis_performance_id for share;
  h:=encode(sha256(convert_to(d->>'sty','UTF8')),'hex');
  if d->>'mt20id' is distinct from p.kopis_performance_id or d->>'prfnm' is distinct from p.title or h is null or h is distinct from p_document->>'sty_sha'
    or d->>'sty' is distinct from p.synopsis or (d#>'{styurls,styurl}' is distinct from to_jsonb(cover) and d#>'{styurls,styurl}' is distinct from to_jsonb(p.intro_image_urls))
    then return '{"status":"stale_kopis_detail","items":0}';end if;
  select payload into src from public.provider_records where provider='r2' and entity_type='source_archive' and provider_id=encode(sha256(convert_to(cover,'UTF8')),'hex') for share;
  select payload into ptr from public.provider_records where provider='codex_vision' and entity_type='direct_reading' and provider_id=p_document->>'reading_key' for share;
  rd:=encode(sha256(convert_to(raw,'UTF8')),'hex');env:=raw::jsonb;
  if src->>'source_url' is distinct from cover or src->>'bucket' is distinct from 'classic-hubble-sources' or src->>'sha256' is distinct from sha
    or src->>'object_key' is distinct from 'originals/sha256/'||left(sha,2)||'/'||sha or not coalesce(src->'performance_ids' ? p_id::text,false)
    or ptr->>'result_sha256' is distinct from rd or ptr->>'result_object_key' is distinct from 'extractions/sha256/'||left(rd,2)||'/'||rd
    or ptr->>'bucket' is distinct from src->>'bucket' or ptr->>'source_object_key' is distinct from src->>'object_key'
    or ptr->>'source_sha256' is distinct from sha or ptr->>'pipeline_version' is distinct from 'codex-direct-vision-v1'
    or ptr->>'method' is distinct from 'chat_model_direct_image_reading' or ptr->>'coverage' is distinct from 'complete' or ptr->>'status' is distinct from 'text_extracted'
    or env->'reading_sha256' is distinct from ptr->'reading_sha256' or coalesce(ptr->>'reading_sha256','')!~'^[a-f0-9]{64}$'
    or env->'method' is distinct from ptr->'method' or env->'pipeline_version' is distinct from ptr->'pipeline_version'
    or env->'source_object_key' is distinct from src->'object_key' or env->'bucket' is distinct from src->'bucket' or env->>'source_sha256' is distinct from sha
    or env#>>'{reading,source_sha256}' is distinct from sha or not public.kopis_lieder_cover(env->'reading',d,p.starts_on)
    then return '{"status":"cover_binding_unverified","items":0}';end if;
  if p_expected is not null then
    checked:=(p_document->>'checked_at')::timestamptz;
    select jsonb_object_agg(x,d->x) into now_detail from unnest(array['mt20id','prfnm','prfpdfrom','prfpdto','dtguidance','fcltynm','styurls']) x;
    if checked is null or checked not between now()-interval '5 minutes' and now()+interval '1 minute'
      or p_document->>'live_sha' is distinct from sha or p_document->>'content_type' is distinct from src->>'content_type'
      or p_document->>'live_sty_sha' is distinct from h or p_document->'live_detail' is distinct from now_detail then return '{"status":"live_source_check_required","items":0}';end if;
  end if;
  songs:=public.kopis_typed_lieder_lines(d->>'sty');
  if songs is null or jsonb_typeof(p_candidates) is distinct from 'array' or jsonb_array_length(p_candidates) not between 1 and 60 then return '{"status":"invalid_program","items":0}';end if;
  select payload into a from public.provider_records where provider='catalogue_repair' and entity_type='lied_catalogue_authority' and provider_id=k for share;
  txt:=a->>'proof_utf8';
  if txt is null or octet_length(txt) not between 2 and 64000 or encode(sha256(convert_to(txt,'UTF8')),'hex') is distinct from k
    or a->>'bucket' is distinct from 'classic-hubble-sources' or a->>'result_sha256' is distinct from k
    or a->>'result_object_key' is distinct from 'extractions/sha256/'||left(k,2)||'/'||k then return '{"status":"missing_catalogue_authority","items":0}';end if;
  proof:=txt::jsonb;
  if proof->>'purpose' is distinct from 'schubert_lied_identities_v1' or proof->>'composer' is distinct from 'Franz Schubert'
    or jsonb_typeof(proof->'works') is distinct from 'array' or jsonb_array_length(proof->'works') not between 1 and 60
    then return '{"status":"unsupported_catalogue_authority","items":0}';end if;
  for c in select value from jsonb_array_elements(p_candidates) loop
    pos:=(c->>'position')::int;wid:=(c->>'work_id')::uuid;
    if pos is null or pos<=last_pos or pos>=jsonb_array_length(songs) or wid is null then return '{"status":"invalid_candidates","items":0}';end if;
    last_pos:=pos;s:=songs->pos;num:=s->>'number';title:=s->>'title';
    if s->'member' is distinct from 'null'::jsonb or s->'line' is distinct from c->'line' then return '{"status":"unsupported_member_or_line","items":0}';end if;
    select count(*),(jsonb_agg(v)->0) into idx,ref from jsonb_array_elements(proof->'works') v
      where v->>'number'=num and v->'member'='null'::jsonb and v->'title_forms' ? title;
    if idx<>1 or ref->>'work_id' is distinct from wid::text or coalesce(ref->>'source_url','')!~'^https://[^/[:space:]]+/.+'
      or coalesce(ref->>'reference','')='' then return '{"status":"ambiguous_catalogue_authority","items":0}';end if;
    select * into w from public.works where id=wid for share;
    if not found or w.slug is distinct from ref->>'work_slug' or w.title is distinct from ref->>'canonical_title'
      or w.composer_id::text is distinct from proof->>'composer_id' then return '{"status":"identity_changed","items":0}';end if;
    select name into composer from public.composers where id=w.composer_id for share;
    if composer is distinct from 'Franz Schubert' then return '{"status":"wrong_composer","items":0}';end if;
    if not (regexp_replace(coalesce(w.catalogue,''),'[. ]','','g')='D'||num or (w.catalogue is null and exists(select from public.work_aliases x
      where x.work_id=wid and regexp_replace(x.alias,'[. ]','','g')='D'||num))) or exists(select from public.works other where other.composer_id=w.composer_id and other.id<>wid
        and (regexp_replace(other.catalogue,'[. ]','','g')='D'||num or exists(select from public.work_aliases x where x.work_id=other.id and regexp_replace(x.alias,'[. ]','','g')='D'||num)))
      then return '{"status":"catalogue_number_not_unique","items":0}';end if;
    if w.title not in (title,s->>'literal') and not exists(select from public.work_aliases x where x.work_id=wid and x.alias in (title,s->>'literal'))
      then return '{"status":"title_not_corroborated","items":0}';end if;
    program:=program||jsonb_build_array(jsonb_build_object('position',pos,'work_id',wid,'composer_name',composer,'display_title',s->>'literal','performed_scope','unknown','scope_details','[]'::jsonb,'source_url',url));
  end loop;
  if p_expected is not null and p_expected is distinct from program then return '{"status":"stale_preview","items":0}';end if;
  audit_key:=p_id::text||':'||encode(sha256(convert_to(jsonb_build_array(sha,rd,h,k,program)::text,'UTF8')),'hex');
  perform 1 from public.program_items where performance_id=p_id for update;
  select coalesce(jsonb_agg(jsonb_build_object('position',position,'work_id',work_id,'composer_name',composer_name,'display_title',display_title,
    'performed_scope',performed_scope,'scope_details',scope_details,'source_url',source_url) order by position),'[]') into current_rows from public.program_items where performance_id=p_id;
  if exists(select from public.program_items where performance_id=p_id and (source_provider is distinct from 'kopis' or source_type::text is distinct from 'official'))
    then return '{"status":"existing_program_preserved","items":0}';end if;
  if current_rows=program and p.program_status::text='partially_confirmed' and p.program_source_url=url and p.program_image_urls=p.intro_image_urls
    and exists(select from public.provider_records where provider='kopis' and entity_type='typed_recital_publication' and provider_id=audit_key)
    then return jsonb_build_object('status','unchanged','items',jsonb_array_length(program));end if;
  if current_rows<>'[]'::jsonb or p.program_status::text is distinct from 'unknown' or p.program_source_url is not null or cardinality(p.program_image_urls)>0
    then return '{"status":"existing_program_preserved","items":0}';end if;
  if p_expected is null then return jsonb_build_object('status','ready','items',jsonb_array_length(program),'program',program);end if;
  before_audit:=jsonb_build_object('version','kopis-typed-lieder-v1','performance_id',p_id,'before',current_rows,'before_performance',to_jsonb(p),'after',program,
    'date',p.starts_on,'venue',d->>'fcltynm','schedule',d->>'dtguidance','official_url',url,'sty',d->>'sty','sty_sha256',h,'total_songs',jsonb_array_length(songs),
    'source_indices',p_candidates,'catalogue_authority',k,'cover_url',cover,'cover_sha256',sha,'envelope_sha256',rd,'cover_reading_key',p_document->>'reading_key',
    'cover_reading_sha256',ptr->>'reading_sha256','cover_contribution','event_identity_only','checked_at',checked);
  insert into public.provider_records(provider,entity_type,provider_id,payload)values('kopis','typed_recital_publication',audit_key,before_audit);
  insert into public.program_items(performance_id,position,work_id,composer_name,display_title,performed_scope,scope_details,source_url,source_type,source_provider)
    select p_id,(v->>'position')::int,(v->>'work_id')::uuid,v->>'composer_name',v->>'display_title','unknown','[]'::jsonb,url,'official','kopis' from jsonb_array_elements(program) v;
  update public.performances set program_status='partially_confirmed',program_source_url=url,program_image_urls=p.intro_image_urls,program_source_updated_at=checked where id=p_id;
  return jsonb_build_object('status','published','items',jsonb_array_length(program));
exception when data_exception then return '{"status":"invalid_evidence","items":0}';
end $$;
revoke all on function public.kopis_typed_lieder_lines(text),public.kopis_lieder_cover(jsonb,jsonb,date),public.publish_kopis_typed_recital(uuid,jsonb,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.kopis_typed_lieder_lines(text),public.kopis_lieder_cover(jsonb,jsonb,date),public.publish_kopis_typed_recital(uuid,jsonb,jsonb,jsonb) to service_role;
notify pgrst,'reload schema';
