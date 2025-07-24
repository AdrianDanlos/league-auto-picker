# flake8: noqa: E501
import requests
import time
import json
import urllib3
import psutil
import re

# Add pyautogui for click simulation
import pyautogui

# Disable warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === Load config ===
with open("config.json") as f:
    config = json.load(f)

# IMPORTANT: CHAMPIONS DECLARED IN CONFIG.JSON MUST BE ADDED TO THIS MAP
# === Champion name -> ID map (partial, add more as needed) ===
CHAMPION_IDS = {
    "Ahri": 103,
    "Syndra": 134,
    "Galio": 3,
    "Darius": 122,
    "Sett": 875,
    "Yuumi": 350,
    "Lee Sin": 64,
    "Yasuo": 157,
    "Draven": 119,
    "Elise": 60,
    "Warwick": 19,
    "Annie": 1,
    "Jhin": 202,
    "Caitlyn": 51,
    "Blitzcrank": 53,
    "Leona": 89,
    "Garen": 86,
}


def get_lcu_credentials():
    for proc in psutil.process_iter(["cmdline"]):
        if proc.info["cmdline"] and "LeagueClientUx.exe" in proc.info["cmdline"][0]:
            cmdline = " ".join(proc.info["cmdline"])
            port = re.search(r"--app-port=(\d+)", cmdline).group(1)
            token = re.search(r"--remoting-auth-token=([\w-]+)", cmdline).group(1)
            return port, token
    raise RuntimeError("League client not found.")


def get_session(base_url, auth):
    r = requests.get(f"{base_url}/lol-champ-select/v1/session", auth=auth, verify=False)
    return r.json() if r.status_code == 200 else None


def get_assigned_lane(session):
    my_cell_id = session.get("localPlayerCellId")
    for participant in session.get("myTeam", []):
        if participant.get("cellId") == my_cell_id:
            return participant.get("assignedPosition")
    return None


def get_pick_order(session, cell_id):
    """
    Returns the pick order (1-based index) for the given cell_id based on your team's pick actions.
    """
    actions = session.get("actions", [])
    my_team_cell_ids = {p["cellId"] for p in session.get("myTeam", [])}
    pick_order = 1
    for action_group in actions:
        for action in action_group:
            if action["type"] == "pick" and action["actorCellId"] in my_team_cell_ids:
                if action["actorCellId"] == cell_id:
                    return pick_order
                pick_order += 1
    return None


def auto_role_swap(session, config):
    """
    Attempts to swap roles if assigned role is not in preferred_roles.
    Simulates two clicks on the teammate with a preferred role using pick_order_coordinates_first_click and pick_order_coordinates_second_click.
    """
    my_cell_id = session.get("localPlayerCellId")
    my_team = session.get("myTeam", [])
    assigned_role = None
    for participant in my_team:
        if participant.get("cellId") == my_cell_id:
            assigned_role = participant.get("assignedPosition")
            break
    print("assigned_role:", assigned_role)
    if not assigned_role:
        print("[Role Swap] Could not determine assigned role.")
        return
    preferred_role = config.get("preferred_role", "")
    if assigned_role == preferred_role:
        print(
            f"[Role Swap] Assigned role '{assigned_role}' is your preferred role. No swap needed."
        )
        return
    # Find a teammate with the preferred role
    swap_target = None
    for participant in my_team:
        print("preferred_role", preferred_role)
        print("participant.get(assignedPosition):", participant.get("assignedPosition"))
        if (
            participant.get("cellId") != my_cell_id
            and participant.get("assignedPosition") == preferred_role
        ):
            swap_target = participant
            break
    if not swap_target:
        # FIXME: THIS EXCEPTION IS THROWN
        print("[Role Swap] No teammate found with a preferred role to swap.")
        return
    # Get pick order for both players
    my_pick_order = get_pick_order(session, my_cell_id)
    target_pick_order = get_pick_order(session, swap_target["cellId"])
    if not target_pick_order:
        print("[Role Swap] Could not determine target's pick order.")
        return
    if not (1 <= target_pick_order <= 5):
        print(
            f"[Role Swap] Target pick order {target_pick_order} is not in 1-5 (your team). Skipping role swap."
        )
        return
    coord_key = f"position_{target_pick_order}"
    coordinates1 = config.get("pick_order_coordinates_first_click", {}).get(coord_key)
    coordinates2 = config.get("pick_order_coordinates_second_click", {}).get(coord_key)
    if not coordinates1:
        print(f"[Role Swap] No coordinates found for first click: {coord_key}.")
        return
    if not coordinates2:
        print(f"[Role Swap] No coordinates found for second click: {coord_key}.")
        return
    x1, y1 = coordinates1["x"], coordinates1["y"]
    x2, y2 = coordinates2["x"], coordinates2["y"]
    print(
        f"[Role Swap] Attempting to swap with {swap_target['assignedPosition']} at pick order {target_pick_order} (first click at {x1},{y1}, second click at {x2},{y2})"
    )
    try:
        pyautogui.click(x1, y1)
        time.sleep(0.2)  # Small delay between clicks
        pyautogui.click(x2, y2)
        print("[Role Swap] Two click actions performed.")
    except Exception as e:
        print(f"[Role Swap] Failed to perform clicks: {e}")


