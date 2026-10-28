-- Work identity and performed extent are independent facts. Legacy rows remain
-- NULL: absence of historical scope evidence must not become a full-work claim.
alter table public.program_items
  add column performed_scope text check (performed_scope in ('full_work','movement','excerpt','arrangement','unknown')),
  add column scope_details jsonb not null default '[]'::jsonb check (jsonb_typeof(scope_details)='array');

create or replace function public.publish_paddle_program_bundle(
  p_performance_id uuid, p_expected_performance jsonb, p_documents jsonb,
  p_evaluation jsonb, p_items jsonb
) returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
  perf public.performances;
  doc jsonb; src jsonb; oc jsonb; rv jsonb; entry jsonb; reference jsonb;
  expected jsonb := '[]'::jsonb; before_rows jsonb; current_items jsonb;
  identity text; source_index integer := 0; has_date boolean := false;
  publication_key text;
begin
  select * into perf from public.performances where id=p_performance_id for update;
  if not found then return jsonb_build_object('status','missing_performance','items',0); end if;
  if jsonb_build_object('id',perf.id,'title',perf.title,'starts_on',perf.starts_on,
      'ends_on',perf.ends_on,'intro_image_urls',perf.intro_image_urls) is distinct from p_expected_performance
    or perf.starts_on is null or perf.starts_on is distinct from perf.ends_on
  then return jsonb_build_object('status','stale','items',0); end if;
  if jsonb_typeof(p_documents) is distinct from 'array'
    or jsonb_array_length(p_documents) not between 1 and 50
    or jsonb_array_length(p_documents) is distinct from cardinality(perf.intro_image_urls)
    or (select count(distinct u) from unnest(perf.intro_image_urls) u) <> cardinality(perf.intro_image_urls)
    or p_evaluation->>'publication_version' is distinct from 'paddle-performance-bundle-v2'
    or p_evaluation->>'date_binding_version' is distinct from 'concert-date-headings-v7'
    or p_evaluation->>'performance_date' is distinct from perf.starts_on::text
    or jsonb_typeof(p_items) is distinct from 'array'
    or jsonb_array_length(p_items) not between 1 and 200
  then raise exception 'Incomplete performance evidence bundle'; end if;
  for doc in select value from jsonb_array_elements(p_documents) loop
    source_index := source_index + 1;
    if doc#>>'{source,source_url}' is distinct from perf.intro_image_urls[source_index]
    then return jsonb_build_object('status','stale','items',0); end if;
    select payload into src from public.provider_records
      where provider='r2' and entity_type='source_archive'
      and provider_id=encode(sha256(convert_to(doc#>>'{source,source_url}','UTF8')),'hex') for update;
    if not found or src is distinct from doc->'source'
      or not coalesce(src->'performance_ids' ? p_performance_id::text,false)
    then return jsonb_build_object('status','stale','items',0); end if;
    select payload into oc from public.provider_records
      where provider='paddleocr' and entity_type='ocr_result'
      and payload->>'source_sha256'=src->>'sha256' and payload->>'bucket'=src->>'bucket'
      order by (payload->>'processed_at')::timestamptz desc,id desc limit 1 for update;
    if not found or oc is distinct from doc->'ocr' or oc->>'status' is distinct from 'text_extracted'
      or oc->>'source_object_key' is distinct from src->>'object_key'
      or coalesce(oc->>'pipeline_version','') not like 'paddle-%'
      or exists(select 1 from public.provider_records where provider='paddleocr' and entity_type='ocr_result'
        and payload->>'source_sha256'=src->>'sha256' and payload->>'bucket'=src->>'bucket'
        and payload->>'result_sha256' <> oc->>'result_sha256'
        and (payload->>'processed_at')::timestamptz >= (oc->>'processed_at')::timestamptz)
    then return jsonb_build_object('status','stale','items',0); end if;
    select payload into rv from public.provider_records where provider='paddle_review' and entity_type='program_selection'
      and provider_id=doc#>>'{review,review_id}' for update;
    if not found or rv is distinct from doc->'review'
      or rv->>'version' is distinct from 'paddle-partial-program-v1'
      or rv->>'method' is distinct from 'reviewed_paddle_text'
      or rv->>'source_sha256' is distinct from src->>'sha256'
      or rv->>'bucket' is distinct from src->>'bucket'
      or rv->>'document_sha256' is distinct from oc->>'result_sha256'
      or rv#>>'{response,document_sha256}' is distinct from oc->>'result_sha256'
      or coalesce(rv#>>'{response,status}','') not in ('items_extracted','no_program_identified')
    then return jsonb_build_object('status','stale','items',0); end if;
    if coalesce(doc->>'date_binding','') not in ('target','absent')
      or doc->>'live_sha256' is distinct from src->>'sha256'
      or doc->>'source_checked_at' is null
      or (doc->>'source_checked_at')::timestamptz < now()-interval '5 minutes'
      or (doc->>'source_checked_at')::timestamptz > now()+interval '1 minute'
      or doc#>>'{matching,document_sha256}' is distinct from oc->>'result_sha256'
      or doc#>>'{matching,validation_status}' is distinct from 'complete'
      or doc#>'{matching,source_warnings}' is distinct from '[]'::jsonb
      or doc#>'{matching,warnings}' is distinct from '[]'::jsonb
      or jsonb_typeof(doc#>'{matching,items}') is distinct from 'array'
    then raise exception 'Incomplete bundle document evidence'; end if;
    has_date := has_date or doc->>'date_binding'='target';
    for entry in select value from jsonb_array_elements(doc#>'{matching,items}') loop
      if entry->>'publication_eligible'='true' then
        reference := rv#>'{response,items}'->(entry->>'source_index')::integer;
        identity := coalesce(entry->>'suggested_work_id',entry->>'scoped_work_id');
        if entry->>'context' is distinct from 'program'
          or coalesce(entry->>'scope','') not in ('full_work','movement','excerpt','arrangement','unknown')
          or identity is null
          or coalesce(entry->>'identity_reason','') not in ('composer_and_catalogue','composer_and_alias')
          or coalesce(entry#>>'{fields,composer}','')=''
          or entry ? 'derived_from' or reference is null or reference is distinct from entry->'evidence'
          or reference->>'context' is distinct from 'program'
          or entry->>'model_scope' is distinct from reference->>'scope'
          or (reference->>'scope' is distinct from entry->>'scope' and not
            (reference->>'scope'='full_work' and entry->>'scope' in ('movement','excerpt','unknown')))
          or entry->>'source_index' is null or (entry->>'source_index')::integer < 0
          or jsonb_typeof(entry#>'{fields,movements}') is distinct from 'array'
        then raise exception 'Bundle item differs from reviewed evidence'; end if;
        expected := expected || jsonb_build_array(jsonb_build_object('work_id',identity,
          'position',jsonb_array_length(expected),'display_title',
          concat_ws(' ',nullif(entry#>>'{fields,title}',''),nullif(entry#>>'{fields,catalogue}','')),
          'composer_name',entry#>>'{fields,composer}','performed_scope',entry->>'scope',
          'scope_details',entry#>'{fields,movements}','source_url',src->>'source_url'));
      end if;
    end loop;
  end loop;
  if not has_date then raise exception 'Bundle has no verified performance date'; end if;
  if expected is distinct from p_items or
    (select count(distinct jsonb_build_array(i->'work_id',i->'performed_scope',i->'scope_details'))
      from jsonb_array_elements(p_items) i) <> jsonb_array_length(p_items)
  then raise exception 'Public items differ from bundle subset'; end if;
  perform 1 from public.program_items where performance_id=p_performance_id for update;
  if exists(select 1 from public.program_items where performance_id=p_performance_id and source_provider is distinct from 'paddleocr')
    or (perf.program_status='confirmed' and not exists(select 1 from public.program_items where performance_id=p_performance_id and source_provider='paddleocr'))
  then return jsonb_build_object('status','existing_program_preserved','items',0); end if;
  select coalesce(jsonb_agg(jsonb_build_object('work_id',work_id,'position',position,'display_title',display_title,
    'composer_name',composer_name,'performed_scope',performed_scope,'scope_details',scope_details,'source_url',source_url)
    order by position),'[]'::jsonb) into current_items from public.program_items where performance_id=p_performance_id;
  if current_items=p_items and perf.program_status::text='partially_confirmed'
    and exists(select 1 from public.provider_records where provider='paddle_review' and entity_type='bundle_publication'
      and payload->>'performance_id'=p_performance_id::text and payload->'after'=p_items
      and payload->'evidence_identity'=(select jsonb_agg(jsonb_build_object('source',d->'source','ocr',d->'ocr','review',d->'review')) from jsonb_array_elements(p_documents) d))
  then return jsonb_build_object('status','unchanged','items',jsonb_array_length(p_items)); end if;
  -- A new subset must not silently erase earlier confirmed identities.
  if exists(select 1 from public.program_items old where old.performance_id=p_performance_id
      and old.work_id is not null and not exists(select 1 from jsonb_array_elements(p_items) i where i->>'work_id'=old.work_id::text))
  then return jsonb_build_object('status','existing_program_preserved','items',0); end if;
  select coalesce(jsonb_agg(to_jsonb(i) order by position),'[]'::jsonb) into before_rows
    from public.program_items i where performance_id=p_performance_id;
  publication_key := p_performance_id::text||':'||md5(jsonb_build_object('documents',p_documents,'items',p_items,'before',before_rows)::text);
  insert into public.provider_records(provider,entity_type,provider_id,payload) values('paddle_review','bundle_publication',publication_key,
    jsonb_build_object('performance_id',p_performance_id,'before',before_rows,'before_performance',to_jsonb(perf),'after',p_items,
      'documents',p_documents,'evaluation',p_evaluation,'evidence_identity',
      (select jsonb_agg(jsonb_build_object('source',d->'source','ocr',d->'ocr','review',d->'review')) from jsonb_array_elements(p_documents) d)))
    on conflict(provider,entity_type,provider_id) do nothing;
  delete from public.program_items where performance_id=p_performance_id and source_provider='paddleocr';
  insert into public.program_items(performance_id,work_id,display_title,composer_name,source_type,confidence,position,
      source_provider,source_url,performed_scope,scope_details)
    select p_performance_id,(i->>'work_id')::uuid,i->>'display_title',i->>'composer_name','ocr',0,
      (i->>'position')::integer,'paddleocr',i->>'source_url',i->>'performed_scope',i->'scope_details'
    from jsonb_array_elements(p_items) i;
  update public.performances set program_status='partially_confirmed', program_source_url=perf.intro_image_urls[1],
    program_image_urls=intro_image_urls,program_source_updated_at=now() where id=p_performance_id;
  return jsonb_build_object('status','published','items',jsonb_array_length(p_items));
end;
$$;
revoke all on function public.publish_paddle_program_bundle(uuid,jsonb,jsonb,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.publish_paddle_program_bundle(uuid,jsonb,jsonb,jsonb,jsonb) to service_role;

-- Old workers may still publish full-work-only subsets. Keep their contract,
-- but do not let it discard the extent/provenance recorded by the bundle path.
alter function public.publish_paddle_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)
  rename to publish_paddle_program_v1;
create function public.publish_paddle_program(
  p_performance_id uuid, p_expected_performance jsonb, p_source jsonb,
  p_ocr jsonb, p_review jsonb, p_evaluation jsonb, p_items jsonb
) returns jsonb language plpgsql security invoker set search_path = '' as $$
begin
  perform 1 from public.performances where id=p_performance_id for update;
  if exists(select 1 from public.program_items where performance_id=p_performance_id and performed_scope is not null)
  then return jsonb_build_object('status','existing_program_preserved','items',0); end if;
  return public.publish_paddle_program_v1(p_performance_id,p_expected_performance,p_source,p_ocr,p_review,p_evaluation,p_items);
end;
$$;
revoke all on function public.publish_paddle_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.publish_paddle_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb) to service_role;
notify pgrst,'reload schema';
