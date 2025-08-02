import requests


def get_session(base_url, auth):
    r = requests.get(f"{base_url}/lol-champ-select/v1/session", auth=auth, verify=False)
    return r.json() if r.status_code == 200 else None


def get_summoner_name(session):
    local_player_cell_id = session.get("localPlayerCellId")

    # Find your player info in myTeam
    for player in session.get("myTeam", []):
        if player["cellId"] == local_player_cell_id:
            game_name = player.get("gameName", "")
            tag_line = player.get("tagLine", "")

            if game_name and tag_line:
                # FIXME: This is porofessor and opgg format. If we intend to reuse this function we should be careful not to break the link
                return f"{game_name}-{tag_line}"
            elif game_name:
                return game_name