def act_on_phase(session, base_url, auth):
    actions = session.get("actions", [])
    my_cell_id = session.get("localPlayerCellId")
    assigned_lane = get_assigned_lane(session)
    if not assigned_lane:
        print("Could not determine assigned lane.")
        return
    print(f"Assigned lane: {assigned_lane}")
    lane_key = assigned_lane.upper()
    for action_group in actions:
        for action in action_group:
            if action["actorCellId"] == my_cell_id and action["isInProgress"]:
                champ_list = (
                    config["bans"].get(lane_key, [])
                    if action["type"] == "ban"
                    else config["picks"].get(lane_key, [])
                )
                for champ in champ_list:
                    champ_id = CHAMPION_IDS.get(champ)
                    if champ_id:
                        print(f"Trying to {action['type']} {champ} (ID {champ_id})...")
                        res = requests.patch(
                            f"{base_url}/lol-champ-select/v1/session/actions/{action['id']}",
                            json={"championId": champ_id, "completed": True},
                            auth=auth,
                            verify=False,
                        )
                        if res.status_code == 204:
                            print(f"✅ {action['type'].capitalize()}ed {champ}!")
                            return
                        else:
                            print(
                                f"❌ Failed to {action['type']} {champ}: {res.status_code}"
                            )


def auto_accept_queue(base_url, auth):
    """Polls the ready-check endpoint and accepts the match if found."""
    while True:
        try:
            r = requests.get(
                f"{base_url}/lol-matchmaking/v1/ready-check", auth=auth, verify=False
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("state") == "InProgress":
                    print("🟢 Match found! Accepting queue...")
                    accept = requests.post(
                        f"{base_url}/lol-matchmaking/v1/ready-check/accept",
                        auth=auth,
                        verify=False,
                    )
                    if accept.status_code == 204:
                        print("✅ Queue accepted!")
                        break
                    else:
                        print(f"❌ Failed to accept queue: {accept.status_code}")
            time.sleep(3)
        except Exception as e:
            print("[Queue Accept Error]", e)
            time.sleep(5)


if __name__ == "__main__":
    import pygetwindow as gw

    # Try to find the League client window (the title may vary, adjust if needed)
    windows = gw.getWindowsWithTitle("League of Legends")
    if windows:
        win = windows[0]
        print(f"Client position: ({win.left}, {win.top})")
        print(f"Client size: {win.width}x{win.height}")
    else:
        print("League client window not found.")
    port, token = get_lcu_credentials()
    base_url = f"https://127.0.0.1:{port}"
    auth = requests.auth.HTTPBasicAuth("riot", token)

    print("🟢 Waiting for queue pop...")
    auto_accept_queue(base_url, auth)
    print("🟢 Waiting for champ select...")
    while True:
        try:
            session = get_session(base_url, auth)
            if session:
                auto_role_swap(session, config)
                act_on_phase(session, base_url, auth)
            time.sleep(1)
        except Exception as e:
            print("[Error]", e)
            time.sleep(5)
