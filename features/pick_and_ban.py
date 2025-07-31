import requests
import time
import random

from utils import get_session


# === Champion name -> ID map (fetched dynamically from Data Dragon) ===
def fetch_champion_ids():
    version = requests.get(
        "https://ddragon.leagueoflegends.com/api/versions.json"
    ).json()[0]
    champ_data = requests.get(
        f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
    ).json()
    return {champ["name"]: int(champ["key"]) for champ in champ_data["data"].values()}


def get_assigned_lane(session):
    my_cell_id = session.get("localPlayerCellId")
    for participant in session.get("myTeam", []):
        if participant.get("cellId") == my_cell_id:
            return participant.get("assignedPosition")
    return None


def get_enemy_champions(session, champion_ids):
    """Get all enemy champions that have been picked or are being hovered."""
    enemy_champions = []
    their_team = session.get("theirTeam", [])

    for participant in their_team:
        # Check if they have picked a champion
        if participant.get("championId") and participant.get("championId") != 0:
            # Convert champion ID to name
            champion_name = get_champion_name_by_id(
                participant.get("championId"), champion_ids
            )
            if champion_name:
                enemy_champions.append(champion_name)

    return enemy_champions


def get_champion_name_by_id(champion_id, champion_ids):
    """Convert champion ID to name using the reverse mapping from champion_ids."""
    # Create reverse mapping from the existing champion_ids dict
    id_to_name = {v: k for k, v in champion_ids.items()}
    return id_to_name.get(champion_id)


def find_best_counter_pick(
    enemy_champions, lane_picks_config, prepicked_champion_ids, champion_ids
):
    """
    Find the best counter-pick based on enemy champions.
    Returns the champion name to pick, or None if no suitable pick found.
    """
    if not enemy_champions:
        print("🔍 Debug: No enemy champions found")
        return None

    print(
        f"🔍 Debug: Searching for counters against enemy champions: {enemy_champions}"
    )
    print(f"🔍 Debug: Available counter champions: {list(lane_picks_config.keys())}")

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

                # Check if the counter champion is available
                counter_id = champion_ids.get(counter_champ)
                print(f"🔍 Debug: {counter_champ} has ID: {counter_id}")

                # Skip if champion is prepicked by teammate
                # Add type checking to prevent "unhashable type: 'list'" error
                if (
                    counter_id is not None
                    and isinstance(counter_id, (int, str))
                    and counter_id in prepicked_champion_ids
                ):
                    print(
                        f"🔍 Debug: Skipping {counter_champ} - already prepicked by teammate"
                    )
                    continue

                # If this counter is available and appears earlier in the list
                if (
                    counter_id
                    and isinstance(counter_id, (int, str))
                    and enemy_index < earliest_position
                ):
                    print(
                        f"🔍 Debug: New best pick found! {counter_champ} (enemy at position {enemy_index})"
                    )
                    best_pick = counter_champ
                    earliest_position = enemy_index
                else:
                    print(
                        f"🔍 Debug: {counter_champ} not selected - position {enemy_index} >= {earliest_position} or not available"
                    )

    print(f"🔍 Debug: Final best pick: {best_pick}")
    return best_pick


