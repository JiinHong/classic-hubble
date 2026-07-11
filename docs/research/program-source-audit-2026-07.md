# Classical Concert Program Source Audit

조사일: 2026-07-11

후속 분석: [LLM·OCR 없는 결정론적 파이썬 수집 가능 비율](deterministic-collection-coverage-2026-07.md)

## 결론

KOPIS만으로는 곡목 중심 서비스를 만들 수 없지만, 실제 예매처와 공연장 원문에는 생각보다 많은 프로그램 정보가 있다. 다만 한 가지 수집 방식으로 전부 가져올 수는 없다.

- NOL의 신형 공연 상세는 프로그램을 선택 가능한 HTML 텍스트로 제공하는 비율이 높다.
- 예술의전당은 기본 화면에서 보이지 않더라도 `작품소개` 탭을 열면 HTML 텍스트가 나오는 경우가 많다.
- 세종문화회관은 HTML, 프로그램 이미지, 이미지의 전체 `alt` 텍스트가 혼재한다.
- 롯데콘서트홀은 KBS교향악단·서울시향 공연은 HTML인 반면, 대관공연과 자체 기획공연에도 긴 이미지 한 장만 쓰는 사례가 많다.
- 금호아트홀은 조사한 기획·대관 표본 모두 프로그램이 HTML 문단이었다.
- 부천아트센터는 HTML과 이미지가 섞여 있다.
- 아트센터인천은 긴 상세 이미지 의존도가 높고, 한 이미지에 여러 날짜의 프로그램을 함께 넣기도 한다.
- 일부 공연은 곡을 당일 공개하거나, 티켓 오픈 시점에 프로그램이 미정이어서 어떤 수집 기술을 써도 곡목이 존재하지 않는다.

따라서 장기적으로 가능한 해법은 `KOPIS + 사이트별 HTML 어댑터 + 이미지/PDF 추출 + 변경 감지 + 검수`의 다중 소스 구조다. KOPIS 단독으로 모든 곡목을 제공하는 것은 불가능하고, 여러 사이트를 수집해도 100% 보장은 불가능하다.

## 조사 방법

- 2026년 공연을 중심으로 12개 계열 사이트의 공연 상세·티켓 오픈 공지 48건을 목적 표집했다.
- 일반 사례뿐 아니라 프로그램 변경, 판매 종료, 이미지 전용, 프로그램 미정, 시리즈 묶음 페이지를 의도적으로 포함했다.
- 17건은 실제 브라우저 DOM까지 열어 탭 전환과 원본 HTML을 확인했다.
- 8개 공연의 상세 이미지 10장을 원본으로 내려받아 사람이 읽는 방식으로 직접 확인했다.
- 아래 수치는 시장 전체의 통계가 아니라 수집 파이프라인 설계를 위한 엔지니어링 표본이다.

### 표본의 주 표시 형태

| 주 표시 형태 | 건수 | 의미 |
|---|---:|---|
| 완전한 HTML 프로그램 | 31 | 곡목이 선택 가능한 텍스트로 노출됨 |
| 부분 HTML 프로그램 | 2 | 일부 곡 또는 `외` 표현만 제공 |
| PDF 중심 | 1 | 프로그램북 다운로드가 주된 상세 자료 |
| 이미지 + 완전한 alt | 3 | 화면은 이미지지만 alt에 곡목 전체가 있음 |
| 이미지 전용, alt 없음 | 7 | 이미지 인식 또는 OCR이 필요함 |
| 이미지 전용, 곡목 자체 없음 | 1 | 이미지를 읽어도 출연진·안내만 있고 곡목이 없음 |
| 미정·당일 공개·아직 미게시 | 3 | 원문 자체에 확정 곡목이 없음 |
| **합계** | **48** | 목적 표집 표본 |

이 표본에서는 37건을 HTML·alt·PDF만으로 읽을 수 있었고, 7건은 이미지 인식이 있어야 프로그램을 얻을 수 있었다. 나머지 4건은 상세 이미지를 읽어도 곡목이 없거나, 프로그램이 실제로 미정·당일 공개 상태였다. 이 수치는 서비스 전체의 예상 커버리지가 아니라 수집 계층을 설계하기 위한 관찰값이다.

