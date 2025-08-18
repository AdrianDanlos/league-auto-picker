import requests

from .logger import log_and_discord
from .lcu_connection import get_auth, get_base_url


def get_rank_data(queueType):
    try:
        response = requests.get(
            f"{get_base_url()}/lol-ranked/v1/current-ranked-stats",
            auth=get_auth(),
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
            return {
                "tier": "Unknown",
                "division": "Unknown",
                "wins": 0,
                "loses": 0,
                "lp": 0,
            }

    except Exception as e:
        print(f"❌ Unexpected error getting rank data: {e}")
        return {
            "tier": "Unknown",
            "division": "Unknown",
            "wins": 0,
            "loses": 0,
            "lp": 0,
        }


def get_gameflow_phase():
    try:
        response = requests.get(
            f"{get_base_url()}/lol-gameflow/v1/gameflow-phase",
            auth=get_auth(),
            verify=False,
        )

        if response.status_code == 200 or response.status_code == 204:
            # print("✅ phase: ", response.json())
            return response.json()
        else:
            log_and_discord(
                f"❌ Failed to get phase {response.status_code}, {response.text}"
            )
            return None

    except Exception as e:
        print(f"❌ Unexpected error getting gameflow phase: {e}")
        return None
