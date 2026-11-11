-- Resolve printed selections, never the whole collection or an unqualified alias.
-- BnF 13984028: FP 63 = nos. 1-10; FP 113 = 11-12; FP 170 = 13-14; FP 176 = 15.
create function public.paddle_numbered_excerpt(p_ref jsonb,p_composer text,p_title text)
returns uuid language plpgsql stable security invoker set search_path='' as $$
declare ranges text[]; part text; m text[]; lo integer; hi integer; last_hi integer := 0;
  total integer := 0; idx integer := 0; composer_line text; title_line text; parent uuid;
begin
  if p_ref->>'context' is distinct from 'program' or p_ref->>'scope' is distinct from 'excerpt'
    or p_ref->'key' is distinct from 'null'::jsonb or p_ref->'catalogue' is distinct from 'null'::jsonb
    or p_composer is distinct from '프랑시스 풀랑크' or p_composer is distinct from p_ref#>>'{composer,0,quote}'
    or p_title is null or length(p_title)>120 or p_title is distinct from p_ref#>>'{title,0,quote}'
    or p_title !~ '^즉흥곡 제[1-9][0-9]?번~제[1-9][0-9]?번(, *제[1-9][0-9]?번~제[1-9][0-9]?번)*$'
    or jsonb_array_length(p_ref->'composer') is distinct from 1 or jsonb_array_length(p_ref->'title') is distinct from 1
  then return null; end if;
  composer_line := p_ref#>>'{composer,0,line_id}'; title_line := p_ref#>>'{title,0,line_id}';
  if coalesce(composer_line,'') !~ '^L[0-9]{6}$' or coalesce(title_line,'') !~ '^L[0-9]{6}$'
    or substr(composer_line,2)::integer+1 <> substr(title_line,2)::integer then return null; end if;
  ranges := regexp_split_to_array(substr(p_title,length('즉흥곡 ')+1),', *');
  if jsonb_array_length(p_ref->'movements') is distinct from cardinality(ranges) then return null; end if;
  foreach part in array ranges loop
    m := regexp_match(part,'^제([1-9][0-9]?)번~제([1-9][0-9]?)번$');
    lo := m[1]::integer; hi := m[2]::integer;
    if lo <= last_hi or hi <= lo or hi > 15 or (p_ref->'movements'->idx) is distinct from
      jsonb_build_array(jsonb_build_object('line_id',title_line,'quote',part)) then return null; end if;
    last_hi := hi; total := total+hi-lo+1; idx := idx+1;
  end loop;
  -- Numbers confined to FP 63 cannot distinguish the two catalogued collections.
  if last_hi<=10 or total>=15 then return null; end if;
  select w.id into parent from public.works w join public.composers c on c.id=w.composer_id
    where w.slug='poulenc-quinze-improvisations' and w.title='Les Quinze Improvisations'
      and c.name='Francis Poulenc' and c.name_ko=p_composer and exists(select 1 from public.work_aliases a
        where a.work_id=w.id and a.source='verified:https://catalogue.bnf.fr/ark:/12148/cb139840284');
  return parent;
exception when data_exception then return null;
end;
$$;
revoke all on function public.paddle_numbered_excerpt(jsonb,text,text) from public,anon,authenticated;
grant execute on function public.paddle_numbered_excerpt(jsonb,text,text) to service_role;

do $migration$
declare sig constant regprocedure := 'public.publish_paddle_program_bundle(uuid,jsonb,jsonb,jsonb,jsonb)'::regprocedure;
  definition text := pg_get_functiondef(sig); old text; replacement text;
begin
  old := '      p_evaluation := p_evaluation - ''section_ocr_utf8'';';
  replacement := $guard$      if exists (
        select 1 from jsonb_array_elements(doc#>'{matching,items}') e
        cross join lateral (select (p_evaluation->>'section_ocr_utf8')::jsonb->'lines' as lines) o
        where e->>'publication_eligible'='true' and e->>'identity_reason'='composer_and_numbered_excerpt'
          and (e->>'suggested_work_id' is not null or e->>'scoped_work_id' is null
            or e->>'scoped_work_id' is distinct from public.paddle_numbered_excerpt(e->'evidence',
              o.lines->(substr(e#>>'{evidence,composer,0,line_id}',2)::int)->>'text',
              o.lines->(substr(e#>>'{evidence,title,0,line_id}',2)::int)->>'text')::text)
      ) then raise exception 'Invalid numbered excerpt'; end if;
$guard$ || old;
  if length(definition)-length(replace(definition,old,''))<>length(old) then raise exception 'Unexpected date proof'; end if;
  definition := replace(definition,old,replacement);
  old := $reason$coalesce(entry->>'identity_reason','') not in ('composer_and_catalogue','composer_and_alias')$reason$;
  replacement := '('||old||$reason$ and not coalesce(entry->>'identity_reason'='composer_and_numbered_excerpt'
            and doc->>'date_binding'='dated_section' and entry->>'scope'='excerpt',false))$reason$;
  if length(definition)-length(replace(definition,old,''))<>length(old) then raise exception 'Unexpected identity proof'; end if;
  definition := replace(definition,old,replacement);
  old := $preserve$where i->>'work_id'=old.work_id::text$preserve$;
  replacement := old||$preserve$ and (old.performed_scope is distinct from 'excerpt' or old.scope_details='[]'::jsonb
        or (i->>'performed_scope'='excerpt' and i->'scope_details'=old.scope_details))$preserve$;
  if length(definition)-length(replace(definition,old,''))<>length(old) then raise exception 'Unexpected existing programme guard'; end if;
  execute replace(definition,old,replacement);
end;
$migration$;
notify pgrst,'reload schema';
