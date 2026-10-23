import importlib
import importlib.util
from dataclasses import replace

import pytest
from classic_hubble_pipeline.music_matching import MusicMatcher, _titles
from classic_hubble_pipeline.work_matching import CanonicalWork

BEETHOVEN = CanonicalWork(
    "beethoven-8",
    "beethoven-8",
    ("Violin Sonata No. 8 in G major", "바이올린 소나타 8번"),
    ("Ludwig van Beethoven", "루트비히 판 베토벤"),
    "Op. 30",
    ("Sonata for Violin and Piano No. 8 in G Major, Op. 30, No. 3",),
)


def matcher(works):
    name = "classic_hubble_pipeline.music_matching"
    assert importlib.util.find_spec(name), "Structured music matcher is missing"
    return importlib.import_module(name).MusicMatcher(works)


@pytest.mark.parametrize("code", ["WAB 106", "WAB.106", "wab106"])
def test_grounded_wab_number_matches_only_explicit_canonical_identity(code):
    work = CanonicalWork(
        "bruckner-6", "bruckner-6", ("Symphony No. 6 in A major",),
        ("Anton Bruckner",), "WAB 106",
    )
    assert matcher([work]).match(
        "Symphony No. 6", "Anton Bruckner", catalogue=code, key="A major",
    ).work_id == work.id


def test_wab_number_embedded_in_title_matches():
    work = CanonicalWork("w", "w", ("Symphony No. 6",), ("Bruckner",), "WAB 106")
    assert matcher([work]).match("Symphony No. 6, WAB 106", "Bruckner").work_id == "w"


@pytest.mark.parametrize("code", ["WAB 107", "WAB 106; WAB 107", "WAB 106,1", "WAB 106/1"])
def test_conflicting_or_versioned_wab_does_not_fall_back_to_exact_title(code):
    work = CanonicalWork("w", "w", ("Symphony No. 6",), ("Bruckner",), "WAB 106")
    assert matcher([work]).match("Symphony No. 6", "Bruckner", catalogue=code).work_id is None


@pytest.mark.parametrize("suffix", [",1", "/1", "-107", ".1"])
def test_versioned_wab_in_title_is_not_reduced_to_parent(suffix):
    work = CanonicalWork("w", "w", ("Symphony No. 6",), ("Bruckner",), "WAB 106")
    assert matcher([work]).match("Symphony No. 6 WAB 106" + suffix, "Bruckner").work_id is None


def test_wab_requires_catalogue_evidence_on_canonical_work():
    work = CanonicalWork("w", "w", ("Symphony No. 6",), ("Bruckner",), None)
    assert matcher([work]).match("Symphony No. 6", "Bruckner", catalogue="WAB 106").work_id is None


def test_unsupported_wab_does_not_modify_legacy_catalogue_parser():
    from classic_hubble_pipeline.work_matching import CATALOGUE
    assert CATALOGUE.search("WAB 106") is None


@pytest.mark.parametrize("printed", ["Bb Major", "Bb장조", "Bb Major Bb장조"])
def test_ascii_flat_key_in_archived_prokofiev_program_matches(printed):
    work = CanonicalWork(
        "prokofiev-5", "prokofiev-5", ("Symphony No. 5 in B-flat major",),
        ("Sergei Prokofiev", "프로코피예프"), "Op. 100",
    )
    result = matcher([work]).match(
        "Symphony No.5 교향곡5번", "S.Prokofiev 프로코피예프",
        catalogue="Op.100", key=printed,
    )
    assert result.work_id == work.id


@pytest.mark.parametrize("printed", ["Bb Major", "Bb장조"])
def test_ascii_flat_cannot_match_natural_key_with_same_catalogue(printed):
    work = CanonicalWork("w", "w", ("Symphony No. 5 in B major",), ("Prokofiev",), "Op.100")
    assert matcher([work]).match("Symphony No.5", "Prokofiev", catalogue="Op.100", key=printed).work_id is None


def test_mixed_ascii_flat_and_natural_keys_are_conflicting():
    work = CanonicalWork("w", "w", ("Symphony No. 5 in B major",), ("Prokofiev",), "Op.100")
    result = matcher([work]).match("Symphony No.5", "Prokofiev", catalogue="Op.100", key="Bb Major B major")
    assert result.work_id is None
    assert result.reason == "conflicting_keys"


