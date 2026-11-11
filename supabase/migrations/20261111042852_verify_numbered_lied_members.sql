-- Numbered Lieder have their own identities. A parent catalogue or a differently numbered song is not sufficient.
create function public.kopis_lied_catalogue_key(c text) returns text
language sql immutable strict security invoker set search_path='' as $$
  select replace(regexp_replace(upper(c),'[. ]','','g'),'NO','/')
$$;

create function public.kopis_verified_lied_member(s jsonb,ref jsonb,w public.works) returns boolean
language plpgsql security invoker set search_path='' as $$
declare
  k text:=ref->>'registry_sha'; a jsonb; raw text; snap jsonb; claim jsonb; source_sha text;
  mt text:=ref->>'member_title'; coll text:=ref->>'collection_title'; op text:=ref->>'opus';
  dkey text; okey text;
begin
  if ref->>'kind' is distinct from 'individual_song' or coalesce(k,'')!~'^[a-f0-9]{64}$'
    or coalesce(mt,'')='' or coalesce(coll,'')='' or s->>'title' not in (mt,regexp_replace(mt,'!$',''),mt||' aus '||coll)
    or coalesce(s->>'number','')!~'^[1-9][0-9]{0,3}$' or coalesce(s->>'member','')!~'^[1-9][0-9]?$'
    or ref->'number' is distinct from s->'number' or ref->'member' is distinct from s->'member'
    or (op is not null and op!~'^[1-9][0-9]{0,3}$') or coalesce(ref->>'source_url','')!~'^https://[^/[:space:]]+/.+'
    then return false;end if;
  select payload into a from public.provider_records where provider='catalogue_repair' and entity_type='lied_member_source' and provider_id=k for share;
  raw:=a->>'proof_utf8';
  if raw is null or octet_length(raw) not between 2 and 32000 or encode(sha256(convert_to(raw,'UTF8')),'hex') is distinct from k
    or a->>'bucket' is distinct from 'classic-hubble-sources' or a->>'result_sha256' is distinct from k
    or a->>'result_object_key' is distinct from 'extractions/sha256/'||left(k,2)||'/'||k then return false;end if;
  snap:=raw::jsonb;source_sha:=snap->>'source_sha256';
  claim:=jsonb_build_object('number',s->>'number','member',s->>'member','member_title',mt,'collection_title',coll,'opus',op);
  if snap->>'source_url' is distinct from ref->>'source_url' or snap->>'composer' is distinct from 'Franz Schubert'
    or coalesce(source_sha,'')!~'^[a-f0-9]{64}$' or a->>'original_object_key' is distinct from 'originals/sha256/'||left(source_sha,2)||'/'||source_sha
    or jsonb_typeof(snap->'claims') is distinct from 'array' or not (snap->'claims' @> jsonb_build_array(claim)) then return false;end if;
  dkey:='D'||(s->>'number')||'/'||(s->>'member');okey:=case when op is null then dkey else 'OP'||op||'/'||(s->>'member') end;
  if w.catalogue is null or public.kopis_lied_catalogue_key(w.catalogue) not in (dkey,okey)
    or exists(select from public.works other where other.composer_id=w.composer_id and other.id<>w.id
      and (public.kopis_lied_catalogue_key(other.catalogue) in (dkey,okey) or exists(select from public.work_aliases x
        where x.work_id=other.id and public.kopis_lied_catalogue_key(x.alias) in (dkey,okey)))) then return false;end if;
  return coalesce(w.title=mt,false) or exists(select from public.work_aliases x where x.work_id=w.id and x.alias=mt);
exception when data_exception then return false;
end $$;