def pick_and_ban(base_url, auth, config):
    """
    Continuously monitors the League of Legends champion select session and automates the pick and ban process.

    ---
    PICK LOGIC:
    1. The function periodically fetches the current champion select session and determines your assigned lane (e.g., TOP, JUNGLE, etc.).
    2. It collects all champion IDs that are already prepicked (hovered or locked in) by your teammates, so it will not attempt to pick these champions.
    3. When it is your turn to pick (i.e., your action is in progress and the phase is PICK): (CONFIG MATCHUPS FROM PATCH 15.14)
        a. It gathers the list of enemy champions that have already been picked or are being hovered.
        b. It looks up your lane's pick configuration from the config file (config["picks"][LANE]).
        c. For each enemy champion, it checks if there is a counter-pick list for that champion in your lane's config. It iterates through the counter-pick list in order, and selects the first champion that:
            - Is present in the champion ID map
            - Is NOT already prepicked by a teammate
        d. If multiple enemy champions have counter-picks available, the function prioritizes the champion that appears at the earliest index position across all counter lists. For example:
            - If enemy A has counter list ["Champ1", "Champ2", "Champ3"] and Champ2 is available (index 1)
            - If enemy B has counter list ["Champ4", "Champ1", "Champ5"] and Champ1 is available (index 1)
            - The function will pick Champ1 because it appears at index 1 in enemy B's list, which is earlier than Champ2 at index 1 in enemy A's list
        e. If a suitable counter-pick is found, it attempts to pick that champion.
        f. If no counter-pick is found for any enemy champion, it falls back to the default pick list for your lane (config["picks"]["DEFAULT"][LANE]). It iterates through the default picks in order, and selects the first champion that is available and not prepicked by a teammate.
        g. If a pick is successfully made (API returns 204), it prints a success message and stops further pick attempts for this round.
        h. If no suitable champion is found (all are prepicked or unavailable), it prints a failure message and does not pick.
    4. The process repeats every 4 seconds until the session ends or is interrupted.

    BAN LOGIC:
    - When it is your turn to ban, it attempts to ban the champion specified for your lane in config["bans"][LANE].
    - If the ban is successful, it prints a success message; otherwise, it prints a failure message.

    Args:
        base_url (str): The base URL for the League Client API.
        auth (tuple): Authentication tuple (username, password) for the API.
        config (dict): Configuration dictionary containing pick and ban preferences.
    """
    print("🔄 Starting continuous pick and ban monitoring...")

    while True:
        try:
            session = get_session(base_url, auth)

            # Check if session is undefined or None
            if not session:
                return

            CHAMPION_IDS = fetch_champion_ids()
            actions = session.get("actions", [])
            my_cell_id = session.get("localPlayerCellId")
            assigned_lane = get_assigned_lane(session)
            if not assigned_lane:
                print("Could not determine assigned lane.")
                time.sleep(4)
                continue
            lane_key = assigned_lane.upper()

            # Get current phase from timer
            timer = session.get("timer", {})
            current_phase = timer.get("phase", "").upper()

            # Only proceed if we're in a relevant phase
            if not current_phase or current_phase not in ["BAN_PICK", "FINALIZATION"]:
                time.sleep(4)
                continue

            # --- New logic: Collect all championIds prepicked (hovered or locked in) by teammates ---
            my_team_cell_ids = {p["cellId"] for p in session.get("myTeam", [])}
            prepicked_champion_ids = set()
            for action_group in actions:
                for action in action_group:
                    if (
                        action["type"] == "pick"
                        and action["actorCellId"] in my_team_cell_ids
                        and action.get("championId", 0) not in (0, None)
                    ):
                        champion_id = action["championId"]
                        # Add type checking to ensure we only add valid champion IDs
                        if isinstance(champion_id, (int, str)):
                            prepicked_champion_ids.add(champion_id)
                        else:
                            print(
                                f"⚠️ Warning: Invalid champion ID type: {type(champion_id)}, value: {champion_id}"
                            )
            # --- End new logic ---

            for action_group in actions:
                for action in action_group:
                    if action["actorCellId"] == my_cell_id and action["isInProgress"]:
                        # Only attempt ban if we're in ban phase, pick if we're in pick phase
                        if action["type"] == "ban" and "BAN" not in current_phase:
                            continue
                        if action["type"] == "pick" and "PICK" not in current_phase:
                            continue

                        if action["type"] == "ban":
                            champ = config["bans"].get(lane_key, None)
                            champ_id = CHAMPION_IDS.get(champ)
                            if champ_id:
                                res = requests.patch(
                                    f"{base_url}/lol-champ-select/v1/session/actions/"
                                    f"{action['id']}",
                                    json={
                                        "championId": champ_id,
                                        "completed": True,
                                    },
                                    auth=auth,
                                    verify=False,
                                )
                                if res.status_code == 204:
                                    print(f"✅ Banned {champ}!")
                                else:
                                    print(
                                        f"❌ Failed to ban {champ}: "
                                        f"{res.status_code}"
                                    )

                        elif action["type"] == "pick":
                            print(
                                "⏰ It's time to pick! Waiting 10 seconds before making selection..."
                            )
                            time.sleep(10)

                            # New pick logic
                            lane_picks_config = config["picks"].get(lane_key, {})
                            enemy_champions = get_enemy_champions(session, CHAMPION_IDS)

                            # Try to find best counter-pick based on enemy champions
                            # Add debugging to help identify the issue
                            print(f"🔍 Debug: enemy_champions = {enemy_champions}")
                            print(
                                f"🔍 Debug: lane_picks_config keys = {list(lane_picks_config.keys())}"
                            )
                            print(
                                f"🔍 Debug: prepicked_champion_ids = {prepicked_champion_ids}"
                            )

                            best_pick = find_best_counter_pick(
                                enemy_champions,
                                lane_picks_config,
                                prepicked_champion_ids,
                                CHAMPION_IDS,
                            )

                            # If no counter-pick found, use DEFAULT
                            if not best_pick:
                                print(f"🔍 Debug: No counter pick found = {best_pick}")
                                mode = (
                                    "RANDOM_MODE"
                                    if config.get("RANDOM_MODE_ACTIVE", False)
                                    else "DEFAULT"
                                )
                                default_picks = (
                                    config["picks"].get(mode, {}).get(lane_key, [])
                                )
                                if default_picks:
                                    # Filter available default picks (not prepicked by teammates)
                                    available_defaults = []
                                    for default_champ in default_picks:
                                        default_champ_id = CHAMPION_IDS.get(
                                            default_champ
                                        )
                                        if (
                                            default_champ_id
                                            and default_champ_id
                                            not in prepicked_champion_ids
                                        ):
                                            available_defaults.append(default_champ)

                                    # Pick a random available default
                                    if available_defaults:
                                        best_pick = random.choice(available_defaults)

                            if best_pick:
                                champ_id = CHAMPION_IDS.get(best_pick)
                                print(
                                    f"Trying to pick {best_pick} " f"(ID {champ_id})..."
                                )
                                res = requests.patch(
                                    f"{base_url}/lol-champ-select/v1/session/actions/"
                                    f"{action['id']}",
                                    json={"championId": champ_id, "completed": True},
                                    auth=auth,
                                    verify=False,
                                )
                                if res.status_code == 204:
                                    print(f"✅ Picked {best_pick}!")
                                    break
                                else:
                                    print(
                                        f"❌ Failed to pick {best_pick}: "
                                        f"{res.status_code}"
                                    )
                            else:
                                print("❌ No suitable champion found to pick.")

            # Wait 4 seconds before next iteration
            time.sleep(4)

        except KeyboardInterrupt:
            print("\n🛑 Pick and ban monitoring stopped by user.")
            break
        except Exception as e:
            print(f"❌ Error in pick and ban loop: {e}")
            break