def test_ascii_flat_key_is_removed_for_composer_scoped_title_comparison():
    work = CanonicalWork("w", "w", ("Sonata in E-flat minor",), ("Composer",), None)
    assert matcher([work]).match("Sonata in Eb minor", "Composer").work_id == "w"


@pytest.mark.parametrize("catalogue", ["Op.37 작품번호 37", "작품번호37 Op. 37"])
def test_matching_bilingual_catalogue_labels_in_archived_concerto_program(catalogue):
    work = CanonicalWork(
        "beethoven-3", "beethoven-3", ("Piano Concerto No. 3 in C minor",),
        ("Ludwig van Beethoven", "베토벤"), "Op. 37",
    )
    assert matcher([work]).match(
        "Piano Concerto No. 3", "Beethoven", catalogue=catalogue,
    ).work_id == work.id


@pytest.mark.parametrize("code", ["WoO 23", "K. 23", "BWV 23"])
def test_generic_korean_number_does_not_assume_an_opus_scheme(code):
    work = CanonicalWork("w", "w", ("Work",), ("Composer",), code)
    assert matcher([work]).match(
        "Work", "Composer", catalogue=code + " 작품번호 23",
    ).work_id == "w"


@pytest.mark.parametrize("catalogue", [
    "작품번호 37", "Op.37 작품번호 38", "Op.37 No.2 작품번호 37",
    "Op.37 작품번호37/2", "Op.37 작품번호37a", "Op.37 작품번호37번",
])
def test_unconfirmed_or_conflicting_generic_catalogue_numbers_remain_unlinked(catalogue):
    work = CanonicalWork("w", "w", ("Work",), ("Composer",), "Op.37")
    assert matcher([work]).match("Work", "Composer", catalogue=catalogue).work_id is None


@pytest.mark.parametrize("title", ["Fantasy", "Fantasia", "Fantaisie", "Fantasie", "Phantasy"])
@pytest.mark.parametrize("composer", [None, "Gabriel Faure"])
def test_generic_fantasy_label_does_not_identify_a_work(title, composer):
    work = CanonicalWork(
        "faure", "faure", ("Fantaisie in G for piano and orchestra in G major",),
        ("Gabriel Faure",), None, (title, "Fantaisie, Op. 111"),
    )
    assert matcher([work]).match(title, composer).work_id is None


def test_fantasy_genre_and_instrumentation_are_not_distinctive_without_composer():
    work = CanonicalWork(
        "faure", "faure", ("Fantaisie for piano and orchestra",), ("Gabriel Faure",), None,
    )
    assert matcher([work]).match(work.titles[0], None).work_id is None


def test_fantasy_with_explicit_composer_and_catalogue_remains_supported():
    work = CanonicalWork(
        "faure", "faure", ("Fantaisie in G for piano and orchestra",),
        ("Gabriel Faure",), None, ("Fantasy", "Fantaisie, Op. 111"),
    )
    assert matcher([work]).match("Fantasy", "Gabriel Faure", catalogue="Op.111").work_id == "faure"


@pytest.mark.parametrize("title", ["Wanderer Fantasy", "Carmen Fantasy"])
def test_named_fantasies_remain_distinctive(title):
    work = CanonicalWork("w", "w", (title,), ("Composer",), None)
    assert matcher([work]).match(title, None).work_id == "w"


def donizetti_work():
    return CanonicalWork(
        "donizetti-elixir", "donizetti-elixir", ("사랑의 묘약", "L'elisir d'amore"),
        ("Gaetano Donizetti", "가에타노 도니체티"), None,
    )


@pytest.mark.parametrize("composer", [
    "가에타노 도니제티", "가에타노도니제티",
    "가에타노 도니제티 (Gaetano Donizetti)",
    "가에타노 도니체티", "Gaetano Donizetti",
])
def test_donizetti_source_backed_full_name_transliteration(composer):
    work = donizetti_work()
    assert matcher([work]).match("사랑의 묘약", composer).work_id == work.id


@pytest.mark.parametrize("composer", ["도니제티", "가에타노 도니저티", "조반니 도니제티"])
def test_donizetti_alias_does_not_enable_fuzzy_or_surname_matching(composer):
    result = matcher([donizetti_work()]).match("사랑의 묘약", composer)
    assert result.work_id is None
    assert result.reason == "composer_unconfirmed"


