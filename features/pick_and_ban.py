import time
import keyboard

from constants import PICK_TIME_LEFT_MS
from features.select_default_runes_and_summs import (
    select_default_runes,
    select_summoner_spells,
)
from utils.logger import log_and_discord
from utils import get_session, LeagueClientDisconnected
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
from features.select_champion_logic import build_pick_candidates
from features.execute_pick_ban import (
    execute_ban,
    execute_pick,
    execute_preselect,
    execute_preselect_intent,
)
from features.discord_message import create_discord_message


def normalize_lane_key(role):
    """Normalize lane names/aliases to config keys."""
    role_key = str(role or "").strip().upper()
    aliases = {
        "MID": "MIDDLE",
        "SUP": "UTILITY",
        "SUPPORT": "UTILITY",
        "ADC": "BOTTOM",
        "BOT": "BOTTOM",
    }
    return aliases.get(role_key, role_key)


def _consume_cycle_request(cycle_state):
    """Consume one queued cycle request from the hotkey callback."""
    if not cycle_state["requested"]:
        return False
    cycle_state["requested"] = False
    return True


def _next_candidate_index(current_index, total_candidates):
    """Return the next candidate index, wrapping back to start."""
    if total_candidates <= 0:
        return 0
    return (current_index + 1) % total_candidates


def _setup_cycle_hotkey(config):
    """Register a global hotkey used to cycle pick candidates."""
    hotkey = str(config.get("cycle_counter_hotkey", "f8")).strip() or "f8"
    cycle_state = {"requested": False}
    hotkey_handler = None

    def _request_cycle():
        cycle_state["requested"] = True

    try:
        hotkey_handler = keyboard.add_hotkey(hotkey, _request_cycle)
        print(f"⌨️ Counter-cycle hotkey active: {hotkey.upper()}")
    except Exception as e:
        log_and_discord(
            f"⚠️ Could not register cycle counter hotkey '{hotkey}': {e}. "
            "Counter cycling will be disabled."
        )

    return hotkey, cycle_state, hotkey_handler


