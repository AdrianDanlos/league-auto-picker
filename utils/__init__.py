"""
Unified utilities package for the League Auto Picker.

This package consolidates all utility functions from various scattered utility files
into organized modules based on their functionality.
"""

from .lcu_connection import (
    get_auth,
    get_base_url,
    get_lcu_credentials,
    get_session,
)
from .rank_utils import get_rank_data, get_gameflow_phase
from .session_utils import (
    get_assigned_lane,
    get_enemy_champions,
    get_banned_champion_ids,
    get_region,
    get_queueType,
    is_still_our_turn_to_pick,
    get_summoner_name,
)
from .champion_utils import (
    fetch_champion_ids,
    fetch_champion_names,
    get_champion_name_by_id,
    is_champion_available,
    is_champion_locked_in,
    get_locked_in_champion,
)
from .logger import log_and_discord, send_discord_error_message

__all__ = [
    # LCU Connection
    "get_auth",
    "get_base_url",
    "get_lcu_credentials",
    "get_session",
    # Rank and Gameflow
    "get_rank_data",
    "get_gameflow_phase",
    # Session utilities
    "get_assigned_lane",
    "get_enemy_champions",
    "get_banned_champion_ids",
    "get_region",
    "get_queueType",
    "is_still_our_turn_to_pick",
    "get_summoner_name",
    # Champion utilities
    "fetch_champion_ids",
    "fetch_champion_names",
    "get_champion_name_by_id",
    "is_champion_available",
    "is_champion_locked_in",
    "get_locked_in_champion",
    # Logging utilities
    "log_and_discord",
    "send_discord_error_message",
]
