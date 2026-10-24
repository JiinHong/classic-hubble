-- Python verifies immutable OCR bytes/quotes and recomputes matches. SQL locks and
-- rechecks their current pointers and binds the public subset to saved selections.
create or replace function public.publish_paddle_program(
  p_performance_id uuid, p_expected_performance jsonb, p_source jsonb,
  p_ocr jsonb, p_review jsonb, p_evaluation jsonb, p_items jsonb
) returns jsonb
language plpgsql security invoker set search_path = ''
as $$
declare
  perf public.performances;
  src jsonb; oc jsonb; rv jsonb; expected jsonb; before_rows jsonb;
  entry jsonb; reference jsonb; publication_key text;
begin
  select * into perf from public.performances where id=p_performance_id for update;
  if not found then return jsonb_build_object('status','missing_performance','items',0); end if;
  if jsonb_build_object('id',perf.id,'title',perf.title,'starts_on',perf.starts_on,
      'ends_on',perf.ends_on,'intro_image_urls',perf.intro_image_urls) is distinct from p_expected_performance
    or cardinality(perf.intro_image_urls) is distinct from 1
    or perf.starts_on is null or perf.starts_on is distinct from perf.ends_on
    or perf.intro_image_urls[1] is distinct from p_source->>'source_url'
  then return jsonb_build_object('status','stale','items',0); end if;
  select payload into src from public.provider_records
    where provider='r2' and entity_type='source_archive'
      and provider_id=encode(sha256(convert_to(p_source->>'source_url','UTF8')),'hex') for update;
  if not found or src is distinct from p_source
    or not coalesce(src->'performance_ids' ? p_performance_id::text,false)
  then return jsonb_build_object('status','stale','items',0); end if;
  select payload into oc from public.provider_records
    where provider='paddleocr' and entity_type='ocr_result'
      and payload->>'source_sha256'=src->>'sha256' and payload->>'bucket'=src->>'bucket'
    order by (payload->>'processed_at')::timestamptz desc, id desc limit 1 for update;
  if not found or oc is distinct from p_ocr or oc->>'status' is distinct from 'text_extracted'
    or oc->>'source_object_key' is distinct from src->>'object_key'
    or coalesce(oc->>'pipeline_version','') not like 'paddle-%'
    or exists(select 1 from public.provider_records where provider='paddleocr' and entity_type='ocr_result'
      and payload->>'source_sha256'=src->>'sha256' and payload->>'bucket'=src->>'bucket'
      and payload->>'result_sha256' <> oc->>'result_sha256'
      and (payload->>'processed_at')::timestamptz >= (oc->>'processed_at')::timestamptz)
  then return jsonb_build_object('status','stale','items',0); end if;
  select payload into rv from public.provider_records
    where provider='paddle_review' and entity_type='program_selection'
      and provider_id=p_review->>'review_id' for update;
  if not found or rv is distinct from p_review
    or rv->>'version' is distinct from 'paddle-partial-program-v1'
    or rv->>'method' is distinct from 'reviewed_paddle_text'
    or rv->>'source_sha256' is distinct from src->>'sha256'
    or rv->>'bucket' is distinct from src->>'bucket'
    or rv->>'document_sha256' is distinct from oc->>'result_sha256'
    or rv#>>'{response,document_sha256}' is distinct from oc->>'result_sha256'
  then return jsonb_build_object('status','stale','items',0); end if;
  if p_evaluation->>'publication_version' is distinct from 'paddle-partial-program-v1'
    or p_evaluation->>'performance_date' is distinct from perf.starts_on::text
    or p_evaluation->>'date_binding_version' is distinct from 'concert-date-headings-v5'
    or p_evaluation->>'live_sha256' is distinct from src->>'sha256'
    or p_evaluation->>'source_checked_at' is null
    or (p_evaluation->>'source_checked_at')::timestamptz < now()-interval '5 minutes'
    or (p_evaluation->>'source_checked_at')::timestamptz > now()+interval '1 minute'
    or p_evaluation#>>'{matching,document_sha256}' is distinct from oc->>'result_sha256'
    or p_evaluation#>>'{matching,validation_status}' is distinct from 'complete'
    or p_evaluation#>'{matching,source_warnings}' is distinct from '[]'::jsonb
    or p_evaluation#>'{matching,warnings}' is distinct from '[]'::jsonb
    or jsonb_typeof(p_evaluation#>'{matching,items}') is distinct from 'array'
    or jsonb_typeof(p_items) is distinct from 'array'
  then raise exception 'Incomplete Paddle publication evidence'; end if;
  if jsonb_array_length(p_items) not between 1 and 200 then raise exception 'Invalid item count'; end if;
  for entry in select value from jsonb_array_elements(p_evaluation#>'{matching,items}') loop
    if entry->>'publication_eligible' = 'true' then
      reference := rv#>'{response,items}'->(entry->>'source_index')::integer;
      if entry->>'context' is distinct from 'program' or entry->>'scope' is distinct from 'full_work'
        or entry->>'suggested_work_id' is null
        or coalesce(entry->>'reason','') not in ('composer_and_catalogue','composer_and_alias')
        or coalesce(entry#>>'{fields,composer}','') = ''
        or reference is null or reference is distinct from entry->'evidence'
        or reference->>'context' is distinct from 'program' or reference->>'scope' is distinct from 'full_work'
        or entry->>'source_index' is null or (entry->>'source_index')::integer < 0
      then raise exception 'Paddle item differs from reviewed evidence'; end if;
    end if;
  end loop;
  select coalesce(jsonb_agg(jsonb_build_object('work_id',m->>'suggested_work_id',
    'position',(m->>'source_index')::integer,
    'display_title',concat_ws(' ',nullif(m#>>'{fields,title}',''),nullif(m#>>'{fields,catalogue}','')),
    'composer_name',m#>>'{fields,composer}') order by (m->>'source_index')::integer),'[]'::jsonb)
    into expected from jsonb_array_elements(p_evaluation#>'{matching,items}') m where m->>'publication_eligible'='true';
  if expected is distinct from p_items
    or (select count(distinct i->>'position') from jsonb_array_elements(p_items) i) <> jsonb_array_length(p_items)
  then raise exception 'Public items differ from evaluated subset'; end if;
  perform 1 from public.program_items where performance_id=p_performance_id for update;
  if exists(select 1 from public.program_items where performance_id=p_performance_id and source_provider is distinct from 'paddleocr')
    or (perf.program_status='confirmed' and not exists(select 1 from public.program_items where performance_id=p_performance_id and source_provider='paddleocr'))
  then return jsonb_build_object('status','existing_program_preserved','items',0); end if;
  select coalesce(jsonb_agg(jsonb_build_object('work_id',work_id,'position',position,
    'display_title',display_title,'composer_name',composer_name) order by position),'[]'::jsonb)
    into expected from public.program_items where performance_id=p_performance_id and source_provider='paddleocr';
  if expected=p_items and perf.program_status::text='partially_confirmed'
    and exists(select 1 from public.provider_records where provider='paddle_review' and entity_type='program_publication'
      and payload->>'performance_id'=p_performance_id::text and payload->'review'=rv and payload->'source'=src and payload->'after'=p_items)
  then return jsonb_build_object('status','unchanged','items',jsonb_array_length(p_items)); end if;
  select coalesce(jsonb_agg(to_jsonb(i) order by position),'[]'::jsonb) into before_rows
    from public.program_items i where performance_id=p_performance_id and source_provider='paddleocr';
  publication_key := p_performance_id::text || ':' || md5(jsonb_build_object('review',rv,'items',p_items,'source',src,'before',before_rows)::text);
  insert into public.provider_records(provider,entity_type,provider_id,payload)
    values('paddle_review','program_publication',publication_key,jsonb_build_object('performance_id',p_performance_id,
      'before',before_rows,'before_performance',to_jsonb(perf),'after',p_items,'source',src,'ocr',oc,'review',rv,'evaluation',p_evaluation))
    on conflict(provider,entity_type,provider_id) do nothing;
  delete from public.program_items where performance_id=p_performance_id and source_provider='paddleocr';
  insert into public.program_items(performance_id,work_id,display_title,composer_name,source_type,confidence,position,source_provider,source_url)
    select p_performance_id,(i->>'work_id')::uuid,i->>'display_title',i->>'composer_name','ocr',0,(i->>'position')::integer,'paddleocr',src->>'source_url'
    from jsonb_array_elements(p_items) i;
  update public.performances set program_status='partially_confirmed', program_source_url=src->>'source_url',
    program_image_urls=intro_image_urls, program_source_updated_at=(p_evaluation->>'source_checked_at')::timestamptz where id=p_performance_id;
  return jsonb_build_object('status','published','items',jsonb_array_length(p_items));
end;
$$;
revoke all on function public.publish_paddle_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.publish_paddle_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb) to service_role;
notify pgrst,'reload schema';