@pytest.mark.parametrize("names", [("Giovanni Donizetti",), ("Donizetti",)])
def test_donizetti_alias_requires_full_canonical_identity(names):
    work = replace(donizetti_work(), composers=names)
    assert matcher([work]).match("사랑의 묘약", "가에타노 도니제티").work_id is None


def test_donizetti_alias_keeps_conflicting_bilingual_composers_unmatched():
    result = matcher([donizetti_work(), BEETHOVEN]).match(
        "사랑의 묘약", "가에타노 도니제티 (Ludwig van Beethoven)",
    )
    assert result.work_id is None
    assert result.reason == "conflicting_composers"


def test_donizetti_alias_keeps_duplicate_and_review_guards():
    work = donizetti_work()
    duplicate = matcher([work, replace(work, id="duplicate")]).match(
        "사랑의 묘약", "가에타노 도니제티",
    )
    assert duplicate.work_id is None and duplicate.reason == "ambiguous"
    review = matcher([replace(work, requires_review=True)]).match(
        "사랑의 묘약", "가에타노 도니제티",
    )
    assert review.work_id is None and review.reason == "catalog_review_required"


def bach_catalogue_conflict_works():
    goldberg = CanonicalWork(
        "goldberg", "goldberg", ("Goldberg Variations in G major",),
        ("Johann Sebastian Bach",), "BWV 988",
        ("Goldberg Variations", "골드베르크 변주곡"),
    )
    prelude = replace(
        goldberg, id="prelude", slug="prelude",
        titles=("Prelude, Fugue and Allegro in E-flat major, BWV 998",),
        catalogue="BWV 998", aliases=("BWV 998",),
    )
    return goldberg, prelude


@pytest.mark.parametrize("title,catalogue", [
    ("Goldberg Variations", "BWV 998"),
    ("Goldberg Variations, BWV 998", None),
    ("골드베르크 변주곡", "BWV 998"),
    ("Goldberg Variations 골드베르크 변주곡", "BWV 998"),
])
@pytest.mark.parametrize("scoped", [False, True])
def test_known_distinctive_title_rejects_another_works_catalogue(title, catalogue, scoped):
    result = matcher(bach_catalogue_conflict_works()).match(
        title, "J. S. Bach", catalogue=catalogue, scoped=scoped,
    )
    assert result.work_id is None
    assert result.candidate_ids == ()
    assert result.reason == "title_catalogue_conflict"


@pytest.mark.parametrize("title,catalogue,expected", [
    ("Goldberg Variations", "BWV 988", "goldberg"),
    ("골드베르크 변주곡", "BWV 988", "goldberg"),
    ("BWV 998", None, "prelude"),
    ("Prelude, Fugue and Allegro", "BWV 998", "prelude"),
])
def test_consistent_titles_and_catalogue_only_labels_still_match(title, catalogue, expected):
    assert matcher(bach_catalogue_conflict_works()).match(
        title, "J. S. Bach", catalogue=catalogue,
    ).work_id == expected


def test_distinctive_title_guard_stays_composer_scoped_and_allows_shared_titles():
    goldberg, prelude = bach_catalogue_conflict_works()
    namesake = replace(goldberg, composers=("Another Composer",))
    assert matcher([namesake, prelude]).match(
        "Goldberg Variations", "J. S. Bach", catalogue="BWV 998",
    ).work_id == prelude.id
    same_title = replace(prelude, aliases=("Goldberg Variations",))
    assert matcher([goldberg, same_title]).match(
        "Goldberg Variations", "J. S. Bach", catalogue="BWV 998",
    ).work_id == prelude.id


def test_title_conflict_guard_does_not_drop_a_bilingual_leading_count():
    twelve = CanonicalWork(
        "op12", "op12", ("Fantasiestucke, Op. 12",), ("Robert Schumann",),
        "Op. 12", ("Fantasiestucke",),
    )
    eleven = replace(
        twelve, id="op111", slug="op111", titles=("Drei Fantasiestucke",),
        catalogue=None, aliases=("Three Fantasiestucke, Op. 111",),
    )
    result = matcher([twelve, eleven]).match(
        "세개의 환상소곡집 3 Fantasiestucke", "R. Schumann", catalogue="Op. 111",
    )
    assert result.work_id == "op111"


