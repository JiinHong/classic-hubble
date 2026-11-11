begin;
do $test$
declare
  c uuid := gen_random_uuid(); w uuid := gen_random_uuid(); w2 uuid := gen_random_uuid();
  other_c uuid := gen_random_uuid(); tribute uuid := gen_random_uuid();
  v uuid := gen_random_uuid(); first_id uuid := gen_random_uuid(); second_id uuid := gen_random_uuid();
  upcoming_id uuid := gen_random_uuid(); r record;
begin
  insert into public.composers(id,name,name_ko) values(c,'History Fixture Composer','검증 전용작곡가');
  insert into public.works(id,slug,title,composer_id) values
    (w,'fixture-'||w,'Fixture sonata',c),(w2,'fixture-'||w2,'Fixture concerto',c);
  insert into public.composers(id,name) values(other_c,'Different Fixture Composer');
  insert into public.works(id,slug,title,composer_id) values(tribute,'fixture-'||tribute,'Different composition',other_c);
  insert into public.work_aliases(work_id,alias) values(tribute,'검증 전용작곡가에게');
  if not exists(select 1 from public.concert_rank_work_candidates('전용작곡가','검증 전용작곡가') where id=tribute)
    or exists(select 1 from public.concert_rank_work_candidates('전용작곡가','검증 전용작곡가') where id=w)
    then raise exception 'composer shortcut suppressed another composer alias or fetched redundant work'; end if;
  insert into public.venues(id,name,city) values(v,'검증회관','검증시');
  insert into public.performances(id,kopis_performance_id,venue_id,title,starts_at,ends_on,status,artists) values
    (first_id,'fixture-'||first_id,v,'정기연주회','2020-01-01',null,'closed','{}'),
    (second_id,'fixture-'||second_id,v,'정기연주회','2021-01-01',null,'upcoming',array['X%_Y']),
    (upcoming_id,'fixture-'||upcoming_id,v,'검증회차',(now()-interval '1 day'),((now() at time zone 'Asia/Seoul')::date+1),'open','{}');
  insert into public.program_items(performance_id,work_id,display_title,position) values
    (first_id,w,'Fixture sonata',0),(second_id,w,'Fixture sonata',0),
    (second_id,w2,'Fixture concerto',1),(upcoming_id,w2,'Fixture concerto',0);
  select * into strict r from public.concert_search_page('검증 전용작곡가','검증시','{}','all',0);
  if r.past_count<>2 or r.upcoming_count<>1 or r.performance_ids<>array[upcoming_id,second_id,first_id]
    or r.match_slugs[2] <> 'fixture-'||w then raise exception 'composer history, grouping or displayed match: %',r; end if;
  select * into strict r from public.concert_search_page(null,'검증시',array[w],'past',1);
  if r.performance_ids<>array[first_id] or r.past_count<>2 then raise exception 'exact work page: %',r; end if;
  select * into strict r from public.concert_search_page('검증 전용작곡가','다른검증시','{}','past',0);
  if r.past_count<>0 or cardinality(r.performance_ids)<>0 or r.available_cities<>array['검증시'] then raise exception 'city filter / options'; end if;
  select * into strict r from public.concert_search_page('%_','검증시','{}','all',0);
  if r.performance_ids<>array[second_id] or r.match_slugs[1] is not null then raise exception 'literal wildcard or false work credit'; end if;
  select * into strict r from public.concert_search_page('정기연주회 검증회관','검증시','{}','past',24);
  if cardinality(r.performance_ids)<>0 or r.past_count<>2 then raise exception 'cross-field literal / end of pagination'; end if;
end $test$;
rollback;
