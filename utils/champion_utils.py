import requests
from .logger import log_and_discord
from .lcu_connection import get_session


def fetch_champion_ids():
    """Fetch champion name to ID mapping from Data Dragon API."""
    try:
        version = requests.get(
            "https://ddragon.leagueoflegends.com/api/versions.json"
        ).json()[0]
        champ_data = requests.get(
            f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
        ).json()
        return {
            champ["name"]: int(champ["key"]) for champ in champ_data["data"].values()
        }
    except Exception as e:
        log_and_discord(f"⚠️ Error fetching champion IDs: {e}")
        return {}


def fetch_champion_names():
    """Fetch champion ID to name mapping from Data Dragon API."""
    try:
        version = requests.get(
            "https://ddragon.leagueoflegends.com/api/versions.json"
        ).json()[0]
        champ_data = requests.get(
            f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
        ).json()
        return {
            int(champ["key"]): champ["name"] for champ in champ_data["data"].values()
        }
    except Exception as e:
        log_and_discord(f"⚠️ Error fetching champion names: {e}")
        return {}


def get_champion_name_by_id(champion_id, champion_ids):
    """Convert champion ID to name using the reverse mapping from champion_ids."""
    # Create reverse mapping from the existing champion_ids dict
    id_to_name = {v: k for k, v in champion_ids.items()}
    return id_to_name.get(champion_id)


def is_champion_available(
    champion_name,
    ally_champion_ids,
    banned_champions_ids,
    enemy_champions,
    champion_ids,
):
    """Check if a champion is available for picking."""
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


def is_champion_locked_in():
    """Check if a champion is already locked in."""
    session = get_session()
    my_id = session["localPlayerCellId"]
    for actions in session["actions"]:
        for a in actions:
            if a.get("actorCellId") == my_id and a.get("type") == "pick":
                return a.get("completed", False)
    return False


def get_locked_in_champion():
    """Get the ID of the currently locked in champion."""
    session = get_session()
    my_id = session["localPlayerCellId"]
    for actions in session["actions"]:
        for a in actions:
            if a.get("actorCellId") == my_id and a.get("type") == "pick":
                return a.get("championId", 0)
    return None
