from classic_hubble_pipeline.normalizer import normalize_work_candidate


def test_normalize_korean_shorthand_alias():
    result = normalize_work_candidate("라흐 피협 2번")

    assert result["work_slug"] == "rachmaninoff-piano-concerto-2"
    assert result["confidence"] >= 0.8


def test_unknown_work_returns_review_candidate():
    result = normalize_work_candidate("작곡가 미상 환상곡")

    assert result["work_slug"] is None
    assert result["review_required"] is True
