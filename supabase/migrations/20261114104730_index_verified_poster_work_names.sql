-- Spellings printed on the reviewed concert program; scope remains on the program item.
insert into public.work_aliases (work_id, alias, locale, source)
select w.id, v.alias, 'ko', 'http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF303044_202610120513254400.png'
from (values
  ('bizet-carmen', 'Georges Bizet', '카르멘'),
  ('hisaishi-a-town-with-an-ocean-view', 'Joe Hisaishi', '바다가 보이는 마을'),
  ('monti-czardas', 'Vittorio Monti', '차르다시')
) v(slug, composer, alias)
join public.works w on w.slug = v.slug
join public.composers c on c.id = w.composer_id and c.name = v.composer
on conflict (work_id, alias) do nothing;

