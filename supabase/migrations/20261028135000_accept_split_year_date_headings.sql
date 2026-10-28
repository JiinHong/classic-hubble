-- Accept the validated split-year worker contract without changing other guards.
do $$
declare
  signature text;
  old_guard text;
  new_guard text;
  definition text;
begin
  for signature, old_guard, new_guard in
    select * from (values
      ('public.publish_paddle_program_v1(uuid,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)',
       'or coalesce(p_evaluation->>''date_binding_version'','''') not in (''concert-date-headings-v5'',''concert-date-headings-v6'',''concert-date-headings-v7'',''concert-date-headings-v8'',''concert-date-headings-v9'',''concert-date-headings-v10'',''concert-date-headings-v11'')',
       'or coalesce(p_evaluation->>''date_binding_version'','''') not in (''concert-date-headings-v5'',''concert-date-headings-v6'',''concert-date-headings-v7'',''concert-date-headings-v8'',''concert-date-headings-v9'',''concert-date-headings-v10'',''concert-date-headings-v11'',''concert-date-headings-v12'')'),
      ('public.publish_paddle_program_bundle(uuid,jsonb,jsonb,jsonb,jsonb)',
       'or coalesce(p_evaluation->>''date_binding_version'','''') not in (''concert-date-headings-v7'',''concert-date-headings-v8'',''concert-date-headings-v9'',''concert-date-headings-v10'',''concert-date-headings-v11'')',
       'or coalesce(p_evaluation->>''date_binding_version'','''') not in (''concert-date-headings-v7'',''concert-date-headings-v8'',''concert-date-headings-v9'',''concert-date-headings-v10'',''concert-date-headings-v11'',''concert-date-headings-v12'')')
    ) as guards(signature, old_guard, new_guard)
  loop
    definition := pg_get_functiondef(signature::regprocedure);
    if strpos(definition, new_guard) > 0 then continue; end if;
    if strpos(definition, old_guard) = 0
      or length(definition)-length(replace(definition,old_guard,'')) <> length(old_guard)
    then raise exception 'Unexpected date contract for %; manual review required', signature; end if;
    execute replace(definition,old_guard,new_guard);
  end loop;
end;
$$;
notify pgrst,'reload schema';
