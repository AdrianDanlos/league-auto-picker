import time
from features.pick_and_ban import game_data
from features.post_game.post_game_utils import get_last_game_data, get_rank_changes
from features.send_discord_message import (
    get_gameflow_phase,
    send_discord_post_game_message,
)


def start_end_of_game_actions(base_url, auth):
    while True:
        gameflow_phase = get_gameflow_phase(base_url, auth)
        if gameflow_phase == "EndOfGame":
            last_game_data = get_last_game_data()
            rank_changes = get_rank_changes()
            print("🟡 rank_changes: ", rank_changes)
            print("🟡 last_game_data: ", last_game_data)
            send_discord_post_game_message(last_game_data, rank_changes, game_data["summoner_name"])
            break
        time.sleep(3)
