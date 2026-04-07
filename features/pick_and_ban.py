import time
import keyboard

from constants import PICK_TIME_LEFT_MS
from features.select_default_runes_and_summs import (
    select_default_runes,
    select_summoner_spells,
)
from utils.logger import log_and_discord
from utils import (
    LeagueClientDisconnected,
    fetch_champion_ids,
    fetch_champion_names,
    get_assigned_lane,
    get_banned_champion_ids,
    get_enemy_champions,
    get_locked_in_champion,
    get_owned_champion_ids,
    get_session,
    is_champion_locked_in,
    is_still_our_turn_to_pick,
    shared_state,
)
from features.select_champion_logic import build_pick_candidate_sources
import features.execute_pick_ban as execute_pick_ban
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


def _first_owned_default_pick(default_names, champion_ids, owned_champion_ids):
    """
    First DEFAULT-list champion with a known ID that the account owns.
    Order matches config; skips entries with missing IDs or not owned.
    """
    if not default_names or not owned_champion_ids:
        return None, None
    for name in default_names:
        cid = champion_ids.get(name)
        if cid and cid in owned_champion_ids:
            return name, cid
    return None, None


def _consume_cycle_request(cycle_state):
    """Consume one queued cycle request from the hotkey callback."""
    if not cycle_state["requested"]:
        return False
    cycle_state["requested"] = False
    return True


def _next_cycle_position(
    candidate_sources, current_source_index, current_candidate_index
):
    """Advance candidate position across source lists and wrap around."""
    if not candidate_sources:
        return 0, 0

    total_sources = len(candidate_sources)
    current_source_index = min(max(current_source_index, 0), total_sources - 1)
    current_candidates = candidate_sources[current_source_index].get("candidates", [])

    if current_candidates and current_candidate_index + 1 < len(current_candidates):
        return current_source_index, current_candidate_index + 1

    for offset in range(1, total_sources + 1):
        next_source_index = (current_source_index + offset) % total_sources
        next_candidates = candidate_sources[next_source_index].get("candidates", [])
        if next_candidates:
            return next_source_index, 0

    return 0, 0


def _get_active_pick(candidate_sources, current_source_index, current_candidate_index):
    """Resolve the active pick and position metadata from candidate sources."""
    if not candidate_sources:
        return None, None, 0, 0

    total_sources = len(candidate_sources)
    current_source_index = min(max(current_source_index, 0), total_sources - 1)
    source = candidate_sources[current_source_index]
    candidates = source.get("candidates", [])
    if not candidates:
        return None, source.get("source_enemy", "UNKNOWN"), current_source_index, 0

    current_candidate_index = min(max(current_candidate_index, 0), len(candidates) - 1)
    return (
        candidates[current_candidate_index],
        source.get("source_enemy", "UNKNOWN"),
        current_source_index,
        current_candidate_index,
    )


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