def test_missing_catalogue_metadata_is_not_reported_as_a_source_conflict():
    goldberg, _ = bach_catalogue_conflict_works()
    incomplete = replace(goldberg, catalogue=None)
    result = matcher([incomplete]).match(
        "Goldberg Variations", "J. S. Bach", catalogue="BWV 988",
    )
    assert result.work_id is None
    assert result.reason == "no_candidate"


def shared_catalogue_parent_and_component():
    parent = CanonicalWork(
        "suite", "suite", ("Nutcracker Suite",), ("Pyotr Ilyich Tchaikovsky",),
        "Op. 71a", ("The Nutcracker Suite",),
    )
    component = replace(
        parent, id="march", slug="march", titles=("Nutcracker March",),
        catalogue=None,
        aliases=("The Nutcracker Suite, Op. 71a: II. Danses: a) Marche",),
    )
    return parent, component


def test_exact_distinctive_title_disambiguates_shared_parent_catalogue():
    result = matcher(shared_catalogue_parent_and_component()).match(
        "The Nutcracker Suite", "P. I. Tchaikovsky", catalogue="Op. 71a", scoped=True,
    )
    assert result.work_id == "suite"
    assert result.reason == "composer_and_catalogue"


def test_exact_component_title_can_disambiguate_shared_parent_catalogue():
    result = matcher(shared_catalogue_parent_and_component()).match(
        "Nutcracker March", "P. I. Tchaikovsky", catalogue="Op. 71a", scoped=True,
    )
    assert result.work_id == "march"
    assert result.reason == "composer_and_catalogue"


def test_complete_chopin_op22_title_does_not_match_polonaise_component():
    parent = CanonicalWork(
        "complete", "complete", ("Andante spianato et grande polonaise brillante",),
        ("Frederic Chopin",), "Op. 22",
        ("Andante spianato and Grande polonaise brillante", "Grande polonaise brillante"),
    )
    component = replace(
        parent, id="polonaise", slug="polonaise", titles=("Grande polonaise brillante",),
        aliases=("Andante spianato et grande polonaise brillante, Op. 22: II. Grande polonaise",),
    )
    m = matcher([parent, component])
    assert m.match("Andante spianato and Grande polonaise brillante", "F. Chopin", catalogue="Op. 22").work_id == "complete"
    assert m.match("Grande polonaise brillante", "F. Chopin", catalogue="Op. 22").work_id is None


@pytest.mark.parametrize("title", ["Suite", "Op. 71a", "Unknown Nutcracker programme"])
def test_shared_catalogue_without_unique_exact_title_stays_ambiguous(title):
    result = matcher(shared_catalogue_parent_and_component()).match(
        title, "P. I. Tchaikovsky", catalogue="Op. 71a",
    )
    assert result.work_id is None
    assert result.reason == "ambiguous"


def test_exact_catalogue_title_does_not_resolve_duplicate_or_reviewed_identity():
    parent, component = shared_catalogue_parent_and_component()
    duplicate = replace(parent, id="duplicate", slug="duplicate")
    assert matcher([parent, component, duplicate]).match(
        "The Nutcracker Suite", "P. I. Tchaikovsky", catalogue="Op. 71a",
    ).work_id is None
    result = matcher([replace(parent, requires_review=True), component]).match(
        "The Nutcracker Suite", "P. I. Tchaikovsky", catalogue="Op. 71a",
    )
    assert result.work_id is None


@pytest.mark.parametrize("composer,catalogue,key", [
    ("F. Chopin", "Op. 71a", None),
    ("P. I. Tchaikovsky", "Op. 71", None),
    ("P. I. Tchaikovsky", "Op. 71a", "C minor"),
])
def test_exact_title_never_overrides_composer_catalogue_or_key(composer, catalogue, key):
    parent, component = shared_catalogue_parent_and_component()
    works = [replace(w, titles=(*w.titles, "Suite in D major")) for w in (parent, component)]
    assert matcher(works).match("The Nutcracker Suite", composer, catalogue=catalogue, key=key).work_id is None


