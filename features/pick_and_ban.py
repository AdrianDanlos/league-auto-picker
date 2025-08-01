import requests
import time
import random

from constants import FLEX_CODE, INSTA_PICK_TIME_MILIS, SOLOQ_CODE
from features.select_default_runes_and_summs import (
    select_default_runes,
    select_summoner_spells,
)
from features.send_discord_error_message import log_and_discord
from lcu_connection import get_session
from utils import get_summoner_name

# Global variable to store the data for discord's message
game_data = {
    "picked_champion": None,
    "summoner_name": None,
    "assigned_lane": None,
    "region": None,
    "queueType": None,
}


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


def get_banned_champion_ids(session):
    banned_champs = [
        action["championId"]
        for phase in session["actions"]
        for action in phase
        if action["type"] == "ban" and action["completed"]
    ]

    return banned_champs


def is_champion_available(
    champion_name,
    ally_champion_ids,
    banned_champions_ids,
    enemy_champions,
    champion_ids,
):
    try:
        champion_id = champion_ids.get(champion_name)

        # Check if champion exists in our ID mapping
        if not champion_id:
            return False

        # Check if champion is picked by teammates
        if champion_id in ally_champion_ids:
            return False

        # Check if champion is banned
        if champion_id in banned_champions_ids:
            return False

        # Check if champion is picked by enemies
        if champion_name in enemy_champions:
            return False

        return True
    except Exception as e:
        log_and_discord(f"⚠️ Error in is_champion_available for {champion_name}: {e}")
        return False


def get_champion_name_by_id(champion_id, champion_ids):
    """Convert champion ID to name using the reverse mapping from champion_ids."""
    # Create reverse mapping from the existing champion_ids dict
    id_to_name = {v: k for k, v in champion_ids.items()}
    return id_to_name.get(champion_id)


def find_best_counter_pick(
    enemy_champions,
    lane_picks_config,
    ally_champion_ids,
    banned_champions_ids,
    champion_ids,
):
    if not enemy_champions:
        log_and_discord("🔍 Debug: No enemy champions found")
        return None

    best_pick = None
    earliest_position = float("inf")

    # Check each enemy champion
    for enemy_champ in enemy_champions:
        # Search through all lane configs to find which champion has this enemy as a counter
        try:
            for counter_champ, counter_list in lane_picks_config.items():
                if enemy_champ in counter_list:
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
                                f"🔍 Debug: Skipping {counter_champ} - not available (prepicked, banned, or picked by enemies)"
                            )
                            continue

                        # Check if any matchups are even more favorable
                        if enemy_index < earliest_position:
                            print(
                                f"🔍 Debug: New best pick found! {counter_champ} (enemy at position {enemy_index})"
                            )
                            best_pick = counter_champ
                            earliest_position = enemy_index
                    except Exception as e:
                        log_and_discord(
                            f"⚠️ Error in is_champion_available for {counter_champ}: {e}"
                        )
                        continue
        except Exception as e:
            log_and_discord(
                f"⚠️ Error in counter-pick iteration: {e}\n ⚠️ Lane picks config: {lane_picks_config}"
            )
            return None

    print(f"🔍 Debug: Final best pick: {best_pick}")
    return best_pick


def get_region(session):
    return session["chatDetails"]["mucJwtDto"].get("targetRegion")


def create_discord_message(best_pick, session):
    # Make the variable accesible to the entrypoint
    global game_data
    game_data["picked_champion"] = best_pick
    game_data["summoner_name"] = get_summoner_name(session)
    game_data["assigned_lane"] = get_assigned_lane(session)
    game_data["region"] = get_region(session)
    game_data["queueType"] = get_queueType(session)


def get_queueType(session):
    queue_type = session.get("queueId", 0)
    if queue_type == SOLOQ_CODE:
        return "RANKED_SOLO_5x5"
    elif queue_type == FLEX_CODE:
        return "RANKED_FLEX_SR"


