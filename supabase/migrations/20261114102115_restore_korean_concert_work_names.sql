-- Korean program names for existing canonical works; do not alter concert links.
insert into public.work_aliases (work_id, alias, locale, source)
select w.id, v.alias, 'ko', v.source
from (values
  ('puccini-la-boheme', 'Giacomo Puccini', '라 보엠', 'https://www.nationalopera.org/cpage/show/showInfo/9229'),
  ('verdi-la-traviata', 'Giuseppe Verdi', '라 트라비아타', 'https://www.nationalopera.org/cpage/show/showInfo/9110'),
  ('verdi-rigoletto', 'Giuseppe Verdi', '리골레토', 'https://www.nationalopera.org/cpage/show/showInfo/9110'),
  ('wikidata-q1557135', 'Johannes Brahms', '자장가', 'https://www.sac.or.kr/site/main/show/show_view?SN=60223'),
  ('wikidata-q1723173', 'Anton Bruckner', '현악 오중주 바장조', 'https://classical.music.apple.com/kr/recording/anton-bruckner-1824-pp25-297610477'),
  ('wikidata-q1723173', 'Anton Bruckner', '현악 5중주 바장조', 'https://classical.music.apple.com/kr/recording/anton-bruckner-1824-pp25-297610477'),
  ('hisaishi-merry-go-round-of-life', 'Joe Hisaishi', '인생의 회전목마', 'https://www.sac.or.kr/site/main/show/show_view?SN=62289')
) v(slug, composer, alias, source)
join public.works w on w.slug = v.slug
join public.composers c on c.id = w.composer_id and c.name = v.composer
on conflict (work_id, alias) do nothing;

-- Summer already has its English title. Supply the missing artist lookup instead
-- of adding a concert-specific exception to search.
update public.composers c set name_ko = '히사이시 조'
where c.name = 'Joe Hisaishi' and c.name_ko is null
  and exists (select from public.works w where w.composer_id = c.id and w.slug = 'hisaishi-summer');
