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


@pytest.fixture
def mazurka_collection_and_member():
    collection = CanonicalWork("set", "set", ("Mazurkas, Op. 17",), ("Chopin",), "Op. 17", ("4 Mazurkas, Op. 17",))
    member = CanonicalWork(
        "member", "member", ("Mazurka no. 13 in A minor, op. 17 no. 4",),
        ("Chopin",), None, ("Mazurkas, piano, op. 17. No. 4",),
    )
    return collection, member


def test_collection_number_does_not_leak_from_member_alias(mazurka_collection_and_member):
    assert matcher(mazurka_collection_and_member).match("4 Mazurkas", "Chopin", catalogue="Op.17").work_id == "set"


def test_collection_without_collection_row_does_not_become_member(mazurka_collection_and_member):
    assert matcher([mazurka_collection_and_member[1]]).match("4 Mazurkas", "Chopin", catalogue="Op.17").work_id is None


def test_exact_member_from_primary_title_remains_matchable(mazurka_collection_and_member):
    assert matcher(mazurka_collection_and_member).match("Mazurka in A minor", "Chopin", catalogue="Op.17 No.4", key="A minor").work_id == "member"


@pytest.mark.parametrize("code", ["Op.17 No.3", "Op.18 No.4"])
def test_primary_title_member_does_not_allow_different_number(mazurka_collection_and_member, code):
    assert matcher([mazurka_collection_and_member[1]]).match("Mazurka", "Chopin", catalogue=code).work_id is None


def test_member_guard_preserves_duplicate_collection_ambiguity(mazurka_collection_and_member):
    collection, member = mazurka_collection_and_member
    result = matcher([collection, member, replace(collection, id="duplicate")]).match("4 Mazurkas", "Chopin", catalogue="Op.17")
    assert result.work_id is None
    assert result.reason == "ambiguous"


def test_member_guard_keeps_composer_conflicts_blocked(mazurka_collection_and_member):
    assert matcher(mazurka_collection_and_member).match("4 Mazurkas", "Schumann", catalogue="Op.17").work_id is None


def test_member_guard_does_not_promote_unreviewed_catalogue(mazurka_collection_and_member):
    works = [replace(w, requires_review=True) for w in mazurka_collection_and_member]
    result = matcher(works).match("4 Mazurkas", "Chopin", catalogue="Op.17")
    assert result.work_id is None
    assert result.reason == "catalog_review_required"


@pytest.mark.parametrize("composer", ["S. Rachmaninov", "S.Rachmaninov", "Sergei Rachmaninov", "Rachmaninov"])
def test_publisher_verified_rachmaninov_form_retains_identity(composer):
    work = CanonicalWork("r", "r", ("Piano Sonata No. 1 in D minor",), ("Sergei Rachmaninoff",), "Op.28")
    assert matcher([work]).match("Piano Sonata No. 1 in d minor", composer, catalogue="Op.28").work_id == "r"


@pytest.mark.parametrize("composer", ["A. Rachmaninov", "Rachmaninof", "S. Rachmaninof"])
def test_rachmaninov_form_does_not_accept_wrong_initial_or_unverified_typo(composer):
    work = CanonicalWork("r", "r", ("Piano Sonata No. 1 in D minor",), ("Sergei Rachmaninoff",), "Op.28")
    assert matcher([work]).match("Piano Sonata No. 1 in d minor", composer, catalogue="Op.28").work_id is None


def test_rachmaninov_alias_keeps_catalogue_conflicts_blocked():
    work = CanonicalWork("r", "r", ("Piano Sonata No. 1 in D minor",), ("Sergei Rachmaninoff",), "Op.28")
    assert matcher([work]).match(work.titles[0], "S.Rachmaninov", catalogue="Op.29").work_id is None


@pytest.fixture
def tchaikovsky_violin_concerto():
    return CanonicalWork(
        "tchaikovsky-op35", "tchaikovsky-op35", ("Violin Concerto in D major",),
        ("Pyotr Ilyich Tchaikovsky",), "Op.35",
    )


