insert into public.composers (name, name_ko, period)
select *
from (
  values
    ('Ludwig van Beethoven', '루트비히 판 베토벤', 'Classical / Romantic'),
    ('Sergei Rachmaninoff', '세르게이 라흐마니노프', 'Late Romantic'),
    ('Antonin Dvorak', '안토닌 드보르자크', 'Romantic'),
    ('Johannes Brahms', '요하네스 브람스', 'Romantic')
) as seed(name, name_ko, period)
where not exists (
  select 1 from public.composers where composers.name = seed.name
);

insert into public.venues (kopis_facility_id, name, city, booking_channels)
select *
from (
  values
    ('classic-hubble-lotte', '롯데콘서트홀', '서울', array['NOL', '공연장']),
    ('classic-hubble-sac-ibk', '예술의전당 IBK챔버홀', '서울', array['SAC', 'NOL']),
    ('classic-hubble-sejong-grand', '세종문화회관 세종대극장', '서울', array['세종문화회관', 'NOL']),
    ('classic-hubble-bucheon', '부천아트센터 콘서트홀', '부천', array['공연장']),
    ('classic-hubble-incheon', '아트센터인천 콘서트홀', '인천', array['공연장', 'NOL'])
) as seed(kopis_facility_id, name, city, booking_channels)
where not exists (
  select 1 from public.venues where venues.name = seed.name
);

insert into public.works (
  composer_id,
  slug,
  title,
  title_ko,
  catalogue,
  instrumentation,
  popularity_rank
)
select composers.id, seed.slug, seed.title, seed.title_ko, seed.catalogue, seed.instrumentation, seed.popularity_rank
from (
  values
    (
      'Sergei Rachmaninoff',
      'rachmaninoff-piano-concerto-2',
      'Piano Concerto No. 2 in C minor',
      '피아노 협주곡 2번',
      'Op. 18',
      'Piano and Orchestra',
      1
    ),
    (
      'Ludwig van Beethoven',
      'beethoven-symphony-5',
      'Symphony No. 5 in C minor',
      '교향곡 5번',
      'Op. 67',
      'Orchestra',
      2
    ),
    (
      'Antonin Dvorak',
      'dvorak-symphony-9',
      'Symphony No. 9 in E minor',
      '교향곡 9번 신세계로부터',
      'Op. 95',
      'Orchestra',
      3
    ),
    (
      'Johannes Brahms',
      'brahms-violin-concerto',
      'Violin Concerto in D major',
      '바이올린 협주곡',
      'Op. 77',
      'Violin and Orchestra',
      4
    )
) as seed(composer_name, slug, title, title_ko, catalogue, instrumentation, popularity_rank)
join public.composers on composers.name = seed.composer_name
on conflict (slug) do update set
  composer_id = excluded.composer_id,
  title = excluded.title,
  title_ko = excluded.title_ko,
  catalogue = excluded.catalogue,
  instrumentation = excluded.instrumentation,
  popularity_rank = excluded.popularity_rank,
  updated_at = now();

