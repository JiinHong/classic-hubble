import { describe, expect, it } from "vitest";
import { formalSeries, workDisplay } from "./work-display";

describe("bilingual work labels", () => {
  it("removes only the identified composer's disambiguator and keeps variants", () => {
    expect(workDisplay("Concerto for Piano and Orchestra No. 1 in E minor", "피아노 협주곡 1번 (쇼팽)", "Op. 11", "프레데리크 쇼팽").heading).toBe("피아노 협주곡 1번");
    expect(workDisplay("Petite suite", "작은 모음곡(드뷔시)", null, "클로드 드뷔시").heading).toBe("작은 모음곡");
    expect(formalSeries("Church Sonata No. 3 (Mozart) in D major", "Wolfgang Amadeus Mozart").ordinal).toBe(3);
    expect(workDisplay("Violin Sonata No. 5", "베토벤 바이올린 소나타 5번", "", "루트비히 판 베토벤").heading).toBe("바이올린 소나타 5번");
    expect(workDisplay("Sonata", "소나타 (초판)", null, "쇼팽").heading).toBe("소나타 (초판)");
    expect(workDisplay("Variations", "변주곡 (바흐)", null, "쇼팽").heading).toBe("변주곡 (바흐)");
  });
  it("distinguishes an opus set from a numbered piece using its original title", () => {
    expect(workDisplay("Nocturnes, Op. 15", "녹턴, Op. 15", "Op. 15").heading).toBe("녹턴집 Op. 15");
    expect(workDisplay("Nocturne No. 20 in C-sharp minor, Op. posth.", "녹턴 올림다단조, Op. posth (쇼팽)", "", "프레데리크 쇼팽").heading).toBe("녹턴 20번");
  });
  it.each([
    [1, "Scherzo No. 1 in B Minor, Op. 20", "스케르초 1번", "B minor", 20],
    [2, "Scherzo no. 2 in B-flat minor, op. 31", "스케르초 2번", "B-flat minor", 31],
    [3, "Scherzo No. 3 in C-sharp minor, Op. 39", null, "C-sharp minor", 39],
    [4, "Scherzo no. 4 in E major, op. 54", "스케르초 4번", "E major", 54],
  ] as const)("renders scherzo %i like the ballades", (n, title, ko, key, op) => {
    expect(workDisplay(title, ko, "Op. " + op)).toEqual({ heading: "스케르초 " + n + "번", subtitle: `Scherzo No. ${n} in ${key}, Op. ${op}` });
  });
  it.each([
    ["Ballade No. 3 in A-flat major, Op. 47", "발라드 3번", "Op. 47", "발라드 3번", "Ballade No. 3 in A-flat major, Op. 47"],
    ["Nocturne No.10 in A-flat major, Op.32, No.2", "야상곡 10번 내림가장조, Op. 32 No. 2", "Op. 32 No. 2", "녹턴 10번", "Nocturne No. 10 in A-flat major, Op. 32 No. 2"],
    ["Étude Op. 25, No. 1 in A-flat major", "연습곡 13번", "Op. 25 No. 1", "에튀드 13번", "Étude Op. 25 No. 1 in A-flat major"],
    ["Prélude no. 8 in F-sharp minor, op. 28", null, "Op. 28 No. 8", "프렐류드 8번", "Prélude No. 8 in F-sharp minor, Op. 28 No. 8"],
    ["Mazurka in F minor, Op. 68, No. 4", null, "Op. 68 No. 4", "마주르카 바단조", "Mazurka in F minor, Op. 68 No. 4"],
    ["Mazurkas, Op. 24", null, "Op. 24", "마주르카집 Op. 24", "Mazurkas, Op. 24"],
    ["Keyboard Sonata in E flat Major", null, "", "건반 소나타 내림마장조", "Keyboard Sonata in E-flat major"],
    ["Keyboard Sonata in E major, op. 5,5", null, null, "건반 소나타 마장조", "Keyboard Sonata in E major, Op. 5 No. 5"],
    ["Double Bass Concerto No. 2", null, null, "콘트라베이스 협주곡 2번", "Double Bass Concerto No. 2"],
    ["Piano Sonata Hob. XVI/20 in C minor", null, null, "피아노 소나타 다단조", "Piano Sonata Hob. XVI:20 in C minor"],
    ["Sonata for Piano four-hands", null, null, "네 손을 위한 피아노 소나타", "Sonata for Piano four-hands"],
    ["Viola d'amore concerto in D minor (RV 393)", null, null, "비올라 다모레 협주곡 라단조", "Viola d'amore concerto in D minor (RV 393)"],
    ["Sonata in G major for two keyboards, op. 15,5", null, null, "두 대의 건반을 위한 소나타 사장조", "Sonata in G major for two keyboards, Op. 15 No. 5"],
    ["Sinfonietta", null, null, "신포니에타", "Sinfonietta"],
    ["Symphony No. 2 in E minor", "교향곡 제2번", "Op. 27", "교향곡 2번", "Symphony No. 2 in E minor, Op. 27"],
    ["String Quartet no.3 in C♯ minor", null, null, "현악 사중주 3번", "String Quartet No. 3 in C-sharp minor"],
    ["Waltz No. 6 in D-flat major", "강아지 왈츠", "Op. 64 No. 1", "강아지 왈츠", "Waltz No. 6 in D-flat major, Op. 64 No. 1"],
    ["Violin concerto in D major (RV 208) \"Grosso Mogul\"", null, "RV 208", "바이올린 협주곡 라장조 ‘Grosso Mogul’", "Violin concerto in D major (RV 208) \"Grosso Mogul\""],
    ["Sonata for violin and continuo in C minor (RV 5)", null, "RV 5", "바이올린과 통주저음을 위한 소나타 다단조", "Sonata for violin and continuo in C minor (RV 5)"],
    ["24 Preludes op. 28", null, "Op. 28", "24개의 프렐류드", "24 Preludes Op. 28"],
    ["Mazurka Op. 33 nr. 1 in G-sharp minor", null, "Op. 33 No. 1", "마주르카 올림사단조", "Mazurka Op. 33 No. 1 in G-sharp minor"],
    ["Waltz No. 14 in E minor, Op. posth.", null, "", "왈츠 14번", "Waltz No. 14 in E minor, Op. posth."],
    ["Waltz No. 5 in A-flat major, Op. 42", "왈츠, Op. 42", "Op. 42", "왈츠 5번", "Waltz No. 5 in A-flat major, Op. 42"],
    ["Concerto for Clarinet and Orchestra in A major", null, "K. 622", "클라리넷 협주곡 가장조", "Concerto for Clarinet and Orchestra in A major, K. 622"],
    ["Piece (Sz. 18) for piano", "피아노 소품", "Sz. 18", "피아노 소품", "Piece (Sz. 18) for piano"],
    ["Flute Concerto No. 2 in D major", "플룻 협주곡 제 2 번", "", "플루트 협주곡 2번", "Flute Concerto No. 2 in D major"],
    ["String Quartet in E-flat major, op. 33 no. 2, Hob. III:38 “The Joke”", null, "Hob. III:38", "현악 사중주 내림마장조 ‘The Joke’", "String Quartet in E-flat major, Op. 33 No. 2, Hob. III:38 “The Joke”"],
    ["String Quartet", "현악 4중주", null, "현악 사중주", "String Quartet"],
    ["Prelude no. 13 in F-sharp major, Op. 28", null, "Op. 28", "프렐류드 13번", "Prélude No. 13 in F-sharp major, Op. 28"],
    ["2 Bourrées", null, null, "2개의 부레", "2 Bourrées"],
    ["Concerto for 4 violins and cello in B minor (RV 580)", null, null, "네 대의 바이올린과 첼로를 위한 협주곡 나단조", "Concerto for 4 violins and cello in B minor (RV 580)"],
    ["Sonata for recorder, bassoon, and continuo in A minor (RV 86)", null, "RV 86", "리코더, 바순과 통주저음을 위한 소나타 가단조", "Sonata for recorder, bassoon, and continuo in A minor (RV 86)"],
    ["Étude No.3 from Trois nouvelles études in D-flat major", null, "", "세 개의 새로운 에튀드 중 3번", "Étude No. 3 from Trois nouvelles études in D-flat major"],
  ] as const)("formats %s", (title, ko, cat, heading, subtitle) => {
    expect(workDisplay(title, ko, cat)).toEqual({ heading, subtitle });
  });
  it("does not promote an excerpt, quoted form, or opus member into a numbered standalone work", () => {
    for (const title of ["Sonata No. 2: II. Scherzo", "Variations on a Theme from a Scherzo", "Scherzo No. 2 (arr. for flute)"])
      expect(workDisplay(title, null, null).heading).toBe(title);
    expect(workDisplay("Étude Op. 25 No. 1", null, null).heading).toBe("에튀드 Op. 25 No. 1");
  });
  it("keeps unknown titles, nicknames and independent catalogue identifiers intact", () => {
    expect(workDisplay("Totentanz", "liszt", "S. 126")).toEqual({ heading: "Totentanz", subtitle: "S. 126" });
    expect(workDisplay("Symphony No. 5 in C minor", "교향곡 5번 '운명'", "Op. 67").heading).toBe("교향곡 5번 '운명'");
    expect(workDisplay("Piece, Op. 20", null, "Op. 2").subtitle).toBe("Op. 2");
    expect(workDisplay("Allegro", "Allegro", null)).toEqual({ heading: "Allegro", subtitle: "" });
    expect(workDisplay("Sonata in D major", "소나타 제2번 라장조 (초판)", "").heading).toContain("초판");
  });
});