@pytest.mark.parametrize("composer", [
    "Peter Ilyich Tchaikovsky", "PETER ILYICH TCHAIKOVSKY", "Pyotr Ilyich Tchaikovsky",
])
def test_publisher_verified_peter_tchaikovsky_form(composer, tchaikovsky_violin_concerto):
    work = tchaikovsky_violin_concerto
    assert matcher([work]).match(work.titles[0], composer, catalogue="Op.35").work_id == work.id


@pytest.mark.parametrize("composer", ["Paul Ilyich Tchaikovsky", "Peter Ilyich Tchaikovskv", "A. I. Tchaikovsky"])
def test_peter_tchaikovsky_form_rejects_unverified_names(composer, tchaikovsky_violin_concerto):
    work = tchaikovsky_violin_concerto
    assert matcher([work]).match(work.titles[0], composer, catalogue="Op.35").work_id is None


@pytest.mark.parametrize("catalogue,key", [("Op.36", "D major"), ("Op.35", "D minor")])
def test_peter_tchaikovsky_form_preserves_identity_conflicts(catalogue, key, tchaikovsky_violin_concerto):
    work = tchaikovsky_violin_concerto
    assert matcher([work]).match(
        work.titles[0], "Peter Ilyich Tchaikovsky", catalogue=catalogue, key=key,
    ).work_id is None


def test_peter_tchaikovsky_form_preserves_duplicate_ambiguity(tchaikovsky_violin_concerto):
    work = tchaikovsky_violin_concerto
    result = matcher([work, replace(work, id="duplicate")]).match(
        work.titles[0], "Peter Ilyich Tchaikovsky", catalogue="Op.35",
    )
    assert result.work_id is None
    assert result.reason == "ambiguous"


def test_peter_tchaikovsky_form_preserves_catalogue_review(tchaikovsky_violin_concerto):
    work = replace(tchaikovsky_violin_concerto, requires_review=True)
    result = matcher([work]).match(work.titles[0], "Peter Ilyich Tchaikovsky", catalogue="Op.35")
    assert result.work_id is None
    assert result.reason == "catalog_review_required"


@pytest.mark.parametrize("title", ["Suite for Violin and Piano", "Violin Suite", "바이올린 모음곡", "Suite for Piano"])
def test_suite_catalogue_does_not_override_explicit_instrument_conflict(title):
    work = CanonicalWork("w", "w", ("Suite for Flute and Piano",), ("Charles-Marie Widor",), "Op.34")
    assert matcher([work]).match(title, "C.M.Widor", catalogue="Op.34").work_id is None


@pytest.mark.parametrize("title", ["Suite for Flute and Piano", "Flute Suite", "플루트 모음곡", "Suite"])
def test_suite_instrument_guard_allows_agreement_or_omission(title):
    work = CanonicalWork("w", "w", ("Suite for Flute and Piano",), ("Charles-Marie Widor",), "Op.34")
    assert matcher([work]).match(title, "C.M.Widor", catalogue="Op.34").work_id == "w"


def test_suite_instrument_guard_uses_primary_title_not_conflicting_alias():
    work = CanonicalWork(
        "w", "w", ("Suite for Flute and Piano",), ("Charles-Marie Widor",), "Op.34", ("Violin Suite",),
    )
    assert matcher([work]).match("Violin Suite", "C.M.Widor", catalogue="Op.34").work_id is None


@pytest.mark.parametrize("title", ["Allegro con brio", "IV. Finale", "4. Allegro con brio"])
@pytest.mark.parametrize("composer", [None, "Ludwig van Beethoven"])
def test_bare_movement_labels_do_not_identify_unrelated_component(title, composer):
    work = CanonicalWork(
        "component", "component", (title,), ("Ludwig van Beethoven",), None,
    )
    assert matcher([work]).match(title, composer).work_id is None


def test_tempo_title_with_explicit_catalogue_can_still_identify_work():
    work = CanonicalWork("w", "w", ("Allegro con brio",), ("Beethoven",), "Op. 22")
    assert matcher([work]).match("Allegro con brio", "Beethoven", catalogue="Op. 22").work_id == "w"


