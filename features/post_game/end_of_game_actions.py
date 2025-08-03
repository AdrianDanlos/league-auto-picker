import time
from features.post_game.post_game_utils import get_last_game_data, get_rank_changes
from features.send_discord_message import (
    get_gameflow_phase,
    send_discord_post_game_message,
)


def start_end_of_game_actions(base_url, auth):
    while True:
        gameflow_phase = get_gameflow_phase(base_url, auth)
        if gameflow_phase == "EndOfGame":
            game_data = get_last_game_data()
            rank_changes = get_rank_changes()
            print(rank_changes)
            print(game_data)
            send_discord_post_game_message(game_data, rank_changes)
            break
        time.sleep(5)
