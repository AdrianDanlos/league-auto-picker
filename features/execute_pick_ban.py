import requests
from utils.logger import log_and_discord
from utils import get_auth, get_base_url, handle_connection_errors


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