@pytest.mark.parametrize("title", ["Adagio for Strings", "Adagio and Allegro", "Finale from The Firebird"])
def test_named_work_not_reduced_to_bare_movement_label(title):
    work = CanonicalWork("w", "w", (title,), ("Example Composer",), None)
    assert matcher([work]).match(title, "Example Composer").work_id == "w"


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


@pytest.mark.parametrize("code", ["FWV 21", "FWV.21", "FwV21"])
def test_franck_fwv_matches_explicit_canonical_identity(code):
    work = CanonicalWork(
        "franck", "franck", ("Prelude, Chorale and Fugue",),
        ("Cesar Franck",), "FWV 21",
    )
    assert matcher([work]).match(
        "Prelude, Choral et Fugue", "C. Franck", catalogue=code,
    ).work_id == work.id
    assert matcher([work]).match(
        "Prelude, Choral et Fugue " + code, "C. Franck",
    ).work_id == work.id


@pytest.mark.parametrize("code", [
    "FWV 22", "FWV 21; FWV 22", "FWV 21,1", "FWV 21/1",
    "FWV 21-22", "FWV 21.1", "FWV 21a",
])
def test_fwv_conflict_or_component_cannot_fall_back_to_exact_title(code):
    work = CanonicalWork("w", "w", ("Prelude, Choral et Fugue",), ("Cesar Franck",), "FWV 21")
    assert matcher([work]).match(work.titles[0], "C. Franck", catalogue=code).work_id is None
    assert matcher([work]).match(work.titles[0] + " " + code, "C. Franck").work_id is None


@pytest.mark.parametrize("composer", ["J. S. Bach", "A. Franck"])
def test_fwv_does_not_override_conflicting_composer(composer):
    work = CanonicalWork("w", "w", ("Prelude, Choral et Fugue",), ("Cesar Franck",), "FWV 21")
    assert matcher([work]).match(work.titles[0], composer, catalogue="FWV 21").work_id is None


def test_fwv_without_composer_retains_title_only_reason_not_composer_match():
    work = CanonicalWork("w", "w", ("Prelude, Choral et Fugue",), ("Cesar Franck",), "FWV 21")
    result = matcher([work]).match(work.titles[0], None, catalogue="FWV 21")
    assert result.reason == "unique_distinctive_title"


def test_fwv_requires_canonical_catalogue_evidence_and_leaves_legacy_unchanged():
    from classic_hubble_pipeline.work_matching import CATALOGUE
    work = CanonicalWork("w", "w", ("Prelude, Choral et Fugue",), ("Cesar Franck",), None)
    assert matcher([work]).match(work.titles[0], "C. Franck", catalogue="FWV 21").work_id is None
    assert CATALOGUE.search("FWV 21") is None


@pytest.mark.parametrize("code", ["M. 81", "M81", "m.81"])
def test_ravel_m_catalogue_matches_explicit_canonical_identity(code):
    work = CanonicalWork("ravel-bolero", "ravel-bolero", ("Boléro",), ("Maurice Ravel",), "M. 81")
    assert matcher([work]).match("Bolero", "M. Ravel", catalogue=code).work_id == work.id
    assert matcher([work]).match("Bolero " + code, "Maurice Ravel").work_id == work.id


@pytest.mark.parametrize("code", ["M. 82", "M. 81; M. 82", "M. 81,1", "M. 81/1", "M. 81-82", "M. 81.1", "M. 81a"])
def test_ravel_m_catalogue_conflicts_or_components_cannot_match_parent(code):
    work = CanonicalWork("w", "w", ("Bolero",), ("Maurice Ravel",), "M. 81")
    assert matcher([work]).match("Bolero", "Maurice Ravel", catalogue=code).work_id is None
    assert matcher([work]).match("Bolero " + code, "Maurice Ravel").work_id is None


