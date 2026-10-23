-- Private corrections retain both observations; published sources need reconciliation.
create or replace function public.revise_private_direct_reading(
  p_key text, p_expected_reading jsonb, p_new_reading jsonb,
  p_proposal_id uuid, p_expected_proposal jsonb, p_expected_sources jsonb
) returns jsonb
language plpgsql security invoker set search_path = ''
as $$
declare
  v_row record;
  v_sources jsonb := '[]';
  v_current jsonb;
  v_proposal jsonb;
  v_revision jsonb;
  v_identity text;
begin
  -- Match the publisher's source -> reading lock order. No programme rows change.
  for v_row in
    select payload from public.provider_records
    where provider = 'r2' and entity_type = 'source_archive'
      and payload->>'sha256' = p_expected_reading->>'source_sha256'
      and payload->>'bucket' = p_expected_reading->>'bucket'
      and payload->>'object_key' = p_expected_reading->>'source_object_key'
    order by id for update
  loop
    v_sources := v_sources || jsonb_build_array(jsonb_build_object(
      'source_url', v_row.payload->'source_url', 'content_type', v_row.payload->'content_type',
      'performance_ids', v_row.payload->'performance_ids', 'checked_at', v_row.payload->'checked_at'));
  end loop;
  select coalesce(jsonb_agg(s order by s->>'source_url'), '[]'::jsonb) into v_sources
    from jsonb_array_elements(v_sources) s;
  if v_sources = '[]'::jsonb or v_sources is distinct from p_expected_sources
  then return jsonb_build_object('status', 'stale', 'published_items', 0); end if;

  select payload into v_current from public.provider_records
    where provider = 'codex_vision' and entity_type = 'direct_reading' and provider_id = p_key
    for update;
  if not found then return jsonb_build_object('status', 'stale', 'published_items', 0); end if;
  select payload into v_proposal from public.provider_records
    where id = p_proposal_id and provider = 'codex_vision'
      and entity_type = 'direct_reading_correction_proposal' for update;
  if not found or v_proposal is distinct from p_expected_proposal
  then return jsonb_build_object('status', 'stale', 'published_items', 0); end if;

  foreach v_identity in array array['source_sha256','source_object_key','bucket','method','pipeline_version']
  loop
    if p_expected_reading->>v_identity is null
      or p_new_reading->>v_identity is distinct from p_expected_reading->>v_identity
    then raise exception 'Invalid correction evidence'; end if;
  end loop;
  if p_new_reading->>'method' is distinct from 'chat_model_direct_image_reading'
    or p_new_reading->>'pipeline_version' is distinct from 'codex-direct-vision-v1'
    or p_expected_reading->>'source_sha256' is distinct from v_proposal->>'source_sha256'
    or p_expected_reading->>'bucket' is distinct from v_proposal->>'bucket'
    or v_proposal->>'status' is distinct from 'pending_revision_workflow'
    or p_expected_reading->>'reading_sha256' is distinct from v_proposal->>'supersedes_reading_sha256'
    or p_new_reading->>'reading_sha256' is distinct from v_proposal->>'corrected_reading_sha256'
    or not coalesce(p_new_reading->>'reading_sha256' ~ '^[a-f0-9]{64}$', false)
    or not coalesce(p_expected_reading->>'reading_sha256' ~ '^[a-f0-9]{64}$', false)
    or p_new_reading->>'reading_sha256' = p_expected_reading->>'reading_sha256'
    or not coalesce(p_new_reading->>'result_sha256' ~ '^[a-f0-9]{64}$', false)
    or p_new_reading->>'result_object_key' is distinct from
      'extractions/sha256/' || left(p_new_reading->>'result_sha256', 2) || '/' || (p_new_reading->>'result_sha256')
    or p_new_reading->'revision' is distinct from jsonb_build_object(
      'proposal_id', p_proposal_id, 'previous_reading_sha256', p_expected_reading->>'reading_sha256')
  then raise exception 'Invalid correction evidence'; end if;

  select payload into v_revision from public.provider_records
    where provider = 'codex_vision' and entity_type = 'direct_reading_revision'
      and provider_id = p_proposal_id::text;
  if found then
    if v_revision->'before' = p_expected_reading and v_revision->'proposal' = p_expected_proposal
      and v_revision->'after' = v_current
      and (v_current - 'stored_at') = (p_new_reading - 'stored_at')
    then return jsonb_build_object('status', 'unchanged', 'published_items', 0); end if;
    return jsonb_build_object('status', 'stale', 'published_items', 0);
  end if;
  if v_current is distinct from p_expected_reading
  then return jsonb_build_object('status', 'stale', 'published_items', 0); end if;

  -- The shared reading lock serializes this check against publication's audit insert.
  if exists (select 1 from public.provider_records
    where provider = 'codex_vision' and entity_type = 'program_publication'
      and payload#>>'{source,sha256}' = v_current->>'source_sha256'
      and payload#>>'{source,bucket}' = v_current->>'bucket')
  then return jsonb_build_object('status', 'published_source_requires_reconciliation', 'published_items', 0); end if;

  insert into public.provider_records(provider, entity_type, provider_id, payload)
    values ('codex_vision', 'direct_reading_revision', p_proposal_id::text,
      jsonb_build_object('before', v_current, 'after', p_new_reading, 'proposal_id', p_proposal_id,
        'proposal', v_proposal, 'sources', v_sources, 'revised_at', now()));
  update public.provider_records set payload = p_new_reading
    where provider = 'codex_vision' and entity_type = 'direct_reading' and provider_id = p_key;
  return jsonb_build_object('status', 'revised', 'published_items', 0);
end;
$$;
revoke all on function public.revise_private_direct_reading(text,jsonb,jsonb,uuid,jsonb,jsonb) from public, anon, authenticated;
grant execute on function public.revise_private_direct_reading(text,jsonb,jsonb,uuid,jsonb,jsonb) to service_role;
notify pgrst, 'reload schema';