def test_bilingual_composer_lifespan_and_catalogue_alias_identify_work():
    result = matcher([BEETHOVEN]).match(
        "Violin Sonata No.8 in G major 바이올린 소나타 8번",
        "Ludwig van Beethoven (1770 - 1827) 루트비히판 베토벤",
        catalogue="Op.30 No.3",
        key="in G major 사장조",
    )
    assert result.work_id == BEETHOVEN.id


@pytest.mark.parametrize("printed,canonical", [
    ("Johann Strauss II", "Johann Strauss Jr"),
    ("Johann Strauss Jr.", "Johann Strauss II"),
    ("Johann Strauss Junior", "Johann Strauss Jr"),
    ("Johann Strauß II (1825-1899)", "Johann Strauss Jr"),
])
def test_qualified_johann_strauss_son_names_are_equivalent(printed, canonical):
    work = replace(BEETHOVEN, composers=(canonical,),
                   titles=("Die Fledermaus",), catalogue="Op. 362", aliases=())
    assert matcher([work]).match("Die Fledermaus", printed).work_id == work.id


@pytest.mark.parametrize("printed,canonical", [
    ("Johann Strauss I", "Johann Strauss II"),
    ("Johann Strauss I", "Johann Strauss Jr"),
    ("Johann Strauss III", "Johann Strauss Jr"),
    ("Johann Strauss II", "Johann Strauss I"),
    ("Johann Strauss Jr", "Richard Strauss"),
    ("Johann Strauss II", "Josef Strauss"),
    ("Johann Strauss II", "Johann Strauss"),
])
def test_qualified_strauss_names_do_not_drop_generation_or_first_name(printed, canonical):
    work = replace(BEETHOVEN, composers=(canonical,),
                   titles=("Die Fledermaus",), catalogue="Op. 362", aliases=())
    assert matcher([work]).match("Die Fledermaus", printed).work_id is None


def test_strauss_son_equivalence_preserves_identity_conflicts():
    work = replace(BEETHOVEN, composers=("Johann Strauss Jr",),
                   titles=("Die Fledermaus",), catalogue="Op. 362", aliases=())
    assert matcher([work, replace(work, id="duplicate")]).match(
        "Die Fledermaus", "Johann Strauss II",
    ).work_id is None
    assert matcher([work]).match(
        "Die Fledermaus", "Johann Strauss II", catalogue="Op. 363",
    ).work_id is None
    father = replace(work, id="father", composers=("Johann Strauss I", "요한 슈트라우스 아버지"))
    result = matcher([work, father]).match(
        "Die Fledermaus", "Johann Strauss II 요한 슈트라우스 아버지",
    )
    assert result.work_id is None
    assert result.reason == "conflicting_composers"


def numbered_ballades():
    return [
        replace(
            BEETHOVEN, id=f"chopin-{number}", slug=f"chopin-{number}",
            titles=(f"Ballade No. {number} in {key}",),
            composers=("Frederic Chopin",), catalogue=catalogue, aliases=(),
        )
        for number, key, catalogue in (
            (1, "G minor", "Op. 23"),
            (2, "F major", "Op. 38"),
            (3, "A-flat major", "Op. 47"),
        )
    ]


@pytest.mark.parametrize("number", [1, 2, 3])
def test_numbered_ballades_plural_matches_only_its_number(number):
    result = matcher(numbered_ballades()).match(f"Ballades No. {number}", "F. Chopin")
    assert result.work_id == f"chopin-{number}"


@pytest.mark.parametrize("title", ["Ballades", "Ballades No. 1,2,3", "Ballades No. 1-3", "Ballades No. 5"])
def test_ballades_collection_or_missing_number_is_not_collapsed_to_one_work(title):
    assert matcher(numbered_ballades()).match(title, "F. Chopin").work_id is None


def test_ballades_plural_keeps_composer_catalogue_key_and_ambiguity_guards():
    works = numbered_ballades()
    m = matcher(works)
    assert m.match("Ballades No. 1", "F. Mendelssohn").work_id is None
    assert m.match("Ballades No. 1", "F. Chopin", catalogue="Op. 38").work_id is None
    assert m.match("Ballades No. 1", "F. Chopin", key="F major").work_id is None
    duplicate = replace(works[0], id="different-ballade")
    assert matcher([*works, duplicate]).match("Ballades No. 1", "F. Chopin").work_id is None


