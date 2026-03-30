import random
from utils.logger import log_and_discord
from utils import is_champion_available


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


def get_ranked_counter_candidates(
    enemy_champions,
    lane_picks_config,
    ally_champion_ids,
    banned_champions_ids,
    champion_ids,
    owned_champion_ids=None,
):
    """Return available counter candidates globally ranked from best to worst."""
    if not enemy_champions:
        return []

    ranked_hits = []
    for enemy_order, enemy_champ in enumerate(enemy_champions):
        print(f"Checking enemy champion: {enemy_champ}")
        found_counter = False
        for counter_order, (counter_champ, counter_list) in enumerate(
            lane_picks_config.items()
        ):
            if enemy_champ not in counter_list:
                continue

            found_counter = True
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

                enemy_index = counter_list.index(enemy_champ)
                ranked_hits.append(
                    (enemy_index, enemy_order, counter_order, counter_champ)
                )
            except Exception as e:
                log_and_discord(
                    f"⚠️ Error in is_champion_available for {counter_champ}: {e}"
                )
                continue

        if not found_counter:
            print(f"No counter found for enemy champion: {enemy_champ}")

    ranked_hits.sort(key=lambda item: (item[0], item[1], item[2]))

    ranked_candidates = []
    seen = set()
    for _, _, _, counter_champ in ranked_hits:
        if counter_champ in seen:
            continue
        seen.add(counter_champ)
        ranked_candidates.append(counter_champ)

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
):
    """Return available DEFAULT picks in configured order."""
    default_picks = config.get("picks", {}).get("DEFAULT", {}).get(lane_key, [])
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
    Build ordered pick candidates:
    ranked counters first, then DEFAULT picks in order.
    """
    ranked_counter_candidates_without_ownership = []
    default_candidates_without_ownership = []
    if owned_champion_ids is not None:
        ranked_counter_candidates_without_ownership = get_ranked_counter_candidates(
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
        )

    ranked_counter_candidates = get_ranked_counter_candidates(
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
    )

    merged_candidates = _merge_candidates(ranked_counter_candidates, default_candidates)

    if owned_champion_ids is not None:
        merged_without_ownership = _merge_candidates(
            ranked_counter_candidates_without_ownership,
            default_candidates_without_ownership,
        )
        ownership_excluded = [
            champ for champ in merged_without_ownership if champ not in merged_candidates
        ]
        if ownership_excluded:
            print(
                "🚫 Excluded by ownership (not owned on this account): "
                f"{ownership_excluded}"
            )

    print(f"Final ordered pick candidates: {merged_candidates}")
    return merged_candidates


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