insert into public.work_aliases (work_id, alias, locale, source)
select works.id, alias_seed.alias, alias_seed.locale, 'curated'
from public.works
join (
  values
    ('rachmaninoff-piano-concerto-2', '라흐마니노프 피아노 협주곡 2번', 'ko'),
    ('rachmaninoff-piano-concerto-2', '라흐 피협 2번', 'ko'),
    ('rachmaninoff-piano-concerto-2', '라피협 2', 'ko'),
    ('rachmaninoff-piano-concerto-2', 'Rachmaninoff Piano Concerto No. 2', 'en'),
    ('rachmaninoff-piano-concerto-2', 'Piano Concerto No.2 Op.18', 'en'),
    ('beethoven-symphony-5', '운명', 'ko'),
    ('beethoven-symphony-5', '베토벤 교향곡 5번', 'ko'),
    ('beethoven-symphony-5', 'Beethoven Symphony No. 5', 'en'),
    ('beethoven-symphony-5', 'Symphony No.5 in C minor', 'en'),
    ('beethoven-symphony-5', 'Fate Symphony', 'en'),
    ('dvorak-symphony-9', '신세계', 'ko'),
    ('dvorak-symphony-9', '드보르자크 신세계', 'ko'),
    ('dvorak-symphony-9', '드보르자크 교향곡 9번', 'ko'),
    ('dvorak-symphony-9', 'From the New World', 'en'),
    ('dvorak-symphony-9', 'Dvorak Symphony No. 9', 'en'),
    ('brahms-violin-concerto', '브람스 바이올린 협주곡', 'ko'),
    ('brahms-violin-concerto', '브바협', 'ko'),
    ('brahms-violin-concerto', 'Brahms Violin Concerto', 'en'),
    ('brahms-violin-concerto', 'Violin Concerto Op.77', 'en')
) as alias_seed(work_slug, alias, locale) on alias_seed.work_slug = works.slug
on conflict (work_id, alias) do nothing;

insert into public.performances (
  kopis_performance_id,
  venue_id,
  title,
  starts_at,
  status,
  artists,
  price_range,
  booking_url,
  poster_url,
  source_label,
  raw_payload
)
select
  seed.kopis_performance_id,
  venues.id,
  seed.title,
  seed.starts_at::timestamptz,
  seed.status::performance_status,
  seed.artists,
  seed.price_range,
  seed.booking_url,
  seed.poster_url,
  seed.source_label,
  jsonb_build_object('seed', 'classic_hubble_mvp', 'public_id', seed.kopis_performance_id)
from (
  values
    (
      'perf-lotte-rach-2',
      '롯데콘서트홀',
      '김정원과 친구들 - 저먼 로맨틱스',
      '2026-07-31 19:30:00+09',
      'open',
      array['김정원', 'KBS교향악단'],
      'R 90,000 / S 70,000 / A 50,000',
      'https://tickets.interpark.com/',
      'https://ticketimage.interpark.com/Play/image/large/26/26009683_p.gif',
      '공연장 상세 이미지 OCR + 관리자 검수'
    ),
    (
      'perf-sac-gala',
      '예술의전당 IBK챔버홀',
      '2026 서초국제예술단 피아노 갈라 콘서트',
      '2026-08-29 17:00:00+09',
      'upcoming',
      array['원재연', '김수연'],
      '전석 40,000',
      'https://www.sac.or.kr/',
      'https://ticketimage.interpark.com/Play/image/large/26/26009095_p.gif',
      'KOPIS + 예술의전당 상세페이지'
    ),
    (
      'perf-sejong-beethoven',
      '세종문화회관 세종대극장',
      '서울시향 베토벤 사이클',
      '2026-09-12 19:30:00+09',
      'open',
      array['서울시립교향악단', '수산나 멜키'],
      '50,000 - 120,000',
      'https://www.sejongpac.or.kr/',
      'https://ticketimage.interpark.com/Play/image/large/26/26006680_p.gif',
      '공식 프로그램 확인'
    ),
    (
      'perf-bucheon-dvorak',
      '부천아트센터 콘서트홀',
      '부천필하모닉 정기연주회 - ENIGMA',
      '2026-10-16 19:30:00+09',
      'open',
      array['부천필하모닉오케스트라'],
      '30,000 - 70,000',
      'https://www.bac.or.kr/',
      'https://www.bac.or.kr/images/snsShareImage1.png',
      '부천아트센터 상세페이지'
    ),
    (
      'perf-incheon-brahms',
      '아트센터인천 콘서트홀',
      '아트센터인천 마스터즈 시리즈',
      '2026-11-08 17:00:00+09',
      'open',
      array['드레스덴 필하모닉', '제임스 에네스'],
      '40,000 - 110,000',
      'https://www.aci.or.kr/',
      'https://ticketimage.interpark.com/Play/image/large/26/26005009_p.gif',
      'NOL 예매 정보 + 공연장 페이지'
    )
) as seed(
  kopis_performance_id,
  venue_name,
  title,
  starts_at,
  status,
  artists,
  price_range,
  booking_url,
  poster_url,
  source_label
)
join public.venues on venues.name = seed.venue_name
on conflict (kopis_performance_id) do update set
  venue_id = excluded.venue_id,
  title = excluded.title,
  starts_at = excluded.starts_at,
  status = excluded.status,
  artists = excluded.artists,
  price_range = excluded.price_range,
  booking_url = excluded.booking_url,
  poster_url = excluded.poster_url,
  source_label = excluded.source_label,
  raw_payload = excluded.raw_payload,
  updated_at = now();

