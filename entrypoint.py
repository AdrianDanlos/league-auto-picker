import time
import requests
import json
import urllib3
import psutil
import re
import threading

from features.send_discord_message import send_discord_message
from features.accept_queue import accept_queue
from features.pick_and_ban import pick_and_ban, game_data
from features.decline_swap_requests import decline_incoming_swap_requests
from features.swap_role import swap_role
from features.swap_pick_position import swap_pick_position
from features.send_chat_message import schedule_champ_select_message
from utils import get_session, logger

# Disable warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === Load config ===
with open("config.json") as f:
    config = json.load(f)


def get_lcu_credentials():
    for proc in psutil.process_iter(["cmdline"]):
        if proc.info["cmdline"] and "LeagueClientUx.exe" in proc.info["cmdline"][0]:
            cmdline = " ".join(proc.info["cmdline"])
            port = re.search(r"--app-port=(\d+)", cmdline).group(1)
            token = re.search(r"--remoting-auth-token=([\w-]+)", cmdline).group(1)
            return port, token
    raise RuntimeError("League client not found.")


def wait_for_champ_select(base_url, auth):
    """Synchronous version - blocks until champ select starts"""
    while True:
        accept_queue(base_url, auth)
        # After accept_queue returns, get the champ select session once
        session = get_session(base_url, auth)
        return session


port, token = get_lcu_credentials()
base_url = f"https://127.0.0.1:{port}"
auth = requests.auth.HTTPBasicAuth("riot", token)


def main():
    # Start logging system
    logger.start_logging()

    try:
        while not get_session(base_url, auth):
            # Wait for a valid session (champ select)
            # This blocks until queue is accepted
            session = wait_for_champ_select(base_url, auth)
            schedule_champ_select_message(session, base_url, auth)
            swap_role(session, base_url, auth, config)

            # Run concurrently in separate threads
            pick_ban_thread = threading.Thread(
                target=pick_and_ban, args=(base_url, auth, config)
            )
            swap_position_thread = threading.Thread(
                target=swap_pick_position, args=(base_url, auth)
            )

            decline_incoming_swap_requests_thread = threading.Thread(
                target=decline_incoming_swap_requests, args=(base_url, auth)
            )

            pick_ban_thread.daemon = True
            swap_position_thread.daemon = True
            decline_incoming_swap_requests_thread.daemon = True

            pick_ban_thread.start()
            swap_position_thread.start()
            decline_incoming_swap_requests_thread.start()

            # Wait for threads to complete (they will run until champ select ends)
            pick_ban_thread.join()
            swap_position_thread.join()
            decline_incoming_swap_requests_thread.join()

            send_discord_message(base_url, auth, game_data)
            print("🟡 Session ended. Stopping pick and ban monitoring.")

            time.sleep(1)
    finally:
        # Stop logging system
        logger.stop_logging()


if __name__ == "__main__":
    main()  # Remove asyncio.run()
