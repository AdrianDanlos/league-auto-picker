"""
Shared state module to hold global variables that need to be accessed across modules.

This helps avoid circular imports by providing a central location for shared state.
"""

# Global variable to store current queue type
current_queue_type = None

# Global variable to store pre-game LP data
pre_game_lp = {"tier": "Unknown", "division": "Unknown", "lp": 0}

# Global variable to store the data for discord's message
game_data = {
    "picked_champion": None,
    "summoner_name": None,
    "assigned_lane": None,
    "region": None,
    "queueType": None,
}

# Global flag to indicate if League client disconnected
client_disconnected = False

# Preferred role loaded from config.json for prompt defaults/fallback.
config_preferred_role = None

# When False, pick_and_ban skips automated pick actions (hover, lock-in, post-lock runes/summs).
# Toggled at runtime via optional config hotkey; reset to True at each champ select.
auto_pick_enabled = True
