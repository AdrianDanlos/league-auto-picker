# flake8: noqa: E501
import requests


# === Champion name -> ID map (fetched dynamically from Data Dragon) ===
def fetch_champion_ids():
    version = requests.get(
        "https://ddragon.leagueoflegends.com/api/versions.json"
    ).json()[0]
    champ_data = requests.get(
        f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
    ).json()
    return {champ["name"]: int(champ["key"]) for champ in champ_data["data"].values()}


def get_assigned_lane(session):
    my_cell_id = session.get("localPlayerCellId")
    for participant in session.get("myTeam", []):
        if participant.get("cellId") == my_cell_id:
            return participant.get("assignedPosition")
    return None


def pick_and_ban(session, base_url, auth, config):
    CHAMPION_IDS = fetch_champion_ids()
    actions = session.get("actions", [])
    my_cell_id = session.get("localPlayerCellId")
    assigned_lane = get_assigned_lane(session)
    if not assigned_lane:
        print("Could not determine assigned lane.")
        return
    lane_key = assigned_lane.upper()

    # --- New logic: Collect all championIds prepicked (hovered or locked in) by teammates ---
    my_team_cell_ids = {p["cellId"] for p in session.get("myTeam", [])}
    prepicked_champion_ids = set()
    for action_group in actions:
        for action in action_group:
            if (
                action["type"] == "pick"
                and action["actorCellId"] in my_team_cell_ids
                and action.get("championId", 0) not in (0, None)
            ):
                prepicked_champion_ids.add(action["championId"])
    # --- End new logic ---

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
                    # --- New logic: Skip if champ is prepicked by a teammate ---
                    if champ_id in prepicked_champion_ids:
                        print(
                            f"Skipping ban on {champ} (ID {champ_id}) because a teammate has prepicked it."
                        )
                        continue
                    # --- End new logic ---
                    if champ_id:
                        print(
                            f"Trying to {action['type']} {champ} " f"(ID {champ_id})..."
                        )
                        res = requests.patch(
                            f"{base_url}/lol-champ-select/v1/session/actions/"
                            f"{action['id']}",
                            json={"championId": champ_id, "completed": True},
                            auth=auth,
                            verify=False,
                        )
                        if res.status_code == 204:
                            print(f"✅ {action['type'].capitalize()}ed " f"{champ}!")
                            return
                        else:
                            print(
                                f"❌ Failed to {action['type']} {champ}: "
                                f"{res.status_code}"
                            )