def pick_and_ban(config, preferred_role_override=None):
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

    is_champion_preselected = False
    is_early_default_intent_sent = False
    post_ban_fallback_attempted = False
    early_intent_attempts = 0
    skip_reason_logged = False
    active_pick_action_id = None
    pick_candidates = []
    current_candidate_index = 0
    preselected_pick_name = None
    _, cycle_state, hotkey_handler = _setup_cycle_hotkey(config)

    try:
        while True:
            session = get_session()

            # Check if session is undefined or None
            if not session:
                return

            CHAMPION_IDS = fetch_champion_ids()
            actions = session.get("actions", [])
            my_cell_id = session.get("localPlayerCellId")
            preferred_lane_key = normalize_lane_key(
                preferred_role_override or config.get("preferred_role", "")
            )

            default_picks_for_preferred_role = (
                config.get("picks", {}).get("DEFAULT", {}).get(preferred_lane_key, [])
            )
            early_default_pick = (
                default_picks_for_preferred_role[0]
                if default_picks_for_preferred_role
                else None
            )
            early_default_pick_id = CHAMPION_IDS.get(early_default_pick)

            # Try to preselect as soon as champ-select session is available.
            if not is_early_default_intent_sent and early_default_pick and early_default_pick_id:
                early_intent_attempts += 1
                if execute_preselect_intent(
                    early_default_pick, early_default_pick_id, log_errors=True
                ):
                    print(
                        f"🎯 Early preselect intent confirmed for {early_default_pick} ({preferred_lane_key}) "
                        f"(attempt {early_intent_attempts})"
                    )
                    is_early_default_intent_sent = True
                elif early_intent_attempts == 1:
                    print(
                        "⏳ Early preselect intent not accepted yet. "
                        "Will retry and fallback after ban if needed."
                    )
            elif not skip_reason_logged and not is_early_default_intent_sent:
                if not early_default_pick:
                    print(
                        f"⚠️ Skipping early preselect: no DEFAULT pick for role {preferred_lane_key}."
                    )
                elif not early_default_pick_id:
                    print(
                        f"⚠️ Skipping early preselect: champion ID not found for {early_default_pick}."
                    )
                skip_reason_logged = True

            # Get current phase from timer
            timer = session.get("timer", {})
            current_phase = timer.get("phase", "").upper()

            # Only proceed if we're in a relevant phase
            if not current_phase or current_phase not in ["BAN_PICK", "FINALIZATION"]:
                time.sleep(4)
                session = get_session()
                continue

            assigned_lane = get_assigned_lane(session)
            if not assigned_lane:
                log_and_discord("Could not determine assigned lane.")
                time.sleep(4)
                continue
            lane_key = assigned_lane.upper()

            # Collect all championIds picked (hovered or locked in) by teammates
            my_team_cell_ids = {p["cellId"] for p in session.get("myTeam", [])}
            ally_champion_ids = set()
            for action_group in actions:
                for action in action_group:
                    if (
                        action["type"] == "pick"
                        and action["actorCellId"] in my_team_cell_ids
                        and action["actorCellId"] != my_cell_id
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
                                    if execute_ban(action, champ, champ_id):
                                        # Fallback path: if early intent could not be set,
                                        # try one immediate intent right after ban completes.
                                        if (
                                            not is_early_default_intent_sent
                                            and not post_ban_fallback_attempted
                                            and early_default_pick
                                            and early_default_pick_id
                                        ):
                                            post_ban_fallback_attempted = True
                                            if execute_preselect_intent(
                                                early_default_pick,
                                                early_default_pick_id,
                                                log_errors=True,
                                            ):
                                                print(
                                                    f"🎯 Fallback preselect intent confirmed for {early_default_pick} "
                                                    "right after ban."
                                                )
                                                is_early_default_intent_sent = True
                                            else:
                                                print(
                                                    "⚠️ Post-ban preselect fallback was not accepted."
                                                )
                                    break

                        elif action["type"] == "pick":
                            try:
                                lane_picks_config = config["picks"].get(lane_key, {})

                                enemy_champions = get_enemy_champions(
                                    session, CHAMPION_IDS
                                )

                                banned_champions_ids = get_banned_champion_ids(session)

                                pick_candidates = build_pick_candidates(
                                    config,
                                    lane_key,
                                    enemy_champions,
                                    lane_picks_config,
                                    ally_champion_ids,
                                    banned_champions_ids,
                                    CHAMPION_IDS,
                                )
                            except Exception as e:
                                log_and_discord(f"⚠️ Error in pick logic: {e}")
                                pick_candidates = []
                                banned_champions_ids = []  # Fallback to empty list

                            action_id = action.get("id")
                            if action_id != active_pick_action_id:
                                active_pick_action_id = action_id
                                current_candidate_index = 0
                                is_champion_preselected = False
                                preselected_pick_name = None

                            if (
                                preselected_pick_name
                                and preselected_pick_name in pick_candidates
                            ):
                                current_candidate_index = pick_candidates.index(
                                    preselected_pick_name
                                )
                            elif pick_candidates:
                                current_candidate_index = min(
                                    current_candidate_index,
                                    len(pick_candidates) - 1,
                                )
                            else:
                                current_candidate_index = 0

                            if _consume_cycle_request(cycle_state):
                                if pick_candidates:
                                    previous_index = current_candidate_index
                                    current_candidate_index = _next_candidate_index(
                                        current_candidate_index, len(pick_candidates)
                                    )
                                    cycled_pick = pick_candidates[current_candidate_index]
                                    if current_candidate_index != previous_index:
                                        is_champion_preselected = False
                                        preselected_pick_name = None
                                    print(
                                        f"🔁 Cycle requested. Candidate {current_candidate_index + 1}/{len(pick_candidates)}: {cycled_pick}"
                                    )
                                else:
                                    print(
                                        "⚠️ Cycle requested but no counter/default candidates are available."
                                    )

                            best_pick = (
                                pick_candidates[current_candidate_index]
                                if pick_candidates
                                else None
                            )

                            if not best_pick:
                                log_and_discord(
                                    "⚠️ Could not determine a valid champion to preselect/pick."
                                )
                                continue

                            if not is_champion_preselected:
                                champ_id_to_preselect = CHAMPION_IDS.get(best_pick)
                                preselect_success = execute_preselect(
                                    action, best_pick, champ_id_to_preselect
                                )
                                if preselect_success:
                                    is_champion_preselected = True
                                    preselected_pick_name = best_pick
                                    print(
                                        f"🎯 Preselected {best_pick}, will lock in when timer is low... "
                                        f"(press {str(config.get('cycle_counter_hotkey', 'f8')).upper()} to cycle counters)"
                                    )
                                else:
                                    print(
                                        f"⚠️ Preselect failed for {best_pick}. Will retry on next loop."
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
                                remaining_sleep = sleep_time
                                while remaining_sleep > 0:
                                    interval = min(0.2, remaining_sleep)
                                    time.sleep(interval)
                                    remaining_sleep -= interval

                                    if not _consume_cycle_request(cycle_state):
                                        continue
                                    if not pick_candidates:
                                        continue

                                    previous_index = current_candidate_index
                                    current_candidate_index = _next_candidate_index(
                                        current_candidate_index, len(pick_candidates)
                                    )
                                    best_pick = pick_candidates[current_candidate_index]

                                    if current_candidate_index != previous_index:
                                        is_champion_preselected = False
                                        preselected_pick_name = None
                                        champ_id_to_preselect = CHAMPION_IDS.get(best_pick)
                                        preselect_success = execute_preselect(
                                            action, best_pick, champ_id_to_preselect
                                        )
                                        if preselect_success:
                                            is_champion_preselected = True
                                            preselected_pick_name = best_pick
                                        print(
                                            f"🔁 Cycle requested during wait. Candidate {current_candidate_index + 1}/{len(pick_candidates)}: {best_pick}"
                                        )

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

                            # Re check if its still our turn, we might have switched pick positions on our turn to pick
                            session = get_session()
                            is_our_turn = is_still_our_turn_to_pick(
                                session, session.get("localPlayerCellId")
                            )
                            if not is_our_turn:
                                break

                            print(f"Picking {best_pick}")
                            champ_id = CHAMPION_IDS.get(best_pick)
                            if execute_pick(action, best_pick, champ_id):
                                create_discord_message(best_pick, session)
                                select_default_runes()
                                select_summoner_spells(config, best_pick, assigned_lane)
                                break

            # Wait 4 seconds before next iteration
            time.sleep(4)

    except KeyboardInterrupt:
        print("\n🛑 Pick and ban monitoring stopped by user.")
    except LeagueClientDisconnected:
        return
    except Exception as e:
        log_and_discord(f"❌ Error in pick and ban loop: {e}")
    finally:
        if hotkey_handler is not None:
            try:
                keyboard.remove_hotkey(hotkey_handler)
            except Exception:
                pass
