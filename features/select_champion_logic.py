import random
from utils.logger import log_and_discord
from utils import is_champion_available


def _counter_list_index_for_enemy(counter_list, enemy_champ):
    """Return list index where an entry matches enemy_champ case-insensitively, or None."""
    if not counter_list or enemy_champ is None:
        return None
    target = str(enemy_champ).casefold()
    for i, name in enumerate(counter_list):
        if str(name).casefold() == target:
            return i
    return None


def _merge_candidates(ranked_counter_candidates, default_candidates):
    """Merge candidates preserving order and removing duplicates."""
    merged_candidates = []
    seen = set()
    for champ in ranked_counter_candidates + default_candidates:
        if champ in seen:
            continue
        seen.add(champ)
        merged_candidates.append(champ)
    return merged_candidates


def get_counter_candidate_lists(
    enemy_champions,
    lane_picks_config,
    ally_champion_ids,
    banned_champions_ids,
    champion_ids,
    owned_champion_ids=None,
):
    """Return ordered counter candidate lists keyed by source enemy champion."""
    if not enemy_champions:
        return []

    counter_candidate_lists = []
    for enemy_order, enemy_champ in enumerate(enemy_champions):
        print(f"Checking enemy champion: {enemy_champ}")
        ranked_hits = []
        for counter_order, (counter_champ, counter_list) in enumerate(
            lane_picks_config.items()
        ):
            enemy_index = _counter_list_index_for_enemy(counter_list, enemy_champ)
            if enemy_index is None:
                continue

            try:
                if not is_champion_available(
                    counter_champ,
                    ally_champion_ids,
                    banned_champions_ids,
                    enemy_champions,
                    champion_ids,
                    owned_champion_ids,
                ):
                    print(
                        f"Skipping {counter_champ} - not available (ownership, prepicked, banned, or picked by enemies)"
                    )
                    continue
                ranked_hits.append((enemy_index, enemy_order, counter_order, counter_champ))
            except Exception as e:
                log_and_discord(
                    f"⚠️ Error in is_champion_available for {counter_champ}: {e}"
                )
                continue

        ranked_hits.sort(key=lambda item: (item[0], item[1], item[2]))
        ranked_candidates = []
        seen = set()
        for _, _, _, counter_champ in ranked_hits:
            if counter_champ in seen:
                continue
            seen.add(counter_champ)
            ranked_candidates.append(counter_champ)

        if ranked_candidates:
            counter_candidate_lists.append(
                {"source_enemy": enemy_champ, "candidates": ranked_candidates}
            )
            print(f"Counter candidate list for {enemy_champ}: {ranked_candidates}")
        else:
            print(f"No counter found for enemy champion: {enemy_champ}")

    return counter_candidate_lists


def get_ranked_counter_candidates(
    enemy_champions,
    lane_picks_config,
    ally_champion_ids,
    banned_champions_ids,
    champion_ids,
    owned_champion_ids=None,
):
    """Return available counter candidates globally ranked from best to worst."""
    counter_candidate_lists = get_counter_candidate_lists(
        enemy_champions,
        lane_picks_config,
        ally_champion_ids,
        banned_champions_ids,
        champion_ids,
        owned_champion_ids,
    )
    ranked_candidates = _merge_candidates(
        [champ for source in counter_candidate_lists for champ in source["candidates"]],
        [],
    )

    print(f"Ranked counter candidates: {ranked_candidates}")
    return ranked_candidates


def get_available_default_picks(
    config,
    lane_key,
    ally_champion_ids,
    banned_champions_ids,
    enemy_champions,
    champion_ids,
    owned_champion_ids=None,
    default_section_key="DEFAULT",
):
    """Return available fallback picks in configured order."""
    default_picks = (
        config.get("picks", {}).get(default_section_key, {}).get(lane_key, [])
    )
    available_defaults = []
    for default_champ in default_picks:
        if is_champion_available(
            default_champ,
            ally_champion_ids,
            banned_champions_ids,
            enemy_champions,
            champion_ids,
            owned_champion_ids,
        ):
            available_defaults.append(default_champ)
    return available_defaults


def build_pick_candidates(
    config,
    lane_key,
    enemy_champions,
    lane_picks_config,
    ally_champion_ids,
    banned_champions_ids,
    champion_ids,
    owned_champion_ids=None,
):
    """
    Build ordered pick candidates.

    - random_mode_active = True: use RANDOM_MODE pool only (ignore counters/default)
    - random_mode_active = False: use ranked counters when available; otherwise use DEFAULT picks
    """
    candidate_sources = build_pick_candidate_sources(
        config,
        lane_key,
        enemy_champions,
        lane_picks_config,
        ally_champion_ids,
        banned_champions_ids,
        champion_ids,
        owned_champion_ids,
    )
    selected_candidates = _merge_candidates(
        [champ for source in candidate_sources for champ in source["candidates"]],
        [],
    )
    print(f"Final ordered pick candidates: {selected_candidates}")
    return selected_candidates