def test_ravel_m_catalogue_does_not_override_conflicting_composer():
    work = CanonicalWork("w", "w", ("Bolero",), ("Maurice Ravel",), "M. 81")
    assert matcher([work]).match("Bolero", "Chopin", catalogue="M. 81").work_id is None


def test_ravel_m_catalogue_requires_canonical_evidence_and_leaves_legacy_unchanged():
    from classic_hubble_pipeline.work_matching import CATALOGUE
    work = CanonicalWork("w", "w", ("Bolero",), ("Maurice Ravel",), None)
    assert matcher([work]).match("Bolero", "Maurice Ravel", catalogue="M. 81").work_id is None
    assert CATALOGUE.search("M. 81") is None


def test_ravel_m_catalogue_without_composer_is_not_composer_grounded():
    work = CanonicalWork("w", "w", ("Bolero",), ("Maurice Ravel",), "M. 81")
    assert matcher([work]).match("Bolero", None, catalogue="M. 81").reason == "unique_distinctive_title"


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


@pytest.fixture
def korean_untyped_catalogue_work():
    return CanonicalWork(
        "mozart-k364", "mozart-k364", ("Sinfonia concertante in E-flat major",),
        ("Wolfgang Amadeus Mozart", "볼프강 아마데우스 모차르트"), "K. 364",
        ("신포니아 콘체르탄테",),
    )


@pytest.mark.parametrize("code", ["작품 364", "작품364", "작품번호 364"])
def test_untyped_catalogue_confirms_independently_matching_title(code, korean_untyped_catalogue_work):
    result = matcher([korean_untyped_catalogue_work]).match(
        "신포니아콘체르탄테 내림마장조", "모차르트", catalogue=code,
    )
    assert result.work_id == "mozart-k364"
    assert result.reason == "composer_and_alias"


def test_untyped_catalogue_label_embedded_in_title_is_still_checked(korean_untyped_catalogue_work):
    assert matcher([korean_untyped_catalogue_work]).match(
        "신포니아콘체르탄테 내림마장조작품 364", "모차르트", catalogue="작품 364",
    ).work_id == "mozart-k364"


@pytest.mark.parametrize("title,composer,code", [
    ("신포니아콘체르탄테", None, "작품 364"),
    ("신포니아콘체르탄테", "Beethoven", "작품 364"),
    ("신포니아콘체르탄테", "모차르트", "작품 365"),
    ("신포니아콘체르탄테 라장조", "모차르트", "작품 364"),
    ("신포니아콘체르탄테 작품 365", "모차르트", "작품 364"),
    ("신포니아콘체르탄테 K.365", "모차르트", "작품 364"),
    ("Unknown Work", "모차르트", "작품 364"),
    ("신포니아콘체르탄테", "모차르트", "작품 364/2"),
    ("신포니아콘체르탄테", "모차르트", "작품 364 No.2"),
])
def test_untyped_catalogue_never_overrides_evidence_conflicts(title, composer, code, korean_untyped_catalogue_work):
    assert matcher([korean_untyped_catalogue_work]).match(title, composer, catalogue=code).work_id is None


@pytest.mark.parametrize("catalogue", [None, "K.365", "K.364 No.1"])
def test_untyped_catalogue_needs_a_complete_primary_canonical_number(catalogue, korean_untyped_catalogue_work):
    work = replace(korean_untyped_catalogue_work, catalogue=catalogue)
    assert matcher([work]).match("신포니아콘체르탄테", "모차르트", catalogue="작품 364").work_id is None


def test_untyped_number_does_not_disambiguate_same_title(korean_untyped_catalogue_work):
    work = korean_untyped_catalogue_work
    other = replace(work, id="other", catalogue="K.297b")
    assert matcher([work, other]).match("신포니아콘체르탄테", "모차르트", catalogue="작품 364").work_id is None


def test_untyped_number_preserves_catalogue_review(korean_untyped_catalogue_work):
    work = replace(korean_untyped_catalogue_work, requires_review=True)
    result = matcher([work]).match("신포니아콘체르탄테", "모차르트", catalogue="작품 364")
    assert result.work_id is None and result.candidate_ids == (work.id,)
    assert result.reason == "catalog_review_required"


