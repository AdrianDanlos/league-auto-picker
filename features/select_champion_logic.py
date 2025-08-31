import random
from utils.logger import log_and_discord
from utils import is_champion_available


def find_best_counter_pick(
    enemy_champions,
    lane_picks_config,
    ally_champion_ids,
    banned_champions_ids,
    champion_ids,
):
    """Find the best counter-pick based on enemy champions."""
    if not enemy_champions:
        return None

    best_pick = None
    earliest_position = float("inf")

    # Check each enemy champion
    for enemy_champ in enemy_champions:
        print(f"Checking enemy champion: {enemy_champ}")
        # Search through all lane configs to find which champion has this enemy as a counter
        try:
            found_counter = False
            for counter_champ, counter_list in lane_picks_config.items():
                if enemy_champ in counter_list:
                    found_counter = True
                    print(
                        f"Found {enemy_champ} in counter list for {counter_champ}"
                    )
                    # Found the enemy champion in this counter list
                    enemy_index = counter_list.index(enemy_champ)

                    try:
                        if not is_champion_available(
                            counter_champ,
                            ally_champion_ids,
                            banned_champions_ids,
                            enemy_champions,
                            champion_ids,
                        ):
                            print(
                                f"Skipping {counter_champ} - not available (prepicked, banned, or picked by enemies)"
                            )
                            continue

                        # Check if any matchups are even more favorable
                        if enemy_index < earliest_position:
                            print(
                                f"New best pick found! {counter_champ} (enemy at position {enemy_index})"
                            )
                            best_pick = counter_champ
                            earliest_position = enemy_index
                    except Exception as e:
                        log_and_discord(
                            f"⚠️ Error in is_champion_available for {counter_champ}: {e}"
                        )
                        continue

            if not found_counter:
                print(f"No counter found for enemy champion: {enemy_champ}")

        except Exception as e:
            log_and_discord(
                f"⚠️ Error in counter-pick iteration: {e}\n ⚠️ Lane picks config: {lane_picks_config}"
            )
            return None

    print(f"Final best pick: {best_pick}")
    return best_pick


def select_default_pick(
    config,
    lane_key,
    ally_champion_ids,
    banned_champions_ids,
    enemy_champions,
    champion_ids,
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