def build_pick_candidate_sources(
    config,
    lane_key,
    enemy_champions,
    lane_picks_config,
    ally_champion_ids,
    banned_champions_ids,
    champion_ids,
    owned_champion_ids=None,
):
    """
    Build ordered candidate sources.

    - random_mode_active = True: use RANDOM_MODE pool only (ignore counters/default)
    - random_mode_active = False: use one counter list per enemy when available; otherwise use DEFAULT picks
    """
    random_mode_active = bool(config.get("random_mode_active"))

    if random_mode_active:
        random_mode_candidates = get_available_default_picks(
            config,
            lane_key,
            ally_champion_ids,
            banned_champions_ids,
            enemy_champions,
            champion_ids,
            owned_champion_ids,
            "RANDOM_MODE",
        )
        random.shuffle(random_mode_candidates)
        print(f"🎲 Random mode active. RANDOM_MODE candidates: {random_mode_candidates}")

        if owned_champion_ids is not None:
            random_mode_candidates_without_ownership = get_available_default_picks(
                config,
                lane_key,
                ally_champion_ids,
                banned_champions_ids,
                enemy_champions,
                champion_ids,
                None,
                "RANDOM_MODE",
            )
            ownership_excluded = [
                champ
                for champ in random_mode_candidates_without_ownership
                if champ not in random_mode_candidates
            ]
            if ownership_excluded:
                print(
                    "🚫 Excluded by ownership (not owned on this account): "
                    f"{ownership_excluded}"
                )

        return [{"source_enemy": "RANDOM_MODE", "candidates": random_mode_candidates}]

    counter_candidate_lists_without_ownership = []
    default_candidates_without_ownership = []
    if owned_champion_ids is not None:
        counter_candidate_lists_without_ownership = get_counter_candidate_lists(
            enemy_champions,
            lane_picks_config,
            ally_champion_ids,
            banned_champions_ids,
            champion_ids,
            None,
        )
        default_candidates_without_ownership = get_available_default_picks(
            config,
            lane_key,
            ally_champion_ids,
            banned_champions_ids,
            enemy_champions,
            champion_ids,
            None,
            "DEFAULT",
        )

    counter_candidate_lists = get_counter_candidate_lists(
        enemy_champions,
        lane_picks_config,
        ally_champion_ids,
        banned_champions_ids,
        champion_ids,
        owned_champion_ids,
    )

    default_candidates = get_available_default_picks(
        config,
        lane_key,
        ally_champion_ids,
        banned_champions_ids,
        enemy_champions,
        champion_ids,
        owned_champion_ids,
        "DEFAULT",
    )

    selected_sources = (
        counter_candidate_lists
        if counter_candidate_lists
        else [{"source_enemy": "DEFAULT", "candidates": default_candidates}]
    )
    if counter_candidate_lists:
        print(f"Using counter candidate lists: {counter_candidate_lists}")
    else:
        print("No counter candidate lists available. Falling back to DEFAULT picks.")

    if owned_champion_ids is not None:
        selected_without_ownership = (
            counter_candidate_lists_without_ownership
            if counter_candidate_lists_without_ownership
            else [
                {
                    "source_enemy": "DEFAULT",
                    "candidates": default_candidates_without_ownership,
                }
            ]
        )
        selected_without_ownership_flat = _merge_candidates(
            [champ for source in selected_without_ownership for champ in source["candidates"]],
            [],
        )
        selected_with_ownership_flat = _merge_candidates(
            [champ for source in selected_sources for champ in source["candidates"]],
            [],
        )
        ownership_excluded = [
            champ
            for champ in selected_without_ownership_flat
            if champ not in selected_with_ownership_flat
        ]
        if ownership_excluded:
            print(
                "🚫 Excluded by ownership (not owned on this account): "
                f"{ownership_excluded}"
            )

    return selected_sources


def find_best_counter_pick(
    enemy_champions,
    lane_picks_config,
    ally_champion_ids,
    banned_champions_ids,
    champion_ids,
    owned_champion_ids=None,
):
    """Find the best counter-pick based on enemy champions."""
    ranked_candidates = get_ranked_counter_candidates(
        enemy_champions,
        lane_picks_config,
        ally_champion_ids,
        banned_champions_ids,
        champion_ids,
        owned_champion_ids,
    )
    best_pick = ranked_candidates[0] if ranked_candidates else None
    print(f"Final best pick: {best_pick}")
    return best_pick


def select_default_pick(
    config,
    lane_key,
    ally_champion_ids,
    banned_champions_ids,
    enemy_champions,
    champion_ids,
    owned_champion_ids=None,
):
    """Select a default pick when no counter-pick is available."""
    print("No counter pick found")
    mode = "RANDOM_MODE" if config.get("random_mode_active") else "DEFAULT"
    print(f"Mode: {mode}")
    default_picks = config["picks"].get(mode, {}).get(lane_key, [])
    print(f"Default picks: {default_picks}")
    if default_picks:
        # Filter available default picks (not prepicked by teammates)
        available_defaults = []
        for default_champ in default_picks:
            if is_champion_available(
                default_champ,
                ally_champion_ids,
                banned_champions_ids,
                enemy_champions,
                champion_ids,
                owned_champion_ids,
            ):
                print(f"Available default: {default_champ}")
                available_defaults.append(default_champ)

        if available_defaults:
            if mode == "DEFAULT":
                print(f"Default pick: {available_defaults[0]}")
                return available_defaults[0]
            else:
                random_pick = random.choice(available_defaults)
                print(f"Random pick: {random_pick}")
                return random_pick

    return None
