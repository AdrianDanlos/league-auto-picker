import time
import json
import urllib3
import threading

from features.post_game.end_of_game_actions import start_end_of_game_actions
from features.send_discord_message import (
    send_discord_pre_game_message,
)
from features.accept_queue import accept_queue
from features.pick_and_ban import pick_and_ban, game_data
from features.decline_swap_requests import decline_incoming_swap_requests
from features.swap_role import swap_role
from features.swap_pick_position import swap_pick_position
from features.send_chat_message import schedule_champ_select_message
from features.post_game.post_game_utils import save_pre_game_lp
from features.pick_and_ban import get_queueType
from lcu_connection import auth, base_url
from lcu_connection import get_session
from features.logger import logger

# Disable warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === Load config ===
with open("config.json") as f:
    config = json.load(f)


def wait_for_champ_select(base_url, auth):
    """Synchronous version - blocks until champ select starts"""
    while True:
        accept_queue(base_url, auth)
        # After accept_queue returns, get the champ select session
        # Wait 3 seconds before getting the session to let everything load
        time.sleep(3)
        session = get_session(base_url, auth)
        return session


def main():
    # Start logging system
    logger.start_logging()

    try:
        # Start end of game actions in a separate thread
        end_of_game_thread = threading.Thread(
            target=start_end_of_game_actions, args=(base_url, auth)
        )
        end_of_game_thread.daemon = True
        end_of_game_thread.start()

        while not get_session(base_url, auth):
            # Wait for a valid session (champ select)
            # This blocks until queue is accepted
            session = wait_for_champ_select(base_url, auth)

            # Save LP before game starts
            queue_type = get_queueType(session)
            save_pre_game_lp(queue_type)

            schedule_champ_select_message(session, base_url, auth)
            swap_role(session, base_url, auth, config)

            # Run concurrently in separate threads
            pick_ban_thread = threading.Thread(
                target=pick_and_ban, args=(base_url, auth, config)
            )
            swap_position_thread = threading.Thread(
                target=swap_pick_position, args=(base_url, auth)
            )

            handle_incoming_swap_requests_thread = threading.Thread(
                target=decline_incoming_swap_requests, args=(base_url, auth)
            )

            pick_ban_thread.daemon = True
            swap_position_thread.daemon = True
            handle_incoming_swap_requests_thread.daemon = True

            pick_ban_thread.start()
            swap_position_thread.start()
            handle_incoming_swap_requests_thread.start()

            # Wait for threads to complete (they will run until champ select ends)
            pick_ban_thread.join()
            swap_position_thread.join()
            handle_incoming_swap_requests_thread.join()

            send_discord_pre_game_message(base_url, auth, game_data)

            print("🟡 Session ended. Stopping pick and ban monitoring.")

            time.sleep(1)
    finally:
        # Stop logging system
        logger.stop_logging()


if __name__ == "__main__":
    main()  # Remove asyncio.run()