def test_untyped_number_cannot_use_a_generic_title():
    work = replace(BEETHOVEN, titles=("Sonata",), catalogue="Op.37", aliases=())
    assert matcher([work]).match("Sonata", "Beethoven", catalogue="작품 37").work_id is None


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


@pytest.mark.parametrize("title", ["Polonaise in A-Flat Major", "Polonaise", "폴로네즈 내림가장조"])
def test_generic_polonaise_namesake_cannot_contradict_explicit_opus(title):
    heroic = CanonicalWork(
        "heroic", "heroic", ('Polonaise in A-flat major "Heroic", Op. 53',),
        ("Frederic Chopin",), "Op. 53", ("Heroic Polonaise",),
    )
    early = replace(heroic, id="early", slug="early", catalogue=None,
                    titles=("Polonaise in A-flat major, B.5",), aliases=(title,))
    result = matcher([heroic, early]).match(title, "Chopin", catalogue="Op.53")
    assert result.work_id == heroic.id
    assert result.reason == "composer_and_catalogue"


@pytest.mark.parametrize("title", ["Polonaise in A-Flat Major", "Polonaise", "폴로네즈 내림가장조"])
def test_generic_polonaise_without_composer_is_not_unique_identity(title):
    work = CanonicalWork("w", "w", (title,), ("Frederic Chopin",), None)
    assert matcher([work]).match(title, None).work_id is None


def test_distinctive_heroic_name_still_rejects_wrong_catalogue():
    heroic = CanonicalWork("heroic", "heroic", ("Heroic Polonaise",), ("Chopin",), "Op.53")
    other = replace(heroic, id="other", slug="other", titles=("Another Polonaise",), catalogue="Op.26")
    result = matcher([heroic, other]).match("Heroic Polonaise", "Chopin", catalogue="Op.26")
    assert result.work_id is None
    assert result.reason == "title_catalogue_conflict"


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


@pytest.mark.parametrize("printed", [
    "요한 슈트라우스 2세", "요한슈트라우스2세", "요한 슈트라우스 2 세",
    "Johann Strauss II 요한 슈트라우스 2세 (1825-1899)",
])
def test_korean_strauss_generation_survives_composer_segmentation(printed):
    work = replace(BEETHOVEN, composers=("Johann Strauss Jr", "요한 슈트라우스 2세"),
                   titles=("Frühlingsstimmen", "봄의 소리"), catalogue="Op. 410", aliases=())
    assert matcher([work]).match("봄의 소리", printed, catalogue="Op. 410").work_id == work.id


@pytest.mark.parametrize("printed", [
    "요한 슈트라우스 1세", "요한 슈트라우스 3세", "요한 슈트라우스 4세",
    "요한슈트라우스1세", "요한슈트라우스3세",
])
def test_korean_strauss_generation_never_falls_back_to_unqualified_name(printed):
    son = replace(BEETHOVEN, composers=("Johann Strauss Jr", "요한 슈트라우스 2세"),
                  titles=("Frühlingsstimmen", "봄의 소리"), catalogue="Op. 410", aliases=())
    unqualified = replace(son, id="unqualified", composers=("Johann Strauss", "요한 슈트라우스"))
    assert matcher([son, unqualified]).match("봄의 소리", printed, catalogue="Op. 410").work_id is None


def test_korean_strauss_bilingual_generation_conflict_is_not_discarded():
    son = replace(BEETHOVEN, composers=("Johann Strauss Jr", "요한 슈트라우스 2세"),
                  titles=("Frühlingsstimmen", "봄의 소리"), catalogue="Op. 410", aliases=())
    father = replace(son, id="father", composers=("Johann Strauss I", "요한 슈트라우스 1세"))
    result = matcher([son, father]).match("봄의 소리", "Johann Strauss I 요한 슈트라우스 2세")
    assert result.work_id is None
    assert result.reason == "conflicting_composers"