def _setup_auto_pick_toggle_hotkey(config):
    """
    Register optional global hotkey to toggle automated picking.
    If config omits toggle_auto_pick_hotkey or it is empty after strip, returns None.
    """
    raw = config.get("toggle_auto_pick_hotkey")
    if raw is None:
        return None
    hotkey = str(raw).strip()
    if not hotkey:
        return None

    def _toggle_auto_pick():
        shared_state.auto_pick_enabled = not shared_state.auto_pick_enabled
        state = "ON" if shared_state.auto_pick_enabled else "OFF"
        print(f"⌨️ Auto-pick {state} ({hotkey.upper()})")

    hotkey_handler = None
    try:
        hotkey_handler = keyboard.add_hotkey(hotkey, _toggle_auto_pick)
        print(f"⌨️ Auto-pick toggle hotkey active: {hotkey.upper()}")
    except Exception as e:
        log_and_discord(
            f"⚠️ Could not register auto-pick toggle hotkey '{hotkey}': {e}. "
            "Auto-pick toggle will be disabled."
        )
    return hotkey_handler


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
    shared_state.auto_pick_enabled = True

    is_champion_preselected = False
    is_early_default_intent_sent = False
    post_ban_fallback_attempted = False
    early_intent_attempts = 0
    skip_reason_logged = False
    ownership_warning_logged = False
    active_pick_action_id = None
    pick_candidate_sources = []
    current_source_index = 0
    current_candidate_index = 0
    preselected_pick_name = None
    hotkey_handlers = []
    _, cycle_state, cycle_hotkey_handler = _setup_cycle_hotkey(config)
    if cycle_hotkey_handler is not None:
        hotkey_handlers.append(cycle_hotkey_handler)
    toggle_hotkey_handler = _setup_auto_pick_toggle_hotkey(config)
    if toggle_hotkey_handler is not None:
        hotkey_handlers.append(toggle_hotkey_handler)
    autoselect_runes = config.get("autoselect_runes", True)

    try:
        while True:
            session = get_session()

            # Check if session is undefined or None
            if not session:
                return

            CHAMPION_IDS = fetch_champion_ids()
            owned_champion_ids = get_owned_champion_ids()
            if not owned_champion_ids and not ownership_warning_logged:
                log_and_discord(
                    "⚠️ No owned champions found for the current account. "
                    "All pick candidates will be filtered out until ownership data is available."
                )
                ownership_warning_logged = True
            elif owned_champion_ids:
                ownership_warning_logged = False
            actions = session.get("actions", [])
            my_cell_id = session.get("localPlayerCellId")
            preferred_lane_key = normalize_lane_key(
                preferred_role_override or config.get("preferred_role", "")
            )

            default_picks_for_preferred_role = (
                config.get("picks", {}).get("DEFAULT", {}).get(preferred_lane_key, [])
            )
            early_default_pick, early_default_pick_id = _first_owned_default_pick(
                default_picks_for_preferred_role,
                CHAMPION_IDS,
                owned_champion_ids,
            )
            has_owned_default_preselect = bool(early_default_pick_id)

            # Try to preselect as soon as champ-select session is available.
            if (
                shared_state.auto_pick_enabled
                and not is_early_default_intent_sent
                and early_default_pick
                and early_default_pick_id
                and has_owned_default_preselect
            ):
                early_intent_attempts += 1
                if execute_pick_ban.execute_preselect_intent(
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
                if not default_picks_for_preferred_role:
                    print(
                        f"⚠️ Skipping early preselect: no DEFAULT pick for role {preferred_lane_key}."
                    )
                elif not owned_champion_ids:
                    print(
                        "⚠️ Skipping early preselect: owned champions could not be loaded."
                    )
                elif not early_default_pick:
                    print(
                        f"⚠️ Skipping early preselect: no owned DEFAULT pick for role "
                        f"{preferred_lane_key} (check IDs and ownership)."
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
                                    if execute_pick_ban.execute_ban(
                                        action, champ, champ_id
                                    ):
                                        # Fallback path: if early intent could not be set,
                                        # try one immediate intent right after ban completes.
                                        if (
                                            shared_state.auto_pick_enabled
                                            and not is_early_default_intent_sent
                                            and not post_ban_fallback_attempted
                                            and early_default_pick
                                            and early_default_pick_id
                                            and has_owned_default_preselect
                                        ):
                                            post_ban_fallback_attempted = True
                                            if execute_pick_ban.execute_preselect_intent(
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
                            if not shared_state.auto_pick_enabled:
                                continue
                            try:
                                lane_picks_config = config["picks"].get(lane_key, {})

                                enemy_champions = get_enemy_champions(
                                    session, CHAMPION_IDS
                                )

                                banned_champions_ids = get_banned_champion_ids(session)

                                pick_candidate_sources = build_pick_candidate_sources(
                                    config,
                                    lane_key,
                                    enemy_champions,
                                    lane_picks_config,
                                    ally_champion_ids,
                                    banned_champions_ids,
                                    CHAMPION_IDS,
                                    owned_champion_ids,
                                )
                            except Exception as e:
                                log_and_discord(f"⚠️ Error in pick logic: {e}")
                                pick_candidate_sources = []
                                banned_champions_ids = []  # Fallback to empty list

                            action_id = action.get("id")
                            if action_id != active_pick_action_id:
                                active_pick_action_id = action_id
                                current_source_index = 0
                                current_candidate_index = 0
                                is_champion_preselected = False
                                preselected_pick_name = None

                            if preselected_pick_name and pick_candidate_sources:
                                found_preselected = False
                                for source_index, source in enumerate(
                                    pick_candidate_sources
                                ):
                                    source_candidates = source.get("candidates", [])
                                    if preselected_pick_name in source_candidates:
                                        current_source_index = source_index
                                        current_candidate_index = (
                                            source_candidates.index(
                                                preselected_pick_name
                                            )
                                        )
                                        found_preselected = True
                                        break
                                if not found_preselected:
                                    current_source_index = min(
                                        current_source_index,
                                        len(pick_candidate_sources) - 1,
                                    )
                                    source_candidates = pick_candidate_sources[
                                        current_source_index
                                    ].get("candidates", [])
                                    current_candidate_index = min(
                                        current_candidate_index,
                                        max(len(source_candidates) - 1, 0),
                                    )
                            elif pick_candidate_sources:
                                current_source_index = min(
                                    current_source_index,
                                    len(pick_candidate_sources) - 1,
                                )
                                source_candidates = pick_candidate_sources[
                                    current_source_index
                                ].get("candidates", [])
                                current_candidate_index = min(
                                    current_candidate_index,
                                    max(len(source_candidates) - 1, 0),
                                )
                            else:
                                current_source_index = 0
                                current_candidate_index = 0

                            if _consume_cycle_request(cycle_state):
                                if pick_candidate_sources:
                                    previous_source_index = current_source_index
                                    previous_candidate_index = current_candidate_index
                                    current_source_index, current_candidate_index = (
                                        _next_cycle_position(
                                            pick_candidate_sources,
                                            current_source_index,
                                            current_candidate_index,
                                        )
                                    )
                                    (
                                        cycled_pick,
                                        source_enemy,
                                        source_index,
                                        candidate_index,
                                    ) = _get_active_pick(
                                        pick_candidate_sources,
                                        current_source_index,
                                        current_candidate_index,
                                    )
                                    if (
                                        current_source_index != previous_source_index
                                        or current_candidate_index
                                        != previous_candidate_index
                                    ):
                                        is_champion_preselected = False
                                        preselected_pick_name = None
                                    print(
                                        "🔁 Cycle requested. "
                                        f"List {source_index + 1}/{len(pick_candidate_sources)} ({source_enemy}), "
                                        f"candidate {candidate_index + 1}/{len(pick_candidate_sources[source_index].get('candidates', []))}: "
                                        f"{cycled_pick}"
                                    )
                                else:
                                    print(
                                        "⚠️ Cycle requested but no counter/default candidates are available."
                                    )

                            (
                                best_pick,
                                source_enemy,
                                source_index,
                                candidate_index,
                            ) = _get_active_pick(
                                pick_candidate_sources,
                                current_source_index,
                                current_candidate_index,
                            )

                            if not best_pick:
                                log_and_discord(
                                    "⚠️ Could not determine a valid champion to preselect/pick."
                                )
                                continue

                            if not is_champion_preselected:
                                champ_id_to_preselect = CHAMPION_IDS.get(best_pick)
                                preselect_success = execute_pick_ban.execute_preselect(
                                    action, best_pick, champ_id_to_preselect
                                )
                                if preselect_success:
                                    is_champion_preselected = True
                                    preselected_pick_name = best_pick
                                    print(
                                        f"🎯 Preselected {best_pick} from list {source_index + 1}/{len(pick_candidate_sources)} "
                                        f"({source_enemy}), candidate {candidate_index + 1}/"
                                        f"{len(pick_candidate_sources[source_index].get('candidates', []))}. "
                                        "Will lock in when timer is low... "
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
                                    if not shared_state.auto_pick_enabled:
                                        break
                                    interval = min(0.2, remaining_sleep)
                                    time.sleep(interval)
                                    remaining_sleep -= interval

                                    if not _consume_cycle_request(cycle_state):
                                        continue
                                    if not pick_candidate_sources:
                                        continue

                                    previous_source_index = current_source_index
                                    previous_candidate_index = current_candidate_index
                                    current_source_index, current_candidate_index = (
                                        _next_cycle_position(
                                            pick_candidate_sources,
                                            current_source_index,
                                            current_candidate_index,
                                        )
                                    )
                                    (
                                        best_pick,
                                        source_enemy,
                                        source_index,
                                        candidate_index,
                                    ) = _get_active_pick(
                                        pick_candidate_sources,
                                        current_source_index,
                                        current_candidate_index,
                                    )

                                    if (
                                        current_source_index != previous_source_index
                                        or current_candidate_index
                                        != previous_candidate_index
                                    ):
                                        is_champion_preselected = False
                                        preselected_pick_name = None
                                        champ_id_to_preselect = CHAMPION_IDS.get(
                                            best_pick
                                        )
                                        preselect_success = (
                                            execute_pick_ban.execute_preselect(
                                                action, best_pick, champ_id_to_preselect
                                            )
                                        )
                                        if preselect_success:
                                            is_champion_preselected = True
                                            preselected_pick_name = best_pick
                                        print(
                                            "🔁 Cycle requested during wait. "
                                            f"List {source_index + 1}/{len(pick_candidate_sources)} ({source_enemy}), "
                                            f"candidate {candidate_index + 1}/{len(pick_candidate_sources[source_index].get('candidates', []))}: "
                                            f"{best_pick}"
                                        )

                            if not shared_state.auto_pick_enabled:
                                continue

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
                            if not champ_id:
                                log_and_discord(
                                    f"⚠️ Missing champion ID for {best_pick}. Cannot lock pick."
                                )
                                continue

                            lock_deadline = time.time() + 6.0
                            lock_attempts = 0
                            did_lock = False
                            while time.time() < lock_deadline:
                                current_session = get_session()
                                if not current_session:
                                    break

                                my_cell_id = current_session.get("localPlayerCellId")
                                if not is_still_our_turn_to_pick(
                                    current_session, my_cell_id
                                ):
                                    break

                                current_pick_action = None
                                for action_group in current_session.get("actions", []):
                                    for current_action in action_group:
                                        if (
                                            current_action.get("actorCellId")
                                            == my_cell_id
                                            and current_action.get("isInProgress")
                                            and current_action.get("type") == "pick"
                                        ):
                                            current_pick_action = current_action
                                            break
                                    if current_pick_action:
                                        break

                                if not current_pick_action:
                                    break

                                if not shared_state.auto_pick_enabled:
                                    break

                                lock_attempts += 1
                                if execute_pick_ban.execute_pick(
                                    current_pick_action, best_pick, champ_id
                                ):
                                    did_lock = True
                                    break
                                time.sleep(0.2)

                            if did_lock:
                                create_discord_message(best_pick, session)
                                if autoselect_runes:
                                    select_default_runes()
                                else:
                                    print(
                                        "ℹ️ Rune auto-select disabled in config. Skipping rune setup."
                                    )
                                select_summoner_spells(config, best_pick, assigned_lane)
                                break
                            if lock_attempts > 0:
                                log_and_discord(
                                    f"⚠️ Lock-in retries exhausted for {best_pick} after {lock_attempts} attempts."
                                )

            # Wait 4 seconds before next iteration
            time.sleep(4)

    except KeyboardInterrupt:
        print("\n🛑 Pick and ban monitoring stopped by user.")
    except LeagueClientDisconnected:
        return
    except Exception as e:
        log_and_discord(f"❌ Error in pick and ban loop: {e}")
    finally:
        for handler in hotkey_handlers:
            try:
                keyboard.remove_hotkey(handler)
            except Exception:
                pass