def test_ballades_plural_does_not_create_composerless_title_fallback():
    works = [
        replace(work, aliases=(f"Ballade No. {index}",))
        for index, work in enumerate(numbered_ballades(), start=1)
    ]
    assert matcher(works).match("Ballades No. 1", None).work_id is None


@pytest.mark.parametrize(
    "catalogue", ["Op.30 No.2", "Op.300 No.3", "Op.30 No.3; Op.31"]
)
def test_catalogue_alias_never_falls_back_to_wrong_parent_or_sibling(catalogue):
    assert (
        matcher([BEETHOVEN])
        .match(
            BEETHOVEN.titles[0],
            "Beethoven",
            catalogue=catalogue,
        )
        .work_id
        is None
    )


def test_duplicate_bilingual_catalogue_and_keys_are_not_conflicts():
    work = replace(BEETHOVEN, catalogue="Op.29", aliases=())
    result = matcher([work]).match(
        work.titles[0],
        "L. van Beethoven 베토벤",
        catalogue="op.29 op.29",
        key="G major 사장조",
    )
    assert result.work_id == work.id


@pytest.mark.parametrize("printed,canonical", [
    ("B-flat장조", "B-flat major"),
    ("A-flat장조", "A-flat major"),
    ("c-sharp단조", "C-sharp minor"),
    ("B♭장조", "B-flat major"),
    ("C#단조", "C-sharp minor"),
    ("내림B장조", "B-flat major"),
    ("내림 B 장조 B-flat장조", "B-flat major"),
    ("올림C단조", "C-sharp minor"),
    ("올림 C 단조 C#단조", "C-sharp minor"),
])
def test_latin_accidental_with_korean_mode_preserves_key_identity(printed, canonical):
    work = replace(BEETHOVEN, titles=(f"Violin Sonata No. 8 in {canonical}",),
                   catalogue="Op. 29", aliases=())
    result = matcher([work]).match(
        "Violin Sonata No. 8", "Beethoven", catalogue="Op. 29", key=printed,
    )
    assert result.work_id == work.id


@pytest.mark.parametrize("key", ["B-flat장조", "B major B-flat장조", "B-flat단조"])
def test_hybrid_key_never_drops_accidental_or_conflict(key):
    work = replace(BEETHOVEN, titles=("Violin Sonata No. 8 in B major",),
                   catalogue="Op. 29", aliases=())
    assert matcher([work]).match(
        "Violin Sonata No. 8", "Beethoven", catalogue="Op. 29", key=key,
    ).work_id is None


@pytest.mark.parametrize("key", ["내림B장조", "내림 B 장조", "올림C단조", "올림 C 단조"])
def test_stripping_korean_key_does_not_leave_accidental_prefix(key):
    assert "violin sonata no 8" in _titles(f"Violin Sonata No. 8 {key}")


@pytest.mark.parametrize("key", ["in c minor 다단조", "G major 다단조"])
def test_conflicting_key_abstains(key):
    assert (
        matcher([BEETHOVEN])
        .match(
            BEETHOVEN.titles[0],
            "Beethoven",
            catalogue="Op.30 No.3",
            key=key,
        )
        .work_id
        is None
    )


def test_conflicting_bilingual_composers_never_pick_one_side():
    other = replace(
        BEETHOVEN, id="mozart", composers=("Wolfgang Amadeus Mozart", "모차르트")
    )
    result = matcher([BEETHOVEN, other]).match(
        BEETHOVEN.titles[0],
        "Ludwig van Beethoven 모차르트",
        catalogue="Op.30 No.3",
    )
    assert result.work_id is None
    assert result.reason == "conflicting_composers"


def test_shared_surname_is_ambiguous_even_when_only_one_catalogue_matches():
    robert = replace(BEETHOVEN, id="robert", composers=("Robert Schumann",))
    clara = replace(
        BEETHOVEN,
        id="clara",
        composers=("Clara Schumann",),
        catalogue="Op.22",
        aliases=(),
    )
    assert matcher([robert, clara]).match("Op.30 No.3", "Schumann").work_id is None


