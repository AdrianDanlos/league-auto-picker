config = {
    "picks": {
        "MIDDLE": {
            "Diana": [
                "Annie",
                "Yone",
                "Malzahar",
                "Leblanc",
                "Azir",
                "Fizz",
                "Aurora",
                "Katarina",
                "Orianna",
                "Akshan",
                "Zed",
                "Xerath",
                "Hwei",
                "Qiyana",
                "Vex",
                "Veigar",
            ],
            "Aurelion Sol": [
                "Orianna",
                "Mel",
                "Yasuo",
                "Taliyah",
                "Sylas",
                "Syndra",
                "Viktor",
                "Hwei",
                "Lissandra",
            ],
            "Ahri": ["Aurelion Sol", "Galio", "Hwei", "Yone", "Ziggs", "Azir"],
            "Kassadin": [
                "Taliyah",
                "Kayle",
                "Mel",
                "Viktor",
                "Leblanc",
                "Hwei",
                "Aurelion Sol",
                "Katarina",
                "Zoe",
                "Annie",
                "Anivia",
            ],
            "Fizz": [
                "Aurelion Sol",
                "Mel",
                "Hwei",
                "Xerath",
                "Syndra",
                "Malzahar",
                "Azir",
                "Taliyah",
                "Qiyana",
                "Yone",
                "Katarina",
                "Ziggs",
            ],
            "Galio": [
                "Ryze",
                "Viktor",
                "Diana",
                "Sylas",
                "Akali",
                "Kassadin",
                "Vladimir",
                "Fizz",
                "Aurelion Sol",
                "Mel",
                "Azir",
                "Katarina",
                "Malzahar",
            ],
            "Lissandra": [
                "Yasuo",
                "Katarina",
                "Fizz",
                "Ryze",
                "Yone",
                "Aurora",
                "Malzahar",
                "Vex",
                "Akali",
                "Azir",
                "Veigar",
                "Taliyah",
            ],
            "Orianna": [
                "Corki",
                "Yone",
                "Vladimir",
                "Mel",
                "Ahri",
                "Kassadin",
                "Twisted Fate",
            ],
            "Viktor": ["Mel", "Azir", "Ryze", "Ziggs"],
            "Malphite": ["Twisted Fate", "Zed", "Mel", "Azir", "Ryze", "Ziggs"],
            "Ziggs": ["Cassiopeia"],
            "Sylas": ["Aurora"],
        }
    }
}

lane_key = "MIDDLE"


def find_best_counter_pick(enemy_champions, lane_picks_config):
    """
    Find the best counter-pick based on enemy champions.
    Returns the champion name to pick, or None if no suitable pick found.
    """
    best_pick = None
    earliest_position = float("inf")

    # Check each enemy champion
    for enemy_champ in enemy_champions:
        print(f"🔍 Debug: Checking enemy champion: {enemy_champ}")
        # Search through all lane configs to find which champion has this enemy as a counter
        for counter_champ, counter_list in lane_picks_config.items():
            if enemy_champ in counter_list:
                # Found the enemy champion in this counter list
                enemy_index = counter_list.index(enemy_champ)
                print(
                    f"🔍 Debug: Found {enemy_champ} in {counter_champ}'s counter list at position {enemy_index}"
                )

                # If this counter is available and appears earlier in the list
                if enemy_index < earliest_position:
                    print(
                        f"🔍 Debug: New best pick found! {counter_champ} (enemy at position {enemy_index})"
                    )
                    best_pick = counter_champ
                    earliest_position = enemy_index
                    # break  # Found the earliest available counter for this enemy
                else:
                    print(
                        f"🔍 Debug: {counter_champ} not selected - position {enemy_index} >= {earliest_position} or not available"
                    )

    print(f"🔍 Debug: Final best pick: {best_pick}")
    return best_pick


# New pick logic
lane_picks_config = config["picks"].get(lane_key, {})
enemy_champions = ["Jarvan", "Ambessa", "Jinx", "Ryze"]

best_pick = find_best_counter_pick(
    enemy_champions,
    lane_picks_config,
)