def test_korean_strauss_generation_keeps_catalogue_and_duplicate_guards():
    son = replace(BEETHOVEN, composers=("Johann Strauss Jr", "요한 슈트라우스 2세"),
                  titles=("Frühlingsstimmen", "봄의 소리"), catalogue="Op. 410", aliases=())
    assert matcher([son]).match("봄의 소리", "요한 슈트라우스 2세", catalogue="Op. 411").work_id is None
    assert matcher([son, replace(son, id="duplicate")]).match(
        "봄의 소리", "요한 슈트라우스 2세", catalogue="Op. 410",
    ).work_id is None


@pytest.mark.parametrize("printed", ["J. Strauss II", "J.Strauss II", "J. Strauß II", "J. Strauss Jr."])
def test_initial_strauss_generation_matches_existing_blue_danube(printed):
    work = replace(BEETHOVEN, composers=("Johann Strauss Jr",),
                   titles=("The Blue Danube in D major",), catalogue="Op.314",
                   aliases=("An der schönen blauen Donau",))
    result = matcher([work]).match("An der schönen, blauen Donau", printed, catalogue="Op.314")
    assert result.work_id == work.id


@pytest.mark.parametrize("printed,canonical", [
    ("J. Strauss I", "Johann Strauss II"),
    ("J. Strauss I", "Johann Strauss Jr"),
    ("J. Strauss III", "Johann Strauss Jr"),
    ("J. Strauss II", "Johann Strauss I"),
    ("J. Strauss II", "Josef Strauss"),
    ("J. Strauss II", "Richard Strauss"),
    ("J. Strauss II", "Johann Strauss"),
    ("R. Strauss II", "Johann Strauss Jr"),
])
def test_initial_strauss_generation_never_expands_roman_numeral(printed, canonical):
    work = replace(BEETHOVEN, composers=(canonical,),
                   titles=("The Blue Danube",), catalogue="Op.314", aliases=())
    assert matcher([work]).match("The Blue Danube", printed, catalogue="Op.314").work_id is None


def test_initial_strauss_generation_keeps_catalogue_and_duplicate_guards():
    work = replace(BEETHOVEN, composers=("Johann Strauss Jr",),
                   titles=("The Blue Danube",), catalogue="Op.314", aliases=())
    assert matcher([work]).match("The Blue Danube", "J. Strauss II", catalogue="Op.315").work_id is None
    assert matcher([work, replace(work, id="duplicate")]).match(
        "The Blue Danube", "J. Strauss II", catalogue="Op.314",
    ).work_id is None


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


@pytest.mark.parametrize("printed", ["세르게이 프로코피에프", "세르게이프로코피에프"])
def test_verified_prokofiev_korean_name_matches_printed_catalogue(printed):
    work = CanonicalWork(
        "prokofiev", "prokofiev", ("Symphony No. 1 in D major",),
        ("Sergei Prokofiev", "세르게이 프로코피예프"), "Op.25",
    )
    result = matcher([work]).match(
        "Symphony No.1 in D major, Op.25", printed,
    )
    assert result.work_id == "prokofiev"
    assert result.reason == "composer_and_catalogue"


def test_verified_prokofiev_name_does_not_hide_bilingual_conflict():
    work = replace(BEETHOVEN, id="prokofiev", composers=("Sergei Prokofiev",))
    result = matcher([work, BEETHOVEN]).match(
        "Op.30 No.3", "세르게이 프로코피에프 Ludwig van Beethoven",
    )
    assert result.work_id is None
    assert result.reason == "conflicting_composers"


def test_unverified_prokofiev_korean_typo_stays_unmatched():
    work = replace(BEETHOVEN, id="prokofiev", composers=("Sergei Prokofiev",))
    result = matcher([work]).match("Op.30 No.3", "세르게이 프로코피에푸")
    assert result.work_id is None


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


