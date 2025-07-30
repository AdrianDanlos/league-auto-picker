# flake8: noqa: E501
import requests
import time

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
        return None

    best_pick = None
    earliest_position = float("inf")

    # Check each enemy champion
    for enemy_champ in enemy_champions:
        if enemy_champ in lane_picks_config:
            counter_list = lane_picks_config[enemy_champ]

            # Check each counter in the list
            for i, counter_champ in enumerate(counter_list):
                counter_id = champion_ids.get(counter_champ)

                # Skip if champion is prepicked by teammate
                if counter_id in prepicked_champion_ids:
                    continue

                # If this counter is available and appears earlier in the list
                if counter_id and i < earliest_position:
                    best_pick = counter_champ
                    earliest_position = i
                    break  # Found the earliest available counter for this enemy

    return best_pick


def pick_and_ban(base_url, auth, config):
    print("🔄 Starting continuous pick and ban monitoring...")

    while True:
        try:
            session = get_session(base_url, auth)

            # Check if session is undefined or None
            if not session:
                print("🟡 Session ended. Stopping pick and ban monitoring.")
                break

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
                        prepicked_champion_ids.add(action["championId"])
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
                            # Ban logic remains the same
                            champ_list = config["bans"].get(lane_key, [])
                            for champ in champ_list:
                                champ_id = CHAMPION_IDS.get(champ)
                                if champ_id:
                                    print(
                                        f"Trying to ban {champ} " f"(ID {champ_id})..."
                                    )
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
                                        break
                                    else:
                                        print(
                                            f"❌ Failed to ban {champ}: "
                                            f"{res.status_code}"
                                        )
                        else:
                            # New pick logic
                            lane_picks_config = config["picks"].get(lane_key, {})
                            enemy_champions = get_enemy_champions(session, CHAMPION_IDS)

                            # Try to find best counter-pick based on enemy champions
                            best_pick = find_best_counter_pick(
                                enemy_champions,
                                lane_picks_config,
                                prepicked_champion_ids,
                                CHAMPION_IDS,
                            )

                            # If no counter-pick found, use DEFAULT
                            if not best_pick:
                                default_picks = (
                                    config["picks"].get("DEFAULT", {}).get(lane_key, [])
                                )
                                if default_picks:
                                    for default_champ in default_picks:
                                        default_champ_id = CHAMPION_IDS.get(
                                            default_champ
                                        )
                                        if (
                                            default_champ_id
                                            and default_champ_id
                                            not in prepicked_champion_ids
                                        ):
                                            best_pick = default_champ
                                            break

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
