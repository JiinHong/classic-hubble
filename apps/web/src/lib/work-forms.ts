import claims from "@/data/work-genre-claims.json";

// Match the form of the work, not a quoted source ("variations on ...") or
// an accompaniment. Listed from specific to broad within each evidence tier.
const rules = [
  ["prelude-fugue", "전주곡과 푸가", /prelude (and|et|und) fug|전주곡과 푸가/],
  ["variation", "변주곡", /\bvariations?\b|\bvariationen\b|변주곡/],
  ["overture", "서곡", /\b(overture|ouverture)s?\b|서곡/],
  ["impromptu", "즉흥곡", /\bimpromptus?\b|즉흥곡/],
  ["symphonic-poem", "교향시", /symphonic poem|tone poem|poeme symphonique|교향시/],
  ["concerto-grosso", "합주 협주곡", /concerto grosso|concerti grossi|합주 협주곡/],
  ["concertante", "협주 교향곡", /sinfonia concertante|symphonie concertante|협주 교향곡/],
  ["invention", "인벤션 · 신포니아", /\binventions?\b|\bbwv\s*(78[7-9]|79[0-9]|80[01])\b|인벤션/],
  ["symphony", "교향곡", /\b(symphon(y|ies|ie)|sinfonietta)\b|교향곡/],
  ["sinfonia", "신포니아", /\bsinfonia\b|신포니아/],
  ["partita", "파르티타", /\bpartit[ae]s?\b|파르티타/],
  ["canon", "카논", /\bcanons?\b|카논/],
  ["bagatelle", "바가텔", /\bbagatell(es?|en)\b|바가텔/],
  ["intermezzo", "인터메초", /\bintermezz[oi]\b|간주곡|인터메초/],
  ["cantabile", "칸타빌레", /^cantabile\b|^칸타빌레/],
  ["etude", "에튀드", /\betudes?\b|\bstud(y|ies)\b|에튀드|연습곡/],
  ["prelude", "프렐류드", /\bpreludes?\b|praeludium|프렐류드|전주곡/],
  ["scherzo", "스케르초", /\bscherz(o|i|os)\b|스케르초/],
  ["ballade", "발라드", /\bballades?\b|발라드/],
  ["nocturne", "녹턴", /\bnocturnes?\b|녹턴|야상곡/],
  ["waltz", "왈츠", /\b(waltz(es)?|vals(e|es)?|walzer)\b|왈츠/],
  ["mazurka", "마주르카", /\bmazur(ka|kas|ek)\b|마주르카|마주르크/],
  ["polonaise", "폴로네즈", /\bpolonaises?\b|폴로네즈|폴로네이즈/],
  ["rondo", "론도", /\brond(o|os|eau|eaux)\b|론도/],
  ["fantasia", "환상곡", /\b(fantas(y|ies|ia|ie)|fantaisie)s?\b|환상곡/],
  ["barcarolle", "뱃노래", /\bbarcarolles?\b|\bbarcaroles?\b|뱃노래/],
  ["lullaby", "자장가", /berceuse|lullaby|자장가/],
  ["rhapsody", "랩소디", /\br(h)?apsod(y|ie|ies|ia)\b|랩소디|광시곡/],
  ["string-quartet", "현악 사중주", /string quartets?|quartett?o? (a cordes|d.archi)|streichquartett|현악\s*(4|사)중주/],
  ["piano-quartet", "피아노 사중주", /piano quartets?|피아노\s*(4|사)중주/],
  ["piano-trio", "피아노 삼중주", /piano trios?|피아노\s*(3|삼)중주/],
  ["trio", "삼중주", /\btrios?\b|(3|삼)중주/],
  ["quartet", "사중주", /\bquartet(t|to|s)?\b|(4|사)중주/],
  ["quintet", "오중주", /\bquintet(t|to|s)?\b|(5|오)중주/],
  ["ensemble", "그 밖의 중주곡", /\b(duet|duo|sextet|septet|octet|nonet)s?\b|[육칠팔구이2-9]중주/],
  ["suite", "모음곡", /\bsuites?\b|모음곡/],
  ["serenade", "세레나데", /\bseren(ad(e|es|a)|ata)\b|세레나데/],
  ["divertimento", "디베르티멘토", /divertiment[oi]|디베르티멘토/],
  ["fugue", "푸가", /\bfug(ue|a|ues|he)\b|푸가/],
  ["toccata", "토카타", /\btoccatas?\b|토카타/],
  ["march", "행진곡", /\bmarch(es|e)?\b|행진곡/],
  ["polka", "폴카", /\bpolkas?\b|폴카/],
  ["minuet", "미뉴에트", /\b(minuets?|menuett?o?s?)\b|미뉴에트/],
  ["dance", "그 밖의 무곡", /\b(dances?|quadrilles?|ecossaises?|bourrees?|gavottes?|sarabandes?|pavanes?|tango|galop|bolero|tarantella|csardas|gigue|courante|fandango|sardana)\b|무곡|에코세즈/],
  ["requiem", "레퀴엠", /\brequiem\b|레퀴엠/],
  ["mass", "미사", /\b(mass|missa|messe)\b|미사곡|미사 /],
  ["cantata", "칸타타", /\bcantat(a|e|as)\b|칸타타/],
  ["oratorio", "오라토리오", /\boratorio\b|오라토리오/],
  ["motet", "모테트", /\bmotet(s|te)?\b|모테트/],
  ["passion", "수난곡", /\bpassion\b|수난곡/],
  ["aria", "아리아", /\barias?\b|아리아/],
  ["opera", "오페라", /\b(opera|operetta|singspiel|dramma per musica|tragedie lyrique)\b|오페라/],
  ["ballet", "발레", /\bballet\b|발레/],
  ["stage", "극음악", /incidental music|film score|buhnenmusik|극음악|영화음악/],
  ["song", "가곡 · 노래", /\b(lied(er)?|songs?|melodies?|chanson(s)?|madrigals?)\b|가곡|노래/],
  ["choral", "합창 · 종교곡", /\b(choral|chorale|chorus|choir|hymn|anthem|psalm|canticle|antiphon|a cappella|church music|religious music)\b|합창|코랄|찬송/],
  ["caprice", "카프리스", /\bcapric(e|es|cio|ci)\b|카프리스|기상곡/],
  ["romance", "로망스", /\bromances?\b|로망스/],
  ["elegy", "엘레지", /\beleg(y|ie|ies)\b|비가|엘레지/],
  ["ragtime", "래그타임", /\b(ragtime|rag)\b|래그타임/],
] as const;