create or replace function public.publish_kopis_typed_recital(p_id uuid,p_document jsonb,p_candidates jsonb,p_expected jsonb)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare
  p public.performances; d jsonb; src jsonb; ptr jsonb; env jsonb; a jsonb; proof jsonb; ref jsonb; c jsonb; w public.works;
  cover text; sha text:=p_document->>'sha'; raw text:=p_document->>'envelope_utf8'; rd text; k text:=p_document->>'authority_key'; txt text; h text;
  url text; songs jsonb; pos int; last_pos int:=-1; s jsonb; wid uuid; num text; title text; composer text; idx int;
  program jsonb:='[]'; current_rows jsonb; audit_key text; checked timestamptz; now_detail jsonb; before_audit jsonb;
  with_members boolean; member boolean; prior_id text; prior_rows jsonb;
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
  with_members:=coalesce(proof->>'purpose'='schubert_lied_identities_v2',false);
  if (not with_members and proof->>'purpose' is distinct from 'schubert_lied_identities_v1') or proof->>'composer' is distinct from 'Franz Schubert'
    or jsonb_typeof(proof->'works') is distinct from 'array' or jsonb_array_length(proof->'works') not between 1 and 60
    then return '{"status":"unsupported_catalogue_authority","items":0}';end if;
  for c in select value from jsonb_array_elements(p_candidates) loop
    pos:=(c->>'position')::int;wid:=(c->>'work_id')::uuid;
    if pos is null or pos<=last_pos or pos>=jsonb_array_length(songs) or wid is null then return '{"status":"invalid_candidates","items":0}';end if;
    last_pos:=pos;s:=songs->pos;num:=s->>'number';title:=s->>'title';
    member:=(s->>'member') is not null;
    if (member and not with_members) or s->'line' is distinct from c->'line' then return '{"status":"unsupported_member_or_line","items":0}';end if;
    select count(*),(jsonb_agg(v)->0) into idx,ref from jsonb_array_elements(proof->'works') v
      where v->>'number'=num and v->'member'=s->'member' and v->'title_forms' ? title;
    if idx<>1 or ref->>'work_id' is distinct from wid::text or coalesce(ref->>'source_url','')!~'^https://[^/[:space:]]+/.+'
      or coalesce(ref->>'reference','')='' then return '{"status":"ambiguous_catalogue_authority","items":0}';end if;
    select * into w from public.works where id=wid for share;
    if not found or w.slug is distinct from ref->>'work_slug' or w.title is distinct from ref->>'canonical_title'
      or w.composer_id::text is distinct from proof->>'composer_id' then return '{"status":"identity_changed","items":0}';end if;
    select name into composer from public.composers where id=w.composer_id for share;
    if composer is distinct from 'Franz Schubert' then return '{"status":"wrong_composer","items":0}';end if;
    if member then
      if not public.kopis_verified_lied_member(s, ref, w) then return '{"status":"member_identity_not_verified","items":0}';end if;
    elsif not (regexp_replace(coalesce(w.catalogue,''),'[. ]','','g')='D'||num or (w.catalogue is null and exists(select from public.work_aliases x
      where x.work_id=wid and regexp_replace(x.alias,'[. ]','','g')='D'||num))) or exists(select from public.works other where other.composer_id=w.composer_id and other.id<>wid
        and (regexp_replace(other.catalogue,'[. ]','','g')='D'||num or exists(select from public.work_aliases x where x.work_id=other.id and regexp_replace(x.alias,'[. ]','','g')='D'||num)))
      then return '{"status":"catalogue_number_not_unique","items":0}';end if;
    if not member and w.title not in (title,s->>'literal') and not exists(select from public.work_aliases x where x.work_id=wid and x.alias in (title,s->>'literal'))
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
  -- Extend only a previously audited snapshot of this same performance and same sources.
  if current_rows<>'[]'::jsonb then
    if not with_members or p.program_status::text is distinct from 'partially_confirmed'
      or p.program_source_url is distinct from url or p.program_image_urls is distinct from p.intro_image_urls
      or not program @> current_rows or jsonb_array_length(program)<=jsonb_array_length(current_rows)
      or exists(select from public.program_items where performance_id=p_id and coalesce(confidence,0)<>0)
      then return '{"status":"existing_program_preserved","items":0}';end if;
    select provider_id into prior_id from public.provider_records
      where provider='kopis' and entity_type='typed_recital_publication' and provider_id like p_id::text||':%'
        and payload->>'performance_id'=p_id::text and payload->'after'=current_rows
        and payload->>'official_url'=url and payload->>'date'=p.starts_on::text
        and payload->>'cover_url'=cover and payload->>'cover_sha256'=sha and payload->>'envelope_sha256'=rd
        and payload->>'sty_sha256'=h and payload->>'sty'=d->>'sty' and payload->>'cover_reading_key'=p_document->>'reading_key'
        and (payload->>'checked_at')::timestamptz=p.program_source_updated_at
      order by provider_id limit 1 for share;
    if prior_id is null then return '{"status":"prior_evidence_changed","items":0}';end if;
    select jsonb_agg(to_jsonb(pi) order by position) into prior_rows from public.program_items pi where performance_id=p_id;
  elsif p.program_status::text is distinct from 'unknown' or p.program_source_url is not null or cardinality(p.program_image_urls)>0
    then return '{"status":"existing_program_preserved","items":0}';end if;
  if p_expected is null then return jsonb_build_object('status','ready','items',jsonb_array_length(program),'program',program);end if;
  before_audit:=jsonb_build_object('version',case when with_members then 'kopis-typed-lieder-v2' else 'kopis-typed-lieder-v1' end,
    'previous_audit',prior_id,'previous_program_rows',coalesce(prior_rows,'[]'::jsonb),'performance_id',p_id,'before',current_rows,'before_performance',to_jsonb(p),'after',program,
    'date',p.starts_on,'venue',d->>'fcltynm','schedule',d->>'dtguidance','official_url',url,'sty',d->>'sty','sty_sha256',h,'total_songs',jsonb_array_length(songs),
    'source_indices',p_candidates,'catalogue_authority',k,'cover_url',cover,'cover_sha256',sha,'envelope_sha256',rd,'cover_reading_key',p_document->>'reading_key',
    'cover_reading_sha256',ptr->>'reading_sha256','cover_contribution','event_identity_only','checked_at',checked);
  insert into public.provider_records(provider,entity_type,provider_id,payload)values('kopis','typed_recital_publication',audit_key,before_audit);
  insert into public.program_items(performance_id,position,work_id,composer_name,display_title,performed_scope,scope_details,source_url,source_type,source_provider)
    select p_id,(v->>'position')::int,(v->>'work_id')::uuid,v->>'composer_name',v->>'display_title','unknown','[]'::jsonb,url,'official','kopis' from jsonb_array_elements(program) v
    where not exists(select from public.program_items pi where pi.performance_id=p_id and pi.position=(v->>'position')::int);
  update public.performances set program_status='partially_confirmed',program_source_url=url,program_image_urls=p.intro_image_urls,program_source_updated_at=checked where id=p_id;
  return jsonb_build_object('status','published','items',jsonb_array_length(program));
exception when data_exception then return '{"status":"invalid_evidence","items":0}';
end $$;
revoke all on function public.kopis_lied_catalogue_key(text),public.kopis_verified_lied_member(jsonb,jsonb,public.works) from public,anon,authenticated;
grant execute on function public.kopis_lied_catalogue_key(text),public.kopis_verified_lied_member(jsonb,jsonb,public.works) to service_role;
notify pgrst,'reload schema';