def test_quoted_nickname_inside_long_title_matches_without_arbitrary_substring():
    work = replace(
        BEETHOVEN,
        id="tartini",
        titles=("Violin Sonata in G minor",),
        catalogue=None,
        composers=("Giuseppe Tartini",),
        aliases=("Devil's Trill",),
    )
    result = matcher([work]).match(
        'Violin Sonata in g minor, "Devil\'s Trill"', "G. Tartini"
    )
    assert result.work_id == "tartini"
    assert (
        matcher([work])
        .match("Not Devil's Trill but a different sonata", "G. Tartini")
        .work_id
        is None
    )


def test_conflicting_work_number_not_hidden_by_matching_nickname():
    work = replace(BEETHOVEN, aliases=("Spring",), catalogue=None)
    assert (
        matcher([work]).match('Violin Sonata No.9 "Spring"', "Beethoven").work_id
        is None
    )


def test_ocr_typo_only_returns_candidate_not_unverified_auto_link():
    work = replace(
        BEETHOVEN,
        id="prokofiev",
        composers=("Sergei Prokofiev",),
        catalogue="Op.56",
        aliases=(),
    )
    result = matcher([work]).match(
        "Sonata for two violins", "S.Prokofev", catalogue="Op.56"
    )
    assert result.work_id is None
    assert result.candidate_ids == ("prokofiev",)
    assert result.reason == "composer_spelling_candidate"


def test_multiple_exact_titles_remain_ambiguous():
    other = replace(BEETHOVEN, id="second")
    assert matcher([BEETHOVEN, other]).match("Op.30 No.3", "Beethoven").work_id is None


def test_alias_catalogue_conflicting_with_primary_catalogue_is_ignored():
    work = replace(BEETHOVEN, catalogue="Op.18")
    assert matcher([work]).match("Op.30 No.3", "Beethoven").work_id is None


def test_distinct_catalogue_systems_require_both_to_belong_to_same_work():
    work = replace(BEETHOVEN, catalogue="Op.104", aliases=("Cello Concerto B.191",))
    # Unsupported catalogue systems must not be silently treated as verified.
    assert (
        matcher([work])
        .match("Cello Concerto", "Beethoven", catalogue="Op.104 Op.105")
        .work_id
        is None
    )


def test_korean_numbered_title_never_degrades_to_generic_genre():
    five = replace(
        BEETHOVEN,
        id="five",
        titles=("Symphony No. 5", "교향곡 5번"),
        aliases=(),
        catalogue=None,
    )
    six = replace(five, id="six", titles=("Symphony No. 6", "교향곡 6번"))
    assert matcher([five, six]).match("교향곡 5번", "Beethoven").work_id == "five"


@pytest.mark.parametrize("title", ["Liszt", "왈츠"])
def test_polluted_composer_or_genre_only_alias_never_identifies_a_work(title):
    work = replace(
        BEETHOVEN,
        composers=("Franz Liszt",),
        titles=("Totentanz", title),
        aliases=(title,),
    )
    result = matcher([work]).match(title, "Liszt")
    assert result.work_id is None
    assert result.reason == "insufficient_title"


def test_korean_number_conflict_is_not_hidden_by_another_language():
    result = matcher([BEETHOVEN]).match(
        "Violin Sonata No.8 바이올린 소나타 9번",
        "Beethoven",
        catalogue="Op.30 No.3",
    )
    assert result.work_id is None


def test_bilingual_title_conflict_is_not_ignored_when_one_alias_matches():
    work = replace(BEETHOVEN, aliases=("Spring",), catalogue=None)
    assert (
        matcher([work]).match("Spring 피아노 협주곡 2번", "Beethoven").work_id is None
    )


@pytest.mark.parametrize("title", ["바이올린소나타제8번", "바이올린 소나타 No.08"])
def test_korean_spacing_and_number_styles_preserve_number(title):
    work = replace(BEETHOVEN, catalogue=None, aliases=())
    assert matcher([work]).match(title, "Beethoven").work_id == work.id
    assert matcher([work]).match(title.replace("8", "9"), "Beethoven").work_id is None