## 사이트별 경향

### NOL 티켓

신형 `tickets.interpark.com/play/performance/...` 페이지는 포스터와 별도로 `프로그램` 아코디언을 만들고, 작곡가와 곡명을 DOM 텍스트로 렌더링한다. 코리안챔버오케스트라 신년음악회 페이지에서 슈만, 타유페르, 라흐마니노프, 코다이 곡목이 이미지가 아닌 텍스트임을 직접 확인했다.

`오픈예정` 공지는 정식 상세와 다른 생명주기 화면이다. 공지의 `공연소개` 안에 프로그램을 텍스트로 적는 경우가 많지만, 축제 전체 설명만 있고 회차별 곡목이 없는 경우도 있다. 판매 종료된 과거 페이지는 프로그램 영역이 사라지거나 축약될 수 있다.

주요 예외:

- 크리스티안 짐머만 리사이틀은 24개의 프렐류드를 연주자가 공연 당일 선택·공개한다고 명시한다. 이 경우는 누락이 아니라 실제 미공개다.
- 박혜상 리사이틀은 일부 곡과 `외`만 적혀 있어 확정 목록으로 사용하면 안 된다.
- 클래식 레볼루션 티켓 오픈 공지는 전체 축제 일정은 있지만 개별 회차 프로그램이 아직 없다.
- 같은 공연도 오픈 공지, 정식 상세, 판매 종료 페이지의 정보량이 다르다.

대표 원문:

