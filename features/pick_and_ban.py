import time

from constants import PICK_TIME_LEFT_MS
from features.select_default_runes_and_summs import (
    select_default_runes,
    select_summoner_spells,
)
from utils.logger import log_and_discord
from utils import get_session
from utils import (
    fetch_champion_ids,
    fetch_champion_names,
    is_champion_locked_in,
    get_locked_in_champion,
)
from utils import (
    get_assigned_lane,
    get_enemy_champions,
    get_banned_champion_ids,
    is_still_our_turn_to_pick,
)
from features.select_champion_logic import find_best_counter_pick, select_default_pick
from features.execute_pick_ban import execute_ban, execute_pick
from features.discord_message import create_discord_message


def pick_and_ban(config):
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
            session = get_session()

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
                session = get_session()
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
                        ally_champion_ids.add(action["championId"])

            for action_group in actions:
                for action in action_group:
                    if action["actorCellId"] == my_cell_id and action["isInProgress"]:
                        # Only attempt ban if we're in ban phase, pick if we're in pick phase
                        if action["type"] == "ban" and "BAN" not in current_phase:
                            continue
                        if action["type"] == "pick" and "PICK" not in current_phase:
                            continue

                        if action["type"] == "ban":
                            champions_to_ban = config["bans"].get(lane_key, [])
                            for champ in champions_to_ban:
                                champ_id = CHAMPION_IDS.get(champ)
                                if champ_id and champ_id not in ally_champion_ids:
                                    execute_ban(action, champ, champ_id)
                                    break

                        elif action["type"] == "pick":
                            print(
                                "⏰ It's time to pick! Waiting before making selection..."
                            )

                            timeLeftToPickMilis = session.get("timer", {}).get(
                                "adjustedTimeLeftInPhase", 0
                            )

                            # Calculate sleep time, ensuring it's not negative
                            sleep_time = max(
                                0, (timeLeftToPickMilis - PICK_TIME_LEFT_MS) / 1000
                            )

                            # Pick when there is 5 seconds left (5000ms) - PICK_TIME_LEFT_MS
                            if sleep_time > 0:
                                time.sleep(sleep_time)

                            # Check if already locked in before waiting
                            if is_champion_locked_in():
                                CHAMPION_NAMES = fetch_champion_names()
                                locked_in_champion_id = get_locked_in_champion()
                                champion_name = CHAMPION_NAMES.get(
                                    locked_in_champion_id
                                )
                                print(
                                    "We have already picked a champion, skipping pick and ban"
                                )
                                create_discord_message(champion_name, session)
                                return

                            try:
                                lane_picks_config = config["picks"].get(lane_key, {})

                                enemy_champions = get_enemy_champions(
                                    session, CHAMPION_IDS
                                )

                                banned_champions_ids = get_banned_champion_ids(session)

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

                            # Re check if its still our turn, we might have switched pick positions on our turn to pick
                            session = get_session()
                            is_our_turn = is_still_our_turn_to_pick(
                                session, my_cell_id
                            )
                            if not is_our_turn:
                                break

                            # If no counter-pick found, use DEFAULT
                            if not best_pick:
                                best_pick = select_default_pick(
                                    config,
                                    lane_key,
                                    ally_champion_ids,
                                    banned_champions_ids,
                                    enemy_champions,
                                    CHAMPION_IDS,
                                )

                            if best_pick:
                                print(f"Picking {best_pick}")
                                champ_id = CHAMPION_IDS.get(best_pick)
                                if execute_pick(action, best_pick, champ_id):
                                    create_discord_message(best_pick, session)
                                    select_default_runes()
                                    select_summoner_spells(
                                        config, best_pick, assigned_lane
                                    )
                                    break
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
