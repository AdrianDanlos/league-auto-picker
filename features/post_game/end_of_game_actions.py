import time
from entrypoint import current_queue_type
from features.discord_message import get_game_data
from features.post_game.post_game_utils import get_last_game_data, get_rank_changes
from features.discord_message import (
    get_gameflow_phase,
    send_discord_post_game_message,
)


def start_end_of_game_actions():
    message_sent = False
    while True:
        gameflow_phase = get_gameflow_phase()
        if (
            gameflow_phase == "EndOfGame"
            and not message_sent
            and current_queue_type is not None
        ):
            print("🟡 END OF GAME gameflow_phase", gameflow_phase)
            message_sent = True
            game_data = get_game_data()
            send_discord_post_game_message(
                get_last_game_data(), get_rank_changes(), game_data["summoner_name"]
            )
        elif gameflow_phase != "EndOfGame":
            # Reset message_sent when we leave EndOfGame phase
            message_sent = False
        time.sleep(3)
