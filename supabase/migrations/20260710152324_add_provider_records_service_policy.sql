create policy "provider records are service-role managed"
  on public.provider_records for all
  to service_role
  using (true)
  with check (true);