def test_two_catalogue_systems_recorded_on_one_work_are_both_usable():
    work = replace(
        BEETHOVEN,
        titles=("Four Impromptus, D. 899 (Op. 90)",),
        catalogue="Op.90",
        aliases=(),
    )
    assert (
        matcher([work]).match("Four Impromptus", "Beethoven", catalogue="D.899").work_id
        == work.id
    )
    assert (
        matcher([work]).match("Four Impromptus", "Beethoven", catalogue="D.900").work_id
        is None
    )
    assert (
        matcher([work])
        .match("Four Impromptus", "Beethoven", catalogue="D.899 Op.91")
        .work_id
        is None
    )


def test_single_quoted_nickname_is_recognized_but_apostrophes_do_not_split_names():
    work = replace(
        BEETHOVEN,
        titles=("Symphony No. 1 in D major",),
        catalogue=None,
        aliases=("Titan",),
    )
    assert (
        matcher([work]).match("Symphony No. 1 in D Major 'Titan'", "Beethoven").work_id
        == work.id
    )


def test_polluted_sibling_catalogue_alias_cannot_override_specific_primary_code():
    work = replace(BEETHOVEN, catalogue="Op.30 No.3", aliases=("Sonata Op.30 No.2",))
    assert (
        matcher([work]).match("Sonata", "Beethoven", catalogue="Op.30 No.2").work_id
        is None
    )


def test_catalogue_cannot_override_explicitly_conflicting_work_genre():
    assert (
        matcher([BEETHOVEN])
        .match("Piano Concerto", "Beethoven", catalogue="Op.30 No.3")
        .work_id
        is None
    )


@pytest.mark.parametrize(
    "title", ["Violin Sonata K. 301 / 293a", "Violin Sonata K.301 (293a)"]
)
def test_koechel_alternate_numbers_require_both_numbers_in_catalogue(title):
    work = CanonicalWork("w", "w", ("Violin Sonata",), ("Mozart",), "K.301; K.293a")
    assert MusicMatcher([work]).match(title, "Mozart").work_id == "w"
    wrong = CanonicalWork("x", "x", ("Violin Sonata",), ("Mozart",), "K.301")
    assert MusicMatcher([wrong]).match(title, "Mozart").work_id is None


def test_different_koechel_alternate_is_not_ignored():
    work = CanonicalWork("w", "w", ("Violin Sonata",), ("Mozart",), "K.301; K.293a")
    assert (
        MusicMatcher([work]).match("Violin Sonata K.301/293b", "Mozart").work_id is None
    )


def test_opus_slash_still_means_member_not_alternate_number():
    work = CanonicalWork("w", "w", ("Sonata",), ("Beethoven",), "Op.102 No.2")
    assert MusicMatcher([work]).match("Sonata Op.102/2", "Beethoven").work_id == "w"


def test_catalogue_number_cannot_turn_an_overture_into_an_unrelated_aria():
    m = MusicMatcher(
        [
            CanonicalWork(
                "aria",
                "aria",
                ("Welche Wonne, welche Lust",),
                ("Wolfgang Amadeus Mozart",),
                "K.384",
            )
        ]
    )
    assert (
        m.match(
            "Die Entführung aus dem Serail, K.384: Overture", "Mozart", scoped=True
        ).work_id
        is None
    )


def test_catalogue_number_with_conflicting_genre_is_not_sufficient():
    m = MusicMatcher(
        [CanonicalWork("pc", "pc", ("Piano Concerto",), ("Samuel Barber",), "Op.38")]
    )
    assert (
        m.match("Canzone for Flute and Piano, Op.38", "Samuel Barber").work_id is None
    )


def test_composer_can_omit_first_given_name_but_not_change_it():
    m = MusicMatcher(
        [CanonicalWork("h", "h", ("Example",), ("Franz Joseph Haydn",), "Op.1")]
    )
    assert m.match("Example Op.1", "Joseph Haydn").work_id == "h"
    assert m.match("Example Op.1", "J. Haydn").work_id == "h"
    assert m.match("Example Op.1", "Michael Haydn").work_id is None


def test_overture_catalogue_with_an_explicit_overture_alias_is_supported():
    m = MusicMatcher(
        [
            CanonicalWork(
                "m",
                "m",
                ("A Midsummer Night's Dream",),
                ("Felix Mendelssohn",),
                "Op.21",
                ("A Midsummer Night's Dream Overture",),
            )
        ]
    )
    assert m.match("Overture to , Op.21", "Mendelssohn", scoped=True).work_id == "m"
