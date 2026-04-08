"""
Show the session lane / chat message prompt when entering a League lobby, not when queueing.
"""

import threading
import time

from utils import shared_state
from utils.exceptions import LeagueClientDisconnected
from utils.rank_utils import get_gameflow_phase
from features.session_lane_prompt import (
    prompt_session_lane_selection,
    dismiss_lane_prompt_for_lobby_exit,
)


def _lobby_prompt_loop():
    was_in_lobby = False
    while True:
        try:
            phase = get_gameflow_phase()
            if phase is None:
                time.sleep(1)
                continue

            in_lobby = phase == "Lobby"

            if in_lobby and not was_in_lobby:
                prompt_session_lane_selection(shared_state.config_preferred_role)

            # Idle at home while a prompt is still open (user left party without confirming).
            if was_in_lobby and not in_lobby and phase == "None":
                dismiss_lane_prompt_for_lobby_exit()

            was_in_lobby = in_lobby
        except LeagueClientDisconnected:
            was_in_lobby = False
            time.sleep(2)
        except Exception as e:
            print(f"[Lobby prompt watcher]: {e}")
            time.sleep(2)
        time.sleep(1)


def start_lobby_lane_prompt_watcher():
    thread = threading.Thread(target=_lobby_prompt_loop, daemon=True)
    thread.start()
    return thread