@pytest.fixture
def brahms_clarinet_sonatas():
    return [CanonicalWork(
        f"brahms-{number}", f"brahms-{number}",
        (f"Sonata for Clarinet and Piano no. {number} in {key}",),
        ("Johannes Brahms",), f"Op. 120 No. {number}",
    ) for number, key in [(1, "F minor"), (2, "E-flat major")]]


@pytest.mark.parametrize("number,key", [(1, "f minor"), (2, "E-flat Major")])
def test_numbered_sonata_primary_title_and_key_disambiguate_opus_root(brahms_clarinet_sonatas, number, key):
    result = matcher(brahms_clarinet_sonatas).match(
        f"Sonata for Clarinet and Piano No.{number}", "J.Brahms", catalogue="Op. 120", key=key,
    )
    assert result.work_id == f"brahms-{number}"
    assert result.reason == "composer_and_catalogue"


@pytest.mark.parametrize("title,composer,code,key", [
    ("Sonata for Clarinet and Piano", "J.Brahms", "Op.120", "E-flat Major"),
    ("Sonata for Clarinet and Piano No.2", "J.Brahms", "Op.120", None),
    ("Sonata for Clarinet and Piano No.2", None, "Op.120", "E-flat Major"),
    ("Sonata for Clarinet and Piano No.2", "J.Brahms", "Op.120", "F minor"),
    ("Sonata for Clarinet and Piano No.2", "J.Brahms", "Op.120 No.1", "E-flat Major"),
    ("Sonata for Clarinet and Piano No.2", "J.Brahms", "Op.121", "E-flat Major"),
    ("Sonata for Clarinet and Piano No.2", "J.Brahms", "Op.120; Op.121", "E-flat Major"),
    ("Sonatas for Clarinet and Piano No.1, No.2", "J.Brahms", "Op.120", "E-flat Major"),
    ("Sonata for Viola and Piano No.2", "J.Brahms", "Op.120", "E-flat Major"),
    ('Other Sonata No.2 "Sonata for Clarinet and Piano No.2"', "J.Brahms", "Op.120", "E-flat Major"),
])
def test_opus_root_needs_complete_uncontradicted_primary_identity(brahms_clarinet_sonatas, title, composer, code, key):
    assert matcher(brahms_clarinet_sonatas).match(title, composer, catalogue=code, key=key).work_id is None


def test_opus_root_does_not_use_alias_to_supply_specific_number(brahms_clarinet_sonatas):
    work = replace(brahms_clarinet_sonatas[1], titles=("Sonata in E-flat major",), aliases=brahms_clarinet_sonatas[1].titles)
    assert matcher([work]).match("Sonata for Clarinet and Piano No.2", "J.Brahms", catalogue="Op.120", key="E-flat Major").work_id is None


def test_opus_root_does_not_resolve_duplicate_primary_identities(brahms_clarinet_sonatas):
    work = brahms_clarinet_sonatas[1]
    duplicate = replace(work, id="other", slug="other")
    assert matcher([work, duplicate]).match("Sonata for Clarinet and Piano No.2", "J.Brahms", catalogue="Op.120", key="E-flat Major").work_id is None


def test_opus_root_does_not_promote_scoped_or_unreviewed_work(brahms_clarinet_sonatas):
    work = brahms_clarinet_sonatas[1]
    assert matcher([work]).match("Sonata for Clarinet and Piano No.2", "J.Brahms", catalogue="Op.120", key="E-flat Major", scoped=True).work_id is None
    assert matcher([replace(work, requires_review=True)]).match("Sonata for Clarinet and Piano No.2", "J.Brahms", catalogue="Op.120", key="E-flat Major").work_id is None


@pytest.fixture
def medtner_named_piece():
    return CanonicalWork(
        "medtner-round", "medtner-round", ("Russian Round Dance",),
        ("Nikolai Medtner",), "Op.58 No.1",
    )


@pytest.mark.parametrize("title", ["Russian Round Dance", "Russian Round Dance, Op. 58"])
def test_named_primary_piece_can_identify_omitted_opus_member(medtner_named_piece, title):
    result = matcher([medtner_named_piece]).match(title, "N. Medtner", catalogue="Op.58")
    assert result.work_id == medtner_named_piece.id
    assert result.reason == "composer_and_catalogue"


