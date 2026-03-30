from features import select_champion_logic


def _always_available(*_args, **_kwargs):
    return True


def test_get_ranked_counter_candidates_orders_globally(monkeypatch):
    monkeypatch.setattr(
        select_champion_logic,
        "is_champion_available",
        _always_available,
    )

    lane_picks_config = {
        "Diana": ["Yone", "Annie"],
        "Ahri": ["Annie", "Yone"],
        "Fizz": ["Yone"],
    }
    enemy_champions = ["Yone", "Annie"]

    ranked = select_champion_logic.get_ranked_counter_candidates(
        enemy_champions,
        lane_picks_config,
        ally_champion_ids=set(),
        banned_champions_ids=[],
        champion_ids={},
    )

    assert ranked == ["Diana", "Fizz", "Ahri"]


def test_get_ranked_counter_candidates_dedupes_candidates(monkeypatch):
    monkeypatch.setattr(
        select_champion_logic,
        "is_champion_available",
        _always_available,
    )

    lane_picks_config = {
        "Diana": ["Yone", "Annie"],
        "Ahri": ["Annie"],
    }
    enemy_champions = ["Yone", "Annie"]

    ranked = select_champion_logic.get_ranked_counter_candidates(
        enemy_champions,
        lane_picks_config,
        ally_champion_ids=set(),
        banned_champions_ids=[],
        champion_ids={},
    )

    assert ranked == ["Diana", "Ahri"]


def test_build_pick_candidates_appends_default_tail_in_order(monkeypatch):
    monkeypatch.setattr(
        select_champion_logic,
        "is_champion_available",
        _always_available,
    )

    config = {
        "picks": {
            "MIDDLE": {
                "Diana": ["Yone"],
                "Ahri": ["Yone"],
            },
            "DEFAULT": {
                "MIDDLE": ["Ahri", "Viktor", "Swain"],
            },
        }
    }

    candidates = select_champion_logic.build_pick_candidates(
        config=config,
        lane_key="MIDDLE",
        enemy_champions=["Yone"],
        lane_picks_config=config["picks"]["MIDDLE"],
        ally_champion_ids=set(),
        banned_champions_ids=[],
        champion_ids={},
    )

    # Ahri appears in counters and defaults; it should appear only once.
    assert candidates == ["Diana", "Ahri", "Viktor", "Swain"]
