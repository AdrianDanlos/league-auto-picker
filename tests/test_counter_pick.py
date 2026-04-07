from features import select_champion_logic
from features.pick_and_ban import _get_active_pick, _next_cycle_position


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


def test_get_ranked_counter_candidates_matches_enemy_case_insensitively(monkeypatch):
    monkeypatch.setattr(
        select_champion_logic,
        "is_champion_available",
        _always_available,
    )

    lane_picks_config = {
        "Kassadin": ["leblanc", "Azir"],
    }
    enemy_champions = ["LeBlanc"]

    ranked = select_champion_logic.get_ranked_counter_candidates(
        enemy_champions,
        lane_picks_config,
        ally_champion_ids=set(),
        banned_champions_ids=[],
        champion_ids={},
    )

    assert ranked == ["Kassadin"]


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


def test_build_pick_candidates_uses_counters_only_when_available(monkeypatch):
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

    assert candidates == ["Diana", "Ahri"]


def test_build_pick_candidates_falls_back_to_defaults_when_no_counters(monkeypatch):
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
        enemy_champions=["Zed"],
        lane_picks_config=config["picks"]["MIDDLE"],
        ally_champion_ids=set(),
        banned_champions_ids=[],
        champion_ids={},
    )

    assert candidates == ["Ahri", "Viktor", "Swain"]


def test_build_pick_candidate_sources_creates_one_list_per_enemy(monkeypatch):
    monkeypatch.setattr(
        select_champion_logic,
        "is_champion_available",
        _always_available,
    )

    config = {
        "picks": {
            "MIDDLE": {
                "Diana": ["Yone", "Annie"],
                "Ahri": ["Annie"],
                "Fizz": ["Yone"],
            },
            "DEFAULT": {
                "MIDDLE": ["Ahri", "Viktor", "Swain"],
            },
        }
    }

    candidate_sources = select_champion_logic.build_pick_candidate_sources(
        config=config,
        lane_key="MIDDLE",
        enemy_champions=["Yone", "Annie"],
        lane_picks_config=config["picks"]["MIDDLE"],
        ally_champion_ids=set(),
        banned_champions_ids=[],
        champion_ids={},
    )

    assert candidate_sources == [
        {"source_enemy": "Yone", "candidates": ["Diana", "Fizz"]},
        {"source_enemy": "Annie", "candidates": ["Ahri", "Diana"]},
    ]


def test_build_pick_candidate_sources_falls_back_to_default_source(monkeypatch):
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

    candidate_sources = select_champion_logic.build_pick_candidate_sources(
        config=config,
        lane_key="MIDDLE",
        enemy_champions=["Zed"],
        lane_picks_config=config["picks"]["MIDDLE"],
        ally_champion_ids=set(),
        banned_champions_ids=[],
        champion_ids={},
    )

    assert candidate_sources == [
        {"source_enemy": "DEFAULT", "candidates": ["Ahri", "Viktor", "Swain"]}
    ]


def test_cycle_position_moves_within_list_then_to_next_list():
    candidate_sources = [
        {"source_enemy": "Yone", "candidates": ["Diana", "Fizz"]},
        {"source_enemy": "Annie", "candidates": ["Ahri", "Diana"]},
    ]

    source_idx, candidate_idx = _next_cycle_position(candidate_sources, 0, 0)
    assert (source_idx, candidate_idx) == (0, 1)

    source_idx, candidate_idx = _next_cycle_position(candidate_sources, source_idx, candidate_idx)
    assert (source_idx, candidate_idx) == (1, 0)

    source_idx, candidate_idx = _next_cycle_position(candidate_sources, source_idx, candidate_idx)
    assert (source_idx, candidate_idx) == (1, 1)

    source_idx, candidate_idx = _next_cycle_position(candidate_sources, source_idx, candidate_idx)
    assert (source_idx, candidate_idx) == (0, 0)


def test_get_active_pick_returns_source_and_position():
    candidate_sources = [
        {"source_enemy": "Yone", "candidates": ["Diana", "Fizz"]},
        {"source_enemy": "Annie", "candidates": ["Ahri"]},
    ]

    pick, source_enemy, source_idx, candidate_idx = _get_active_pick(
        candidate_sources, 1, 0
    )
    assert pick == "Ahri"
    assert source_enemy == "Annie"
    assert source_idx == 1
    assert candidate_idx == 0