@pytest.mark.parametrize("title,composer,code", [
    ("Round Dance", "N. Medtner", "Op.58"),
    ('Other piece "Russian Round Dance"', "N. Medtner", "Op.58"),
    ("Russian Round Dance", None, "Op.58"),
    ("Russian Round Dance", "Other Composer", "Op.58"),
    ("Russian Round Dance", "N. Medtner", "Op.59"),
    ("Russian Round Dance", "N. Medtner", "Op.58 No.2"),
    ("Russian Round Dance", "N. Medtner", "Op.58; Op.59"),
    ("Russian Round Dance No.2", "N. Medtner", "Op.58"),
])
def test_named_opus_member_requires_complete_primary_identity(medtner_named_piece, title, composer, code):
    assert matcher([medtner_named_piece]).match(title, composer, catalogue=code).work_id is None


@pytest.mark.parametrize("title", [
    "Three Pieces", "2 Dances", "Two Character Pieces", "Dances", "Songs",
    "Sonata for Clarinet and Piano No.2", "Romance", "Andante",
])
def test_generic_or_counted_primary_name_does_not_supply_opus_member(medtner_named_piece, title):
    work = replace(medtner_named_piece, titles=(title,))
    assert matcher([work]).match(title, "N. Medtner", catalogue="Op.58").work_id is None


def test_named_opus_member_ignores_alias_identity(medtner_named_piece):
    work = replace(medtner_named_piece, titles=("Two Pieces",), aliases=medtner_named_piece.titles)
    assert matcher([work]).match("Russian Round Dance", "N. Medtner", catalogue="Op.58").work_id is None


@pytest.mark.parametrize("changes,composer", [
    ({"catalogue": "Op.58 No.2"}, "N. Medtner"),
    ({"composers": ("Other Composer",)}, "Other Composer"),
    ({"catalogue": "Op.59 No.1"}, "N. Medtner"),
])
def test_named_opus_member_requires_source_verified_canonical_identity(medtner_named_piece, changes, composer):
    work = replace(medtner_named_piece, **changes)
    assert matcher([work]).match("Russian Round Dance", composer, catalogue="Op.58").work_id is None


def test_named_opus_member_does_not_discard_conflicting_primary_number(medtner_named_piece):
    work = replace(medtner_named_piece, titles=("Russian Round Dance, Op.58 No.2",))
    assert matcher([work]).match("Russian Round Dance", "N. Medtner", catalogue="Op.58").work_id is None


def test_named_opus_member_does_not_verify_an_unknown_key(medtner_named_piece):
    assert matcher([medtner_named_piece]).match("Russian Round Dance", "N. Medtner", catalogue="Op.58", key="C minor").work_id is None


def test_named_opus_member_does_not_resolve_duplicate_primary_rows(medtner_named_piece):
    duplicate = replace(medtner_named_piece, id="duplicate", slug="duplicate")
    assert matcher([medtner_named_piece, duplicate]).match("Russian Round Dance", "N. Medtner", catalogue="Op.58").work_id is None


def test_named_opus_member_still_holds_scoped_and_review_required(medtner_named_piece):
    assert matcher([medtner_named_piece]).match("Russian Round Dance", "N. Medtner", catalogue="Op.58", scoped=True).work_id is None
    work = replace(medtner_named_piece, requires_review=True)
    assert matcher([work]).match("Russian Round Dance", "N. Medtner", catalogue="Op.58").work_id is None


def test_named_opus_member_does_not_hide_parent_collection_ambiguity(medtner_named_piece):
    parent = replace(medtner_named_piece, id="collection", slug="collection", titles=("Two Pieces",), catalogue="Op.58")
    result = matcher([medtner_named_piece, parent]).match("Russian Round Dance, Op.58", "N. Medtner")
    assert result.work_id is None
    assert result.reason == "ambiguous"


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