def pick_and_ban(base_url, auth, config):
    """
    Continuously monitors the League of Legends champion select session and automates the pick and ban process.

    This function runs in an infinite loop, periodically checking the champion select session
    and automatically performing picks and bans based on the provided configuration.

    **Pick Logic:**
    1. **Lane Detection**: Determines the player's assigned lane (TOP, JUNGLE, MID, BOTTOM, UTILITY)
    2. **Teammate Tracking**: Collects all champions already picked/hovered by teammates to avoid conflicts
    3. **Counter-Pick Selection**: When it's the player's turn to pick:
        - Gathers enemy champions that have been picked or are being hovered
        - Retrieves the list of banned champions
        - Looks up the lane's pick configuration from config["picks"][LANE]
        - For each enemy champion, searches for counter-picks in the lane's config
        - Selects the first available champion that:
            * Exists in the champion ID mapping
            * Is not prepicked by teammates
            * Is not banned
            * Is not picked by enemies
        - Prioritizes counter-picks based on their position in enemy counter lists
        - Falls back to default picks if no counter-pick is available
    4. **Random Mode**: If random_mode_active is enabled, randomly selects from available default picks
    5. **Execution**: Attempts to pick the selected champion via API call

    **Ban Logic:**
    - When it's the player's turn to ban, attempts to ban the champion specified in config["bans"][LANE]
    - Provides success/failure feedback for ban attempts

    **Session Monitoring:**
    - Continuously polls the session every 4 seconds
    - Only processes actions during BAN_PICK or FINALIZATION phases
    - Handles session termination gracefully

    **Error Handling:**
    - Catches and logs exceptions during pick logic execution
    - Provides fallback behavior when champion availability checks fail
    - Gracefully handles API errors and invalid session states

    Args:
        base_url (str): The base URL for the League Client API (e.g., "https://127.0.0.1:2999")
        auth (tuple): Authentication tuple containing (username, password) for API access
        config (dict): Configuration dictionary with the following structure:
            - picks (dict): Lane-specific pick configurations
                - LANE (str): Dictionary mapping champion names to counter lists
                - DEFAULT (dict): Default pick lists per lane
                - RANDOM_MODE (dict): Random pick lists per lane (if random_mode_active is True)
            - bans (dict): Lane-specific ban preferences
                - LANE (str): Champion name to ban for each lane
            - random_mode_active (bool, optional): Whether to use random selection for default picks

    Returns:
        None: This function runs indefinitely until interrupted or session ends
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
                log_and_discord("Could not determine assigned lane.")
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

            # Collect all championIds picked (hovered or locked in) by teammates
            my_team_cell_ids = {p["cellId"] for p in session.get("myTeam", [])}
            ally_champion_ids = set()
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
                            ally_champion_ids.add(champion_id)
                        else:
                            log_and_discord(
                                f"⚠️ Warning: Invalid champion ID type: {type(champion_id)}, value: {champion_id}"
                            )

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
                                    log_and_discord(
                                        f"❌ Failed to ban {champ}: {res.status_code}"
                                    )

                        elif action["type"] == "pick":
                            print(
                                "⏰ It's time to pick! Waiting before making selection..."
                            )
                            time.sleep(10)

                            # pick_time = False
                            # while not pick_time:
                            #     time.sleep(1)
                            #     session = get_session(base_url, auth)
                            #     if (
                            #         session.get("timer", {}).get(
                            #             "adjustedTimeLeftInPhase", ""
                            #         )
                            #         < INSTA_PICK_TIME_MILIS
                            #     ):
                            #         pick_time = True

                            if game_data["picked_champion"]:
                                print(
                                    "We have already picked a champion, skipping pick and ban"
                                )
                                create_discord_message(
                                    game_data["picked_champion"], session
                                )
                                return

                            try:
                                lane_picks_config = config["picks"].get(lane_key, {})

                                enemy_champions = get_enemy_champions(
                                    session, CHAMPION_IDS
                                )

                                banned_champions_ids = get_banned_champion_ids(session)

                                # print(f"🔍 Debug: Enemy champions: {enemy_champions}")
                                # print(
                                #     f"🔍 Debug: Banned champions: {banned_champions_ids}"
                                # )
                                # print(
                                #     f"🔍 Debug: ally_champion_ids: {ally_champion_ids}"
                                # )

                                best_pick = find_best_counter_pick(
                                    enemy_champions,
                                    lane_picks_config,
                                    ally_champion_ids,
                                    banned_champions_ids,
                                    CHAMPION_IDS,
                                )
                            except Exception as e:
                                log_and_discord(f"⚠️ Error in pick logic: {e}")
                                best_pick = None
                                banned_champions_ids = []  # Fallback to empty list

                            # If no counter-pick found, use DEFAULT
                            if not best_pick:
                                print("No counter pick found")
                                mode = (
                                    "RANDOM_MODE"
                                    if config.get("random_mode_active", False)
                                    else "DEFAULT"
                                )
                                default_picks = (
                                    config["picks"].get(mode, {}).get(lane_key, [])
                                )
                                if default_picks:
                                    # Filter available default picks (not prepicked by teammates)
                                    available_defaults = []
                                    for default_champ in default_picks:
                                        if is_champion_available(
                                            default_champ,
                                            ally_champion_ids,
                                            banned_champions_ids,
                                            enemy_champions,
                                            CHAMPION_IDS,
                                        ):
                                            available_defaults.append(default_champ)

                                    if available_defaults:
                                        if mode == "DEFAULT":
                                            best_pick = available_defaults[0]
                                        else:
                                            best_pick = random.choice(
                                                available_defaults
                                            )

                            if best_pick:
                                print(f"🔍 Debug: Picking {best_pick}")
                                champ_id = CHAMPION_IDS.get(best_pick)
                                print(f"🔍 Debug: Champ ID: {champ_id}")
                                res = requests.patch(
                                    f"{base_url}/lol-champ-select/v1/session/actions/"
                                    f"{action['id']}",
                                    json={"championId": champ_id, "completed": True},
                                    auth=auth,
                                    verify=False,
                                )
                                if res.status_code == 204:
                                    print(f"✅ Picked {best_pick}!")
                                    create_discord_message(best_pick, session)
                                    select_default_runes(base_url, auth)
                                    select_summoner_spells(
                                        base_url, auth, config, best_pick, assigned_lane
                                    )
                                    break
                                else:
                                    log_and_discord(
                                        f"❌ Failed to pick {best_pick}: {res.status_code}"
                                    )
                            else:
                                log_and_discord(
                                    "❌ No suitable champion found to pick."
                                )

            # Wait 4 seconds before next iteration
            time.sleep(4)

        except KeyboardInterrupt:
            print("\n🛑 Pick and ban monitoring stopped by user.")
            break
        except Exception as e:
            log_and_discord(f"❌ Error in pick and ban loop: {e}")
            break
