import time
from features.discord_message import get_game_data
from features.post_game.post_game_utils import get_last_game_data, get_rank_changes
from features.discord_message import (
    get_gameflow_phase,
    send_discord_post_game_message,
)


def start_end_of_game_actions():
    while True:
        gameflow_phase = get_gameflow_phase()
        if gameflow_phase == "EndOfGame":
            game_data = get_game_data()
            send_discord_post_game_message(
                get_last_game_data(), get_rank_changes(), game_data["summoner_name"]
            )
        time.sleep(3)
