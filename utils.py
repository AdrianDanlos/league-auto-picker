import requests

from features.send_discord_error_message import log_and_discord


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


def get_rank_data(base_url, auth, queueType):
    try:
        response = requests.get(
            f"{base_url}/lol-ranked/v1/current-ranked-stats",
            auth=auth,
            verify=False,
        )

        if response.status_code == 200 or response.status_code == 204:
            player_data = response.json()
            ranked_data = player_data["queueMap"][queueType]
            return {
                "tier": ranked_data.get("tier", "Unknown"),
                "division": ranked_data.get("division", "Unknown"),
                "wins": ranked_data.get("wins", 0),
                "loses": ranked_data.get("losses", 0),
                "lp": ranked_data.get("leaguePoints", 0),
            }
        else:
            log_and_discord(
                f"❌ Failed to get rank data {response.status_code}, {response.text}"
            )

    except Exception as e:
        log_and_discord(f"❌ Unexpected error sending discord message: {e}")


def get_gameflow_phase(base_url, auth):
    try:
        response = requests.get(
            f"{base_url}/lol-gameflow/v1/gameflow-phase",
            auth=auth,
            verify=False,
        )

        if response.status_code == 200 or response.status_code == 204:
            print("✅ phase: ", response.json())
            return response.json()
        else:
            log_and_discord(
                f"❌ Failed to get phase {response.status_code}, {response.text}"
            )

    except Exception as e:
        log_and_discord(f"❌ Unexpected error sending discord message: {e}")
