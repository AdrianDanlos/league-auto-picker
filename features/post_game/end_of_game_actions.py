import time
import requests
from utils import shared_state, LeagueClientDisconnected
from features.discord_message import get_game_data
from features.post_game.post_game_utils import sanitize_last_game_data, get_rank_changes
from features.discord_message import (
    get_gameflow_phase,
    send_discord_post_game_message,
)


def start_end_of_game_actions():
    message_sent = False
    while True:
        try:
            gameflow_phase = get_gameflow_phase()
            if (
                gameflow_phase == "EndOfGame"
                and not message_sent
                and shared_state.current_queue_type is not None
            ):
                print("🟡 END OF GAME gameflow_phase", gameflow_phase)
                message_sent = True
                game_data = get_game_data()
                send_discord_post_game_message(
                    sanitize_last_game_data(),
                    get_rank_changes(),
                    game_data["summoner_name"],
                )
            elif gameflow_phase != "EndOfGame":
                # Reset message_sent when we leave EndOfGame phase
                message_sent = False
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.RequestException,
            RuntimeError,
            LeagueClientDisconnected,
        ):
            # Set a flag to indicate the client disconnected (don't print here, main thread handles it)
            shared_state.client_disconnected = True
            break
        except Exception as e:
            print(f"❌ Error in end game actions: {e}")
            # Continue running for other types of errors
        time.sleep(3)
