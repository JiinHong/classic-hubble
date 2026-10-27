-- Add the strictly validated joined weekday/clock parser contract without
-- changing publication evidence, date, scope, permissions, or stale-source guards.
do $$
declare
  definition text;
  old_guard text := 'or coalesce(p_evaluation->>''date_binding_version'','''') not in (''concert-date-headings-v5'',''concert-date-headings-v6'')';
  new_guard text := 'or coalesce(p_evaluation->>''date_binding_version'','''') not in (''concert-date-headings-v5'',''concert-date-headings-v6'',''concert-date-headings-v7'')';
begin
  definition := pg_get_functiondef('public.publish_paddle_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)'::regprocedure);
  if strpos(definition, new_guard) > 0 then return; end if;
  if strpos(definition, old_guard) = 0
    or length(definition)-length(replace(definition,old_guard,'')) <> length(old_guard)
  then raise exception 'Unexpected Paddle date contract; manual review required'; end if;
  execute replace(definition,old_guard,new_guard);
end;
$$;
notify pgrst,'reload schema';
