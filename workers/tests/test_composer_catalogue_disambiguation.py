from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


def work(id, composer, catalogue, title="Orchestral Suite No. 3 in D major"):
    return CanonicalWork(id, id, (title,), composer, catalogue, ())


def test_bach_family_is_resolved_by_bwv_with_existing_title_guards():
    matcher = MusicMatcher([
        work("js", ("Johann Sebastian Bach", "바흐"), "BWV 1068"),
        work("cpe", ("Carl Philipp Emanuel Bach", "바흐"), "Wq. 183"),
    ])
    match = matcher.match('Air (Orchestral Suite No. 3 in D major, BWV 1068)', "바흐", scoped=True)
    assert (match.work_id, match.reason) == ("js", "composer_and_catalogue")
    assert matcher.match("Orchestral Suite No. 4 in D major", "바흐", catalogue="BWV 1068").work_id is None
    assert matcher.match("Orchestral Suite No. 3 in C minor", "바흐", catalogue="BWV 1068").work_id is None


def test_shared_catalogue_and_generic_opus_do_not_disambiguate_a_family():
    for catalogue in ("Op. 18", "BWV 1068"):
        matcher = MusicMatcher([
            work("a", ("Johann Sebastian Bach",), catalogue),
            work("b", ("Carl Philipp Emanuel Bach",), catalogue),
        ])
        assert matcher.match("Orchestral Suite No. 3", "Bach", catalogue=catalogue).work_id is None
    matcher = MusicMatcher([
        work("a", ("Johann Strauss",), "Op. 18"),
        work("b", ("Richard Strauss",), "Op. 20"),
    ])
    assert matcher.match("Orchestral Suite No. 3", "Strauss", catalogue="Op. 18").work_id is None
    assert matcher.match("Ave Maria", None).work_id is None
