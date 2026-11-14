-- Result narrowing must retain the canonical row for Korean concert searches.
begin;
set local role anon;
do $$
declare ex record;
begin
 for ex in select * from (values
 ('슈만','슈만 헌정','schumann-widmung-op25-no1'),
 ('작은','작은 푸가','wikidata-q4120798'),
 ('시인의','시인의 사랑','reviewed-schumann-dichterliebe-op48')
 ) t(anchor,term,slug)
 loop
  if not exists(select from public.concert_rank_work_candidates(ex.anchor,ex.term) where slug=ex.slug)
  then raise exception 'missing concert candidate: %', ex.term; end if;
 end loop;
 if not (public.concert_bigrams('작은 푸가') @> array['작은','푸가'])
    or public.concert_bigrams('작은 푸가') @> array['작가']
    or public.concert_bigrams('가나') @> array['가%']
    or public.concert_bigrams('가나') @> array['_나']
    or not (public.concert_bigrams('가%_나') @> array['가%','_나'])
 then raise exception 'two-character literal search changed'; end if;
end $$;
rollback;