delete from public.program_items
where performance_id in (
  select id
  from public.performances
  where kopis_performance_id in (
    'perf-lotte-rach-2',
    'perf-sac-gala',
    'perf-sejong-beethoven',
    'perf-bucheon-dvorak',
    'perf-incheon-brahms'
  )
);

insert into public.program_items (
  performance_id,
  work_id,
  display_title,
  composer_name,
  source_type,
  confidence,
  position
)
select
  performances.id,
  works.id,
  seed.display_title,
  seed.composer_name,
  seed.source_type::program_source_type,
  seed.confidence,
  seed.position
from (
  values
    (
      'perf-lotte-rach-2',
      'rachmaninoff-piano-concerto-2',
      'Rachmaninoff Piano Concerto No. 2 in C minor, Op. 18',
      'Sergei Rachmaninoff',
      'verified',
      0.93,
      0
    ),
    (
      'perf-sac-gala',
      'rachmaninoff-piano-concerto-2',
      '라흐마니노프 피아노 협주곡 2번',
      '세르게이 라흐마니노프',
      'ocr',
      0.82,
      0
    ),
    (
      'perf-sejong-beethoven',
      'beethoven-symphony-5',
      '베토벤 교향곡 5번 다단조 Op. 67',
      '루트비히 판 베토벤',
      'official',
      0.99,
      0
    ),
    (
      'perf-bucheon-dvorak',
      'dvorak-symphony-9',
      'Dvorak Symphony No. 9 From the New World',
      'Antonin Dvorak',
      'estimated',
      0.74,
      0
    ),
    (
      'perf-incheon-brahms',
      'brahms-violin-concerto',
      'Brahms Violin Concerto in D major, Op. 77',
      'Johannes Brahms',
      'verified',
      0.91,
      0
    )
) as seed(
  performance_public_id,
  work_slug,
  display_title,
  composer_name,
  source_type,
  confidence,
  position
)
join public.performances on performances.kopis_performance_id = seed.performance_public_id
join public.works on works.slug = seed.work_slug;

delete from public.poster_review_items
where performance_id in (
  select id
  from public.performances
  where kopis_performance_id in ('perf-sac-gala', 'perf-bucheon-dvorak')
);

insert into public.poster_review_items (
  performance_id,
  image_url,
  extracted_text,
  suggested_work_id,
  confidence,
  state
)
select
  performances.id,
  seed.image_url,
  seed.extracted_text,
  works.id,
  seed.confidence,
  'needs_review'::review_state
from (
  values
    (
      'perf-sac-gala',
      'https://ticketimage.interpark.com/Play/image/large/26/26009095_p.gif',
      'Rachmaninoff Piano Concerto No. 2 in C minor Op.18',
      'rachmaninoff-piano-concerto-2',
      0.82
    ),
    (
      'perf-bucheon-dvorak',
      'https://www.bac.or.kr/images/snsShareImage1.png',
      'Dvorak Symphony No.9 New World',
      'dvorak-symphony-9',
      0.74
    )
) as seed(performance_public_id, image_url, extracted_text, suggested_work_slug, confidence)
join public.performances on performances.kopis_performance_id = seed.performance_public_id
join public.works on works.slug = seed.suggested_work_slug;