const instrumentForms = {
  "piano-concerto":"피아노 협주곡", "violin-concerto":"바이올린 협주곡", "cello-concerto":"첼로 협주곡",
  concerto:"그 밖의 협주곡", "piano-sonata":"피아노 소나타", "violin-sonata":"바이올린 소나타",
  "flute-concerto":"플루트 협주곡", "horn-concerto":"호른 협주곡", "oboe-concerto":"오보에 협주곡",
  "clarinet-concerto":"클라리넷 협주곡", "bassoon-concerto":"바순 협주곡", "keyboard-concerto":"건반 협주곡",
  "trio-sonata":"트리오 소나타", "flute-sonata":"플루트 소나타", "clarinet-sonata":"클라리넷 소나타",
  "cello-sonata":"첼로 소나타", sonata:"그 밖의 소나타",
  keyboard:"건반곡", chamber:"실내악", orchestra:"관현악곡", other:"그 밖의 작품",
};
export type Form = typeof rules[number][0] | keyof typeof instrumentForms;
export const formLabels = new Map<Form, string>([
  ...rules.map(([id,label]) => [id,label] as const),
  ...Object.entries(instrumentForms) as [keyof typeof instrumentForms,string][],
]);
const normalize = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").normalize("NFC").toLowerCase();
const instruments = [
  ["violin", /\bviolins?\b|바이올린/], ["cello", /\b(violon)?cell(o|i)\b|첼로/],
  ["flute", /\bflutes?\b|플루트|플룻/], ["oboe", /\boboes?\b|오보에/], ["clarinet", /\bclarinets?\b|클라리넷/],
  ["bassoon", /\bbassoons?\b|바순/], ["horn", /\bhorns?\b|호른/],
  ["keyboard", /\b(keyboard|harpsichord|clavier|cembalo)s?\b|하프시코드|쳄발로/], ["piano", /\bpianos?\b|pianoforte|피아노/],
] as const;
function namedForm(s: string): Form | undefined {
  const normalized = normalize(s);
  const text = normalized.split(/\bon (?:a |the )?themes?\b|\bon .*?theme\b|\bfrom the opera\b/)[0];
  if (/\bvariations?\b|변주곡/.test(text)) return "variation";
  if (/\b(overture|ouverture)\b|서곡/.test(text)) return "overture";
  if (/concerto grosso|concerti grossi|합주 협주곡/.test(text)) return "concerto-grosso";
  if (/trio sonata|sonata a tre|트리오 소나타/.test(text)) return "trio-sonata";
  const kind = /\b(concerto|concertos|concerti|konzert|concertino)\b|협주곡/.test(text) ? "concerto"
    : /\bsonat(a|as|e|en|ina|ine)s?\b|소나타|소나티네/.test(text) ? "sonata" : null;
  if (kind) {
    const soloists = instruments.filter(([,re])=>re.test(text));
    const otherSoloist = /\b(harp|viola|trumpet|organ|trombone|guitar|saxophone|tuba|recorder)\b|하프(?!시코드)|비올라|트럼펫|오르간/.test(text);
    if (otherSoloist || !soloists.length || (kind === "concerto" && soloists.length > 1)) return kind;
    const specific = (soloists[0][0] + "-" + kind) as Form;
    return formLabels.has(specific) ? specific : kind;
  }
  return rules.find(([, , re]) => re.test(text))?.[0];
}
const claimForms = new Map<number, Set<Form>>();
function broadForm(label: string): Form | undefined {
  if (/^chamber music$/i.test(label)) return "chamber";
  if (/^(piano( solo| piece.*| cycle| four hands)?|organ music|keyboard (music|composition))$/i.test(label)) return "keyboard";
  if (/^(orchestral work|symphonic music)$/i.test(label)) return "orchestra";
}
for (const { label, works } of Object.values(claims)) {
  const form = namedForm(label) ?? broadForm(label);
  if (!form) continue;
  for (const id of works) {
    const set = claimForms.get(id) ?? new Set<Form>();
    set.add(form);
    claimForms.set(id,set);
  }
}
export function classify(w: { slug: string; title: string; title_ko: string | null; instrumentation?: string | null }): Form {
  // An aria or transcription mentioning an opera does not identify the full opera.
  if (cataloguedOperas.has(w.slug)) return "opera";
  if (w.slug === "wikidata-q2401650" || w.slug === "wikidata-q924223") return "aria";
  const names = [namedForm(w.title), namedForm(w.title_ko || "")].filter((x): x is Form => !!x);
  const claims = claimForms.get(Number(/^wikidata-q(\d+)$/.exec(w.slug)?.[1]));
  const sourced = [...(claims ?? [])];
  const broad = new Set<Form>(["keyboard","chamber","orchestra","choral"]);
  const matches = [...names, ...sourced.filter(f => !broad.has(f)), ...sourced.filter(f => broad.has(f))];
  const first = matches[0];
  if (first === "concerto" || first === "sonata") return matches.find(x=>x.endsWith("-"+first)) ?? first;
  if (first) return first;
  return broadForm(w.instrumentation || "") ?? "other";
}
const cataloguedOperas = new Set([
  "mozart-die-zauberflote-k620", "mozart-don-giovanni-k527", "mozart-cosi-fan-tutte-k588", "wikidata-q201873", "wikidata-q578526",
  "verdi-la-traviata", "verdi-rigoletto", "verdi-aida", "verdi-falstaff", "verdi-la-forza-del-destino",
  "verdi-simon-boccanegra", "verdi-don-carlos", "verdi-un-ballo-in-maschera",
  "puccini-madama-butterfly", "puccini-gianni-schicchi", "puccini-la-boheme", "puccini-turandot", "puccini-manon-lescaut", "puccini-tosca",
  "wagner-die-meistersinger-wwv96", "wagner-lohengrin-wwv75", "bizet-carmen",
]);
