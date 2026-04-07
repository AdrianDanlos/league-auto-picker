import requests
from .logger import log_and_discord
from .lcu_connection import get_session, get_base_url, get_auth

_cached_owned_summoner_id = None
_cached_owned_champion_ids = set()


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


def get_current_summoner_id():
    """Return the currently logged-in summoner ID from LCU."""
    try:
        response = requests.get(
            f"{get_base_url()}/lol-summoner/v1/current-summoner",
            auth=get_auth(),
            verify=False,
        )
        if response.status_code != 200:
            return None
        payload = response.json() or {}
        return payload.get("summonerId")
    except Exception as e:
        log_and_discord(f"⚠️ Error fetching current summoner ID: {e}")
        return None


def get_owned_champion_ids(force_refresh=False):
    """
    Return champion IDs owned by the current account.

    Uses the LCU endpoint:
    /lol-champions/v1/inventories/{summonerId}/champions-minimal
    """
    global _cached_owned_summoner_id, _cached_owned_champion_ids

    summoner_id = get_current_summoner_id()
    if not summoner_id:
        return set()

    if (
        not force_refresh
        and _cached_owned_summoner_id == summoner_id
        and _cached_owned_champion_ids
    ):
        return set(_cached_owned_champion_ids)

    try:
        response = requests.get(
            f"{get_base_url()}/lol-champions/v1/inventories/{summoner_id}/champions-minimal",
            auth=get_auth(),
            verify=False,
        )
        if response.status_code != 200:
            log_and_discord(
                f"⚠️ Could not fetch owned champions (status {response.status_code})."
            )
            return set()

        champions = response.json() or []
        owned_ids = set()
        for champion in champions:
            if not (champion.get("ownership", {}) or {}).get("owned", False):
                continue
            champion_id = champion.get("id") or champion.get("championId")
            if isinstance(champion_id, int) and champion_id > 0:
                owned_ids.add(champion_id)

        _cached_owned_summoner_id = summoner_id
        _cached_owned_champion_ids = owned_ids
        return set(owned_ids)
    except Exception as e:
        log_and_discord(f"⚠️ Error fetching owned champions: {e}")
        return set()


def _name_in_list_case_insensitive(name, names):
    if not name or not names:
        return False
    target = str(name).casefold()
    return any(str(n).casefold() == target for n in names)


def is_champion_available(
    champion_name,
    ally_champion_ids,
    banned_champions_ids,
    enemy_champions,
    champion_ids,
    owned_champion_ids=None,
):
    """Check if a champion is available for picking."""
    try:
        champion_id = champion_ids.get(champion_name)

        # Check if champion exists in our ID mapping
        if not champion_id:
            return False

        # Check if champion is owned by the current account
        if owned_champion_ids is not None and champion_id not in owned_champion_ids:
            return False

        # Check if champion is picked by teammates
        if champion_id in ally_champion_ids:
            return False

        # Check if champion is banned
        if champion_id in banned_champions_ids:
            return False

        # Check if champion is picked by enemies
        if _name_in_list_case_insensitive(champion_name, enemy_champions):
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
