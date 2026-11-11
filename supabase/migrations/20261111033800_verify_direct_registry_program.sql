-- An independent catalogue can identify the parent work, never the performed edition.
create function public.direct_registry_item(r jsonb, ref jsonb, frozen jsonb, section int, wid uuid, proof_key text)
returns jsonb language plpgsql volatile security invoker set search_path='' as $$
declare
  ptr jsonb; proof jsonb; raw text; fields jsonb:=frozen->'fields'; w public.works; author public.composers;
  ls jsonb:=r->'lines'; a int; t int; credit text; title_line text; printed_name text:=fields->>'composer'; printed_title text:=fields->>'title';
  opus text:=fields->>'catalogue'; tonality text:=fields->>'key'; ambiguous boolean;
begin
  if section is null or coalesce(proof_key,'')!~'^[a-f0-9]{64}$' or wid is null or coalesce(printed_name,'')='' or coalesce(printed_title,'')=''
    or frozen->'evidence' is distinct from ref or frozen->>'context' is distinct from 'program'
    or ref->>'context' is distinct from 'program' or ref->>'scope' is distinct from 'full_work'
    or jsonb_array_length(ref->'composer') is distinct from 1 or jsonb_array_length(ref->'title') is distinct from 1
    or coalesce(ref#>>'{composer,0,line_id}','')!~'^L[0-9]{6}$' or coalesce(ref#>>'{title,0,line_id}','')!~'^L[0-9]{6}$'
    then return null;end if;
  a:=substr(ref#>>'{composer,0,line_id}',2)::int;t:=substr(ref#>>'{title,0,line_id}',2)::int;
  if a<=section or t<>a+1 or ref#>>'{composer,0,quote}' is distinct from printed_name or ref#>>'{title,0,quote}' is distinct from printed_title then return null;end if;
  if exists(select from jsonb_array_elements(ls) with ordinality l(v,n) where n>section+1 and
    (v->>'text') ~* '(편곡|발췌|편집|개정|판본|취소|대체|변경|(^|[^a-z])(arr\.|arranged|arrangement|version|adaptation|edition|excerpts?|transcription|revised|completed by)([^a-z]|$))') then return null;end if;
  credit:=regexp_replace(regexp_replace(ls->a->>'text','^[IVX]+[.]? +',''),' +\([12][0-9]{3} *[-–] *([12][0-9]{3})?\)$','');
  title_line:=ls->t->>'text';
  if credit is distinct from printed_name then return null;end if;
  select payload into ptr from public.provider_records where provider='catalogue_repair' and entity_type='parent_work_authority' and provider_id=proof_key for share;
  raw:=ptr->>'proof_utf8';
  if raw is null or octet_length(raw) not between 2 and 16384 or ptr->>'bucket' is distinct from 'classic-hubble-sources'
    or encode(sha256(convert_to(raw,'UTF8')),'hex') is distinct from proof_key or ptr->>'result_sha256' is distinct from proof_key
    or ptr->>'result_object_key' is distinct from 'extractions/sha256/'||left(proof_key,2)||'/'||proof_key then return null;end if;
  proof:=raw::jsonb;
  if proof->>'purpose' is distinct from 'canonical_parent_identity_v1' or proof->>'work_id' is distinct from wid::text
    or proof->'edition_identified' is distinct from 'false'::jsonb or coalesce(proof->>'source_url','')!~'^https://[^/[:space:]]+/.+'
    or jsonb_typeof(proof->'title_forms') is distinct from 'array' or not coalesce(proof->'title_forms' ? printed_title,false)
    then return null;end if;
  select * into w from public.works where id=wid for share;
  if not found or proof->>'work_slug' is distinct from w.slug or proof->>'canonical_title' is distinct from w.title
    or proof->>'composer_id' is distinct from w.composer_id::text or not(proof?'catalogue') or proof->>'catalogue' is distinct from w.catalogue then return null;end if;
  select * into author from public.composers where id=w.composer_id for share;
  if not found or proof->>'composer' is distinct from author.name or not public.direct_printed_composer(printed_name,author.name,author.name_ko) then return null;end if;
  if lower(printed_title) is distinct from lower(w.title) and lower(printed_title) is distinct from lower(w.title_ko) and not exists(
    select from public.work_aliases x where x.work_id=wid and x.source like 'verified:https://%' and lower(x.alias)=lower(printed_title)) then return null;end if;

  if frozen->>'scope'='full_work' then
    if frozen->>'reason' is distinct from 'composer_and_alias' or frozen->>'identity_reason' is distinct from 'composer_and_alias'
      or frozen->'candidate_ids' is distinct from jsonb_build_array(wid) or frozen->>'suggested_work_id' is distinct from wid::text
      or frozen->>'scoped_work_id' is not null or ref->'catalogue' is distinct from 'null'::jsonb or ref->'key' is distinct from 'null'::jsonb
      or ref->'movements' is distinct from '[]'::jsonb or title_line is distinct from printed_title
      or fields is distinct from jsonb_build_object('title',printed_title,'composer',printed_name,'key',null,'catalogue',null,'movements','[]'::jsonb)
      then return null;end if;
  elsif frozen->>'scope'='unknown' then
    if frozen->>'reason' is distinct from 'scope_requires_review' or frozen->>'identity_reason' is distinct from 'no_candidate'
      or frozen->'candidate_ids' is distinct from '[]'::jsonb or frozen->>'scoped_work_id' is not null or frozen->>'suggested_work_id' is not null
      or public.direct_movement_citations(r,ref,section) is distinct from fields
      or tonality is null or proof->>'tonality' is distinct from tonality or opus is null or w.catalogue is distinct from opus
      or opus !~ '^(K|Op)\. [1-9][0-9]{0,3}$' or title_line is distinct from printed_title||' in '||tonality||', '||opus
      or jsonb_array_length(ref->'key') is distinct from 1 or ref#>>'{key,0,line_id}' is distinct from ref#>>'{title,0,line_id}'
      or jsonb_array_length(ref->'catalogue') is distinct from 1 or ref#>>'{catalogue,0,line_id}' is distinct from ref#>>'{title,0,line_id}'
      then return null;end if;
  else return null;end if;

  select exists(select from public.works other join public.composers c on c.id=other.composer_id
    where other.id<>wid and public.direct_printed_composer(printed_name,c.name,c.name_ko) and (
      (opus is not null and regexp_replace(upper(regexp_replace(other.catalogue,'[ .]','','g')),'^KV','K')=upper(regexp_replace(opus,'[ .]','','g')))
      or lower(other.title)=lower(printed_title) or lower(other.title_ko)=lower(printed_title)
      or exists(select from public.work_aliases x where x.work_id=other.id and lower(x.alias)=lower(printed_title)))) into ambiguous;
  if ambiguous then return null;end if;
  return fields;
exception when data_exception then return null;
end $$;
revoke all on function public.direct_registry_item(jsonb,jsonb,jsonb,int,uuid,text) from public,anon,authenticated;
grant execute on function public.direct_registry_item(jsonb,jsonb,jsonb,int,uuid,text) to service_role;

-- Both modes use the same original-byte check, row lock, history and preview comparison.
do $migration$
declare
  def text:=pg_get_functiondef('public.publish_direct_movement_program(uuid,jsonb,jsonb,jsonb)'::regprocedure);
  anchor text:='    fields:=public.direct_movement_citations(r,ref,header);';
  branch text:=$branch$    if p_document->>'identity_mode'='independent_parent_registry_v1' then
      fields:=public.direct_registry_item(r,ref,e,header,wid,c->>'authority_key');
      if n<>1 or fields is null or scope<>'unknown' then return '{"status":"parent_authority_unverified","items":0}';end if;
      items:=items||jsonb_build_array(jsonb_build_object('position',idx,'work_id',wid,'composer_name',fields->>'composer',
        'display_title',concat_ws(' ',fields->>'title',fields->>'catalogue'),'performed_scope','unknown','scope_details',fields->'movements','source_url',url));
      continue;
    elsif p_document?'identity_mode' or c?'authority_key' then return '{"status":"unsupported_identity_mode","items":0}';end if;
$branch$;
  version_anchor text:='history:=jsonb_build_object(''version'',''direct-cited-movements-v1'',';
begin
  if length(def)-length(replace(def,anchor,''))<>length(anchor) or length(def)-length(replace(def,version_anchor,''))<>length(version_anchor)
    then raise exception 'Unexpected dated programme signature';end if;
  def:=replace(def,anchor,branch||anchor);
  execute replace(def,version_anchor,'history:=jsonb_build_object(''version'',case when p_document->>''identity_mode''=''independent_parent_registry_v1'' then ''direct-parent-registry-v1'' else ''direct-cited-movements-v1'' end,');
end $migration$;
notify pgrst,'reload schema';