- [코리안챔버오케스트라 2026 신년음악회](https://tickets.interpark.com/play/performance/%EC%BD%94%EB%A6%AC%EC%95%88%EC%B1%94%EB%B2%84%EC%98%A4%EC%BC%80%EC%8A%A4%ED%8A%B8%EB%9D%BC-2026-%EC%8B%A0-gMzkDQWyaR1CKqOv)
- [서울솔로이스츠하모니카오케스트라](https://tickets.interpark.com/play/performance/%EC%84%9C%EC%9A%B8%EC%86%94%EB%A1%9C%EC%9D%B4%EC%8A%A4%EC%B8%A0%ED%95%98%EB%AA%A8%EB%8B%88%EC%B9%B4%EC%98%A4%EC%BC%80%EC%8A%A4%ED%8A%B8%EB%9D%BC-gQRyzeJxptWhJF7o)
- [리오라 콰르텟](https://tickets.interpark.com/play/performance/%EC%84%9C%EC%9A%B8-%EC%88%98%EC%84%9C-%EC%82%AC%EB%9E%91%EC%9D%98-%EA%B2%B0-%EB%A6%AC%EC%98%A4%EB%9D%BC-%EC%BD%B0-gbshJ5Z50RMs0RQc)
- [박지영 바이올린 독주회](https://tickets.interpark.com/play/performance/%EB%B0%95%EC%A7%80%EC%98%81-%EB%B0%94%EC%9D%B4%EC%98%AC%EB%A6%B0-%EB%8F%85%EC%A3%BC%ED%9A%8C-gBu6hDEGRU2FiyfY)
- [크리스티안 짐머만 리사이틀](https://tickets.interpark.com/play/performance/%ED%81%AC%EB%A6%AC%EC%8A%A4%ED%8B%B0%EC%95%88-%EC%A7%90%EB%A8%B8%EB%A7%8C-%ED%94%BC%EC%95%84%EB%85%B8-%EB%A6%AC%EC%82%AC%EC%9D%B4-gHJlI9ktACNp0bRH)
- [소프라노 박혜상 티켓 오픈 공지](https://tickets.interpark.com/contents/notice/detail/13433)
- [디토 오케스트라 앙상블 티켓 오픈 공지](https://tickets.interpark.com/contents/notice/detail/12651)
- [클래식 레볼루션 2026 티켓 오픈 공지](https://tickets.interpark.com/contents/notice/detail/14081)
- [오베르뉴론알프 국립 오케스트라 티켓 오픈 공지](https://tickets.interpark.com/contents/notice/detail/12564)

### 예술의전당

기간, 시간, 장소, 가격, 주최, 문의는 구조화되어 있고, 프로그램과 프로필은 `작품소개` 탭에 들어간다. 단순 HTTP 응답이나 기본 탭만 읽으면 프로그램이 없는 것으로 오판할 수 있다.

직접 확인한 박노을 첼로 독주회는 기본 `알립니다` 탭에는 곡목이 없었지만, `작품소개`를 누르면 바흐 무반주 모음곡 1번, 베토벤 첼로 소나타 5번, 라흐마니노프 첼로 소나타가 모두 HTML 문단으로 나타났다.

주요 예외:

- 프로그램북 PDF를 별도로 내려받을 수 있는 공연이 있다.
- 공지 탭에서 변경 전·변경 후 프로그램을 함께 제공하는 경우가 있어 최신본 선택이 필요하다.
- 시리즈 페이지는 날짜별 프로그램과 `추후 오픈 예정` 회차가 한 페이지에 섞일 수 있다.
- 검색엔진에 곡목이 안 잡혀도 동적 탭 안에는 텍스트가 있을 수 있다.

대표 원문:

- [클래시컬 브릿지 챔버 콘서트 I: 프로그램 변경](https://www.sac.or.kr/site/main/show/show_view?SN=76626)
- [박노을 첼로 독주회: 숨은 작품소개 탭](https://www.sac.or.kr/site/main/show/show_view?SN=76680)
- [김지수 피아노 독주회: HTML + 프로그램북](https://www.sac.or.kr/site/main/show/show_view?SN=81002)
- [드오 콘서트: 창작곡 목록](https://www.sac.or.kr/site/main/show/show_view?SN=78573)
- [히사이시 조 영화음악 콘서트](https://www.sac.or.kr/site/main/show/show_view?SN=77690)
- [박혜상 한국가곡 연대기](https://www.sac.or.kr/site/main/show/show_view?SN=77580)
- [서울시향 유럽 투어 프리뷰](https://www.sac.or.kr/site/main/show/show_view?SN=74737)
- [베토벤 페노메논 II](https://www.sac.or.kr/site/main/show/show_view?SN=80120)
- [예술의전당 토요콘서트](https://www.sac.or.kr/site/main/show/show_view?SN=80191)
- [서울시향 협연자·프로그램 변경](https://www.sac.or.kr/site/main/show/show_view?SN=74740)

### 세종문화회관

공연일자, 장소, 시간, 러닝타임, 관람연령, 가격, 문의는 표 형태로 안정적으로 노출된다. 상세 본문은 외부 기획사가 올리는 HTML과 이미지가 섞인다.

이미지 처리도 일관되지 않다.

- 강금화 피아노 독주회는 곡목이 이미지에 있지만 `alt`에도 바흐와 힌데미트 프로그램 전체가 복제돼 있다. OCR 없이 alt만으로 수집할 수 있다.
- 김승직 리사이틀은 3개의 긴 이미지가 있고 모두 유용한 alt가 없다. 두 번째 이미지 안에 베토벤 가곡 4곡, 슈베르트 가곡 9곡, 슈만 `시인의 사랑 Op.48`이 들어 있어 이미지 인식이 필수다.
- 청소년 클래식 페스티벌과 Ensemble VoRA 페이지도 프로그램 이미지의 alt가 곡목 전체를 포함한다.

세종 페이지가 음악 공연을 `전시일정`으로 표시하는 사례도 있어 화면 제목이나 분류 문자열만 신뢰하면 안 된다.

대표 원문:

- [아크 피아노 콰르텟](https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?menuNo=200320&performIdx=37199)
- [정음피아노앙상블](https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?menuNo=200320&performIdx=37224)
- [강금화 피아노 독주회](https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?menuNo=200320&performIdx=36929)
- [김승직 솔로 리사이틀](https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?menuNo=200320&performIdx=37266)
- [임호열 피아노 독주회](https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?menuNo=200320&performIdx=37235)
- [서울스프링실내악축제](https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?menuNo=200320&performIdx=36947)
- [베르누스 무지카](https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?menuNo=200320&performIdx=37247)
- [청소년을 위한 클래식 페스티벌](https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?menuNo=200320&performIdx=37353)
- [Ensemble VoRA](https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?menuNo=200320&performIdx=37394)
- [음악예술학회 정기연주회](https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?menuNo=200320&performIdx=37233)

### 롯데콘서트홀

기본 메타데이터와 예매처, 잔여석, 가격은 구조화되어 있다. `공연소개`는 편집기 HTML이며, 곡목을 텍스트로 넣기도 하고 긴 이미지 한 장만 넣기도 한다.

HTML 사례:

- 차이코프스키 스페셜은 바이올린 협주곡과 교향곡 4번을 HTML 문단으로 제공한다.
- 브루스 리우와 KBS교향악단 공연, 서울시향 모차르트 레퀴엠은 출연진과 프로그램을 HTML로 제공한다.

이미지 사례:

- KSC 신인아티스트 콘서트는 9개의 협주곡 악장과 연주자가 이미지에만 있다.
- Spring FESTA는 1부 클래식과 2부 영화음악 메들리가 이미지에만 있다.
- 롯데 자체 기획 조성진 리사이틀도 바흐, 쇤베르크, 슈만, 쇼팽 프로그램을 이미지에만 넣었다.
- 이데일리 신년음악회는 긴 이미지가 있지만 좌석·출연진·예매안내만 있고 곡목은 없다.

이미지 `src`가 `http://`로 기록되어 브라우저에서 혼합 콘텐츠로 차단되는 페이지도 있었다. 백엔드에서는 동일 경로를 `https://`로 받아올 수 있었지만, URL 정규화와 실패 처리가 필요하다.

대표 원문:

- [차이코프스키 스페셜](https://www.lotteconcerthall.com/product/ko/performance/260963)
- [이데일리 신년음악회](https://www.lotteconcerthall.com/product/ko/performance/260938)
- [KSC 신인아티스트 콘서트](https://www.lotteconcerthall.com/product/ko/performance/261035)
- [Spring FESTA](https://www.lotteconcerthall.com/product/ko/performance/260974)
- [조성진 인 하우스 리사이틀](https://www.lotteconcerthall.com/product/ko/performance/261058)
- [브루스 리우 x 에스트라다](https://www.lotteconcerthall.com/product/ko/performance/261049)
- [서울시향 모차르트 레퀴엠](https://www.lotteconcerthall.com/product/performance/260891)

### 금호아트홀 연세

조사한 금호영아티스트 기획공연과 외부 대관공연 모두 `프로그램소개` 아래에 작곡가, 작품, 악장을 HTML 문단으로 제공했다. 이미지도 있으나 곡목의 유일한 원본은 아니었다.

구형 URL과 별도 포트(`:448`)를 사용하고 일부 대관공연 예매는 NOL로 연결되므로 연결 안정성과 리디렉션 처리가 필요하다.

- [박지율 비올라 독주회](https://www.kumhoarthall.com:448/designer/skin/01/detail.html?p_idx=25401&s_idx=11&vwY=2026&vwM=07&se_idx=283)
- [FOR THE PIANO 정기연주회](https://www.kumhoarthall.com:448/designer/skin/01/detail.html?p_idx=25596&s_idx=11&vwY=2026&vwM=07&se_idx=0)

### 부천아트센터

핵심 메타데이터는 구조화되어 있다. 상세정보는 공연별로 HTML 또는 이미지다.

- 오케스트라 syncope 공연은 제목 아래에 차이콥스키 피아노 협주곡 1번과 교향곡 4번이 짧게 노출되지만, 정식 프로그램과 소개는 alt 없는 긴 이미지에 있다.
- 부천필 한불수교 공연은 박성아, 라벨, 드뷔시 프로그램을 HTML로 제공한다.
- 한컴오피스에서 붙여 넣은 대용량 JSON 주석이 HTML에 포함된 페이지가 있어, 전체 HTML 텍스트를 무작정 파싱하면 잡음이 커진다. 실제 보이는 편집기 콘텐츠만 추출해야 한다.

- [오케스트라 syncope 차이코프스키 시리즈](https://www.bac.or.kr/product/performance/253387)
- [부천필 한불수교 140주년](https://www.bac.or.kr/product/ko/performance/253370)

### 아트센터인천

상세 본문이 `upload/ckeditor`의 초장문 이미지인 사례가 많고 alt가 비어 있다.

`조조 클래식 III` 상세 이미지는 한 공연만 설명하는 것이 아니라 3월, 5월, 8월, 11월 네 회차의 출연자와 프로그램을 함께 담는다. 이미지 인식 후에도 현재 상세 페이지의 날짜와 맞는 블록을 다시 분리해야 한다.

장-기엔 케라스 공연처럼 제목이 이미 `바흐: 무반주 첼로 모음곡 전곡`을 알려 주는 경우도 있지만, 제목 힌트와 정식 프로그램을 같은 신뢰도로 저장하면 안 된다.

- [조조 클래식 III](https://www.aci.or.kr/main/show/view.do?SHOW_IDX=14138&menuNo=010000&month=8&subMenuNo=010100&viewType=month&year=2026)
- [장-기엔 케라스 첼로 리사이틀](https://www.aci.or.kr/main/show/view.do?SHOW_IDX=14126&menuNo=010000&sch_kind=1&show_type=all&subMenuNo=010100&viewType=img)
- [바흐 요한수난곡](https://www.aci.or.kr/main/show/view.do?SHOW_IDX=13575&menuNo=010000&show_type=all&subMenuNo=010100&viewType=img)

### LG아트센터·기타 지역 공연장·예매처

LG아트센터의 홍진호 `첼로의 숲`은 프로그램을 HTML로 제공했다. 기획 시즌 전체 정보는 별도 시즌 브로셔 PDF에도 있다. 2026년 LG SIGNATURE 홀은 클래식 표본 자체가 다른 전문 콘서트홀보다 적었다.

대구콘서트하우스, 고양아람누리, 성남아트센터의 확인 표본은 프로그램이 HTML 텍스트였다. 다만 이 세 표본만으로 각 사이트의 모든 대관공연이 동일하다고 일반화할 수는 없다.

YES24의 후지타 마오 티켓 오픈 공지는 공연·출연자 정보는 텍스트지만 프로그램이 아직 없었다. 멜론티켓은 `작품설명`을 이미지로만 올리는 패턴이 확인돼, 공연장 원문을 찾지 못할 때의 보조 소스로는 이미지 수집이 필요하다.

- [LG아트센터 홍진호 첼로의 숲](https://www.lgart.com/product/performance/252869)
- [대구콘서트하우스 표본](https://www.daeguconcerthouse.or.kr/eng/index.do?category=&con_id=SC_00000000000000002762&menu_id=00000192&menu_link=%2Ffront%2Fschedule%2FconcertScheduleDetailView.do&occurrence=2026-03-18&pageIndex=2)
- [고양아람누리 표본](https://www.artgy.or.kr/PF/PF0201V.aspx?showid=0000007787)
- [성남아트센터 표본](https://www.snart.or.kr/main/prex/prefer/view.do?prfr_exhb_sn=100143)
- [YES24 후지타 마오 티켓 오픈 공지](https://m.ticket.yes24.com/Notice/Detail.aspx?bid=17896&order=1&type=1)

## 직접 확인한 이미지 10장

| 공연 | 파일 | 이미지에서 확인한 내용 | alt 상태 |
|---|---|---|---|
| 세종 강금화 독주회 | [program](program-source-audit-assets/sejong-kang-geumhwa-program.png) | 바흐 파르티타 1·3·4번과 힌데미트 `Ludus Tonalis` 발췌 | 곡목 전체 있음 |
| 세종 김승직 리사이틀 | [좌석·안내](program-source-audit-assets/sejong-kim-seungjik-seating.png) | 좌석도와 관람안내, 곡목 없음 | 비어 있음 |
| 세종 김승직 리사이틀 | [프로그램](program-source-audit-assets/sejong-kim-seungjik-program.png) | 베토벤 가곡 4곡, 슈베르트 가곡 9곡, 슈만 `시인의 사랑 Op.48` | 비어 있음 |
| 세종 김승직 리사이틀 | [프로필](program-source-audit-assets/sejong-kim-seungjik-profiles.png) | 테너·피아니스트 프로필, 곡목 없음 | 비어 있음 |
| 롯데 이데일리 신년음악회 | [상세](program-source-audit-assets/lotte-edaily-2026-detail.jpg) | 출연진, 좌석, 예매안내만 있고 레퍼토리 없음 | 비어 있음 |
| 롯데 KSC 신인아티스트 | [상세](program-source-audit-assets/lotte-ksc-2026-detail.jpg) | 모차르트·베토벤·슈타미츠·차이콥스키·시벨리우스 협주곡 악장 9개 | 비어 있음 |
| 롯데 Spring FESTA | [상세](program-source-audit-assets/lotte-spring-festa-detail.jpeg) | 1부 클래식 5곡, 2부 영화음악·뮤지컬 메들리 | 비어 있음 |
| 롯데 조성진 리사이틀 | [상세](program-source-audit-assets/lotte-seongjin-recital-detail.jpg) | 바흐 파르티타 1번, 쇤베르크 Op.25, 슈만 Op.26, 쇼팽 14개 왈츠 | 비어 있음 |
| 부천 syncope | [상세](program-source-audit-assets/bac-syncope-detail.png) | 차이콥스키 피아노 협주곡 1번과 교향곡 4번 | 비어 있음 |
| 아트센터인천 조조 클래식 | [상세](program-source-audit-assets/aci-jojo-series-detail.jpg) | 네 회차의 독주자와 서로 다른 프로그램을 한 이미지에 묶음 | 비어 있음 |

## 반복적으로 나타난 예외 케이스

1. **실제 미정**: 연주자가 당일 곡을 선택하거나 프로그램이 추후 공개된다.
2. **부분 공개**: 대표곡 몇 개 뒤에 `외`, `등`이 붙는다.
3. **제목 힌트만 존재**: 제목에 `메시아`, `바흐 무반주 전곡`이 있지만 상세 목록은 없다.
4. **동적 탭**: 기본 HTML 화면에는 없고 탭을 눌러야 서버가 렌더링한다.
5. **이미지 alt 불일치**: 전체 곡목이 있는 alt, 일반적인 `공연 이미지`, 빈 alt가 같은 사이트 안에 공존한다.
6. **다중 이미지 역할**: 첫 이미지는 좌석, 둘째는 프로그램, 셋째는 프로필일 수 있다.
7. **시리즈 묶음 이미지**: 한 이미지에 여러 날짜의 프로그램이 들어 있어 회차별 분리가 필요하다.
8. **PDF 병행 또는 PDF 중심**: 상세 페이지와 프로그램북의 최신성이 다를 수 있다.
9. **변경 전·후 동시 노출**: 공지에 구 프로그램과 새 프로그램이 함께 남는다.
10. **판매 생명주기 차이**: 티켓 오픈 공지, 정식 판매 페이지, 판매 종료 페이지의 내용이 다르다.
11. **혼합 콘텐츠**: 이미지 URL이 HTTP라 브라우저에서 안 보이지만 서버에서는 HTTPS 경로로 받을 수 있다.
12. **편집기 잡음**: 한컴 JSON, 빈 문단, 서식용 태그가 곡목 사이에 대량 포함된다.
13. **중복 언어**: 한글·영문 곡명이 연속으로 있어 같은 곡을 두 건으로 만들기 쉽다.
14. **분류 오류**: 클래식 공연이 `전시일정`으로 표시되는 등 화면 분류가 틀릴 수 있다.
15. **원문에도 없음**: 이미지를 완전히 읽어도 좌석·출연진만 있고 곡목이 없는 공연이 있다.

## 수집 파이프라인에 주는 결론

### 운영 안정성 평가

| 소스 | 메타데이터 안정성 | 프로그램 안정성 | 운영상 주의점 |
|---|---|---|---|
| KOPIS Open API | 높음 | 낮음 | 공식 API이지만 곡목 필드와 원문 완전성이 부족함 |
| NOL 신형 상세 | 중간 | 중간 이상 | 프로그램 텍스트는 좋지만 SPA 구조와 판매 생명주기에 따라 페이지가 달라짐 |
| 예술의전당 | 높음 | 중간 이상 | 작품소개 탭 전환과 변경 공지 처리가 필요함 |
| 세종문화회관 | 높음 | 중간 | HTML·이미지·alt 품질이 공연마다 다름 |
| 롯데콘서트홀 | 높음 | 중간 이하 | 이미지 전용 비중과 HTTP 이미지 URL 예외가 큼 |
| 금호아트홀 | 중간 | 중간 이상 | 프로그램 텍스트는 양호하지만 구형 URL·포트·리디렉션 의존성이 있음 |
| 부천아트센터 | 높음 | 중간 | 편집기 HTML과 이미지가 혼재하고 한컴 주석 잡음이 큼 |
| 아트센터인천 | 높음 | 낮음~중간 | 초장문 이미지와 다중 회차 이미지 때문에 OCR 뒤 분할이 필요함 |
| OCR·비전 결과 | 해당 없음 | 중간 | 원본 품질과 레이아웃에 따라 달라지므로 신뢰도와 검수가 필수임 |

여기서 `안정성`은 공개 페이지를 기술적으로 읽는 관점의 평가다. 운영 전에는 각 사이트의 이용약관·robots 정책과 허용 범위를 별도로 확인하고, 낮은 호출 빈도, 캐시, 조건부 요청, 원본 출처 표기를 적용해야 한다. 공식 API가 아닌 HTML 수집은 사이트 개편에 따라 깨질 수 있으므로 어댑터별 모니터링과 실패율 알림이 필요하다.

### 소스 우선순위

1. 공연장 또는 연주단체 공식 페이지의 최신 프로그램
2. 주최·기획사 공식 페이지
3. NOL·YES24·티켓링크·멜론 등 예매처 상세
4. KOPIS의 공연·시설 메타데이터
5. 제목에서 얻은 힌트는 확정 프로그램이 아닌 별도 후보로만 저장

KOPIS는 공연 식별자, 기간, 장소, 포스터, 출연자, 예매 링크의 뼈대로 적합하다. 곡목의 최종 원본으로는 적합하지 않다.

### 추출 단계

1. KOPIS 레코드로 공연 후보를 만든다.
2. 공식 공연장·주최사·예매처 URL을 연결한다.
3. 페이지의 원본 HTML, 조회 시각, 해시를 보관한다.
4. 사이트별 어댑터로 메타데이터와 프로그램 컨테이너만 읽는다.
5. HTML 텍스트가 없으면 이미지 alt를 확인한다.
6. PDF가 있으면 텍스트 레이어를 먼저 읽고 스캔 PDF만 OCR한다.
7. 이미지 전용이면 프로그램 이미지와 좌석·프로필 이미지를 분류한 뒤 OCR/비전 추출한다.
8. 날짜·회차·연주자별로 프로그램을 분리한다.
9. 변경 공지와 새 해시를 비교해 최신 버전을 선택한다.
10. 작품 alias 정규화 후 낮은 신뢰도의 결과만 검수 큐로 보낸다.

### 반드시 별도 저장할 상태

- `confirmed`: 공식 원문에 완전한 목록이 있음
- `partial`: `외`, `등`, 일부 악장 등 불완전 목록
- `announced_later`: 주최사가 추후 공개한다고 명시
- `selected_on_day`: 공연 당일 선택·공개
- `not_published`: 상세를 확인했으나 곡목 없음
- `source_unavailable`: 페이지 삭제·차단·접속 실패
- `changed`: 이전 프로그램에서 변경됨

`not_published`와 `source_unavailable`을 같은 null로 저장하면 데이터 품질을 판단할 수 없다.

## 현재 제품 범위에 대한 권고

KOPIS 전용 MVP에서는 다음 기능을 안전하게 제공할 수 있다.

- 공연명, 기간, 공연장, 출연자, 포스터, 상태, 예매 링크
- 공연장·기간·출연자 검색과 필터
- 관심 공연 저장과 일정 알림
- 프로그램 상태를 `아직 제공되지 않음`으로 표시

곡명 검색, 작품별 알림, 프로그램 기반 추천은 공식 상세 페이지 수집이 시작된 공연에만 제한적으로 열어야 한다. 제목에 작품명이 있어도 자동으로 확정 프로그램으로 승격하지 않는 것이 맞다.
