from classic_hubble_pipeline.component_inventory import inventory


def test_inventory_accounts_for_every_work_and_holds_conflicting_album_names():
    work = {
        "id": "parent",
        "slug": "parent",
        "composer_id": "composer",
        "title": "Waldszenen",
        "catalogue": "Op. 82",
    }
    source = {"url": "https://example.org/program", "sha256": "a" * 64}
    catalog = {
        "works": [work],
        "composers": [{"id": "composer", "name": "Robert Schumann"}],
        "links": [],
        "work_aliases": [],
    }
    manual = {
        "parent_slug": "parent",
        "expected_parent_title": "Waldszenen",
        "expected_composer": "Robert Schumann",
        "source": source,
        "parts": [{"position": 1, "title": "Entry", "title_ko": "입구"}],
    }
    part = {
        "parent_key": "waldszenen",
        "parent_title_en": "Waldszenen, Op. 82",
        "parent_title_ko": "숲의 정경, Op. 82",
        "composer": "Robert Schumann",
        "position": 3,
        "title_en": "Name A",
        "title_ko": None,
        "sources": [source],
    }
    result = inventory(catalog, {}, [part, {**part, "title_en": "Name B"}], manual)
    assert result["audit"]["summary"]["existing_works_checked"] == 1
    assert len(result["audit"]["works"]) == 1
    assert [r["position"] for r in result["plan"]["relations"]] == [1]

    single = inventory(catalog, {}, [part], manual)
    assert [r["position"] for r in single["plan"]["relations"]] == [1]
    corroborated = [
        {
            **part,
            "sources": [
                {**source, "url": f"https://classical.music.apple.com/us/album/{i}"}
            ],
        }
        for i in (123, 456)
    ]
    double = inventory(catalog, {}, corroborated, manual)
    assert [r["position"] for r in double["plan"]["relations"]] == [1, 3]
