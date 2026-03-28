import requests
import time
from utils.logger import log_and_discord
from utils import get_auth, get_base_url, handle_connection_errors, get_session


@handle_connection_errors
def execute_ban(action, champion_name, champion_id):
    """Execute a ban action via the League Client API."""
    try:
        res = requests.patch(
            f"{get_base_url()}/lol-champ-select/v1/session/actions/{action['id']}",
            json={
                "championId": champion_id,
                "completed": True,
            },
            auth=get_auth(),
            verify=False,
        )
        if res.status_code == 204:
            print(f"✅ Banned {champion_name}!")
            return True
        else:
            log_and_discord(f"❌ Failed to ban {champion_name}: {res.status_code}")
            return False
    except Exception as e:
        log_and_discord(f"❌ Error executing ban for {champion_name}: {e}")
        return False


@handle_connection_errors
def execute_preselect(action, champion_name, champion_id):
    """Execute a champion preselection (hover) without locking via the League Client API."""
    try:
        res = requests.patch(
            f"{get_base_url()}/lol-champ-select/v1/session/actions/{action['id']}",
            json={"championId": champion_id, "completed": False},
            auth=get_auth(),
            verify=False,
        )
        if res.status_code == 204:
            return True
        else:
            log_and_discord(
                f"❌ Failed to preselect {champion_name}: {res.status_code}"
            )
            return False
    except Exception as e:
        log_and_discord(f"❌ Error executing preselect for {champion_name}: {e}")
        return False


@handle_connection_errors
def execute_preselect_intent(champion_name, champion_id, log_errors=True):
    """Set hover intent via my-selection, even before pick turn."""
    try:
        # Newer clients use `championPickIntent` on my-selection.
        intent_res = requests.patch(
            f"{get_base_url()}/lol-champ-select/v1/session/my-selection",
            json={"championPickIntent": champion_id},
            auth=get_auth(),
            verify=False,
        )
        # Older/community examples use intentChampionId.
        intent_legacy_res = requests.patch(
            f"{get_base_url()}/lol-champ-select/v1/session/my-selection",
            json={"intentChampionId": champion_id},
            auth=get_auth(),
            verify=False,
        )
        # Some clients only react to championId as hover intent.
        champion_res = requests.patch(
            f"{get_base_url()}/lol-champ-select/v1/session/my-selection",
            json={"championId": champion_id},
            auth=get_auth(),
            verify=False,
        )

        # Read-after-write can be briefly stale in champ select.
        current_intent = 0
        current_champion = 0
        my_selection = {}
        my_selection_status = None
        for _ in range(3):
            session = get_session() or {}
            my_cell_id = session.get("localPlayerCellId")
            my_team = session.get("myTeam", [])
            my_player = next(
                (player for player in my_team if player.get("cellId") == my_cell_id),
                {},
            )
            current_intent = my_player.get("championPickIntent")
            current_champion = my_player.get("championId")

            my_selection_res = requests.get(
                f"{get_base_url()}/lol-champ-select/v1/session/my-selection",
                auth=get_auth(),
                verify=False,
            )
            my_selection_status = my_selection_res.status_code
            if my_selection_res.status_code == 200:
                my_selection = my_selection_res.json() or {}

            if (
                current_intent == champion_id
                or current_champion == champion_id
                or my_selection.get("championPickIntent") == champion_id
                or my_selection.get("championId") == champion_id
            ):
                return True
            time.sleep(0.2)

        if log_errors:
            log_and_discord(
                f"❌ Preselect intent did not stick for {champion_name}. "
                f"PATCH statuses: championPickIntent={intent_res.status_code}, "
                f"intentChampionId={intent_legacy_res.status_code}, championId={champion_res.status_code}. "
                f"Session state: championPickIntent={current_intent}, championId={current_champion}. "
                f"My-selection[{my_selection_status}]: "
                f"championPickIntent={my_selection.get('championPickIntent')}, "
                f"championId={my_selection.get('championId')}. "
                f"Responses: championPickIntent='{intent_res.text}', "
                f"intentChampionId='{intent_legacy_res.text}', championId='{champion_res.text}'"
            )
        return False
    except Exception as e:
        if log_errors:
            log_and_discord(f"❌ Error setting preselect intent for {champion_name}: {e}")
        return False


@handle_connection_errors
def execute_pick(action, champion_name, champion_id):
    """Execute a pick action via the League Client API."""
    try:
        res = requests.patch(
            f"{get_base_url()}/lol-champ-select/v1/session/actions/{action['id']}",
            json={"championId": champion_id, "completed": True},
            auth=get_auth(),
            verify=False,
        )
        if res.status_code == 204:
            print(f"✅ Picked {champion_name}!")
            return True
        else:
            log_and_discord(f"❌ Failed to pick {champion_name}: {res.status_code}")
            return False
    except Exception as e:
        log_and_discord(f"❌ Error executing pick for {champion_name}: {e}")
        return False
