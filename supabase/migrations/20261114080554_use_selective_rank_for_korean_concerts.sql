create or replace function public.concert_rank_work_candidates(search_term text, literal_name text)
returns setof public.works language sql stable security invoker set search_path = '' as $$
  select w.* from public.search_work_candidates_v2(search_term) w
  where w.composer_id not in (select public.concert_named_composers(literal_name))
$$;

insert into public.work_aliases(work_id,alias,locale,source)
select w.id,v.alias,'ko',v.source
from (values
  ('reviewed-schumann-dichterliebe-op48','Op. 48','Robert Schumann','시인의 사랑','https://simf.kr/product/detail.html?product_no=563'),
  ('wikidata-q4120798','BWV 578','Johann Sebastian Bach','작은 푸가','https://musopen.org/ko/music/3665-fugue-in-g-minor-little-bwv-578/')
) as v(slug,catalogue,composer,alias,source)
join public.works w on w.slug=v.slug and w.catalogue=v.catalogue
join public.composers c on c.id=w.composer_id and c.name=v.composer
on conflict(work_id,alias) do nothing;
