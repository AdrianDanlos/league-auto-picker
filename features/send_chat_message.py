import requests
import random
import json
import threading

from utils.logger import log_and_discord
from utils import get_auth, get_base_url


def send_champ_select_message(session, message_override=None):
    # Load messages from config file
    with open("config.json", "r") as f:
        config = json.load(f)

    override = (
        message_override.strip()
        if isinstance(message_override, str) and message_override.strip()
        else None
    )
    if override:
        message = override
    else:
        messages = config.get("messages")
        if not isinstance(messages, list) or not messages:
            print("[Chat] No configured messages found. Skipping chat message.")
            return

        message = random.choice(messages)

    # Try to get the chatId from session
    chat_id = None
    if "chatDetails" in session:
        # Try both possible keys
        chat_id = session["chatDetails"].get("chatId") or session["chatDetails"].get(
            "multiUserChatId"
        )
    elif "chatId" in session:
        chat_id = session["chatId"]
    if chat_id:
        url = f"{get_base_url()}/lol-chat/v1/conversations/{chat_id}/messages"
        res = requests.post(url, json={"body": message}, auth=get_auth(), verify=False)
        if res.status_code == 200:
            print(f"[Chat] Sent message: {message}")
        else:
            log_and_discord(f"[Chat] Failed to send message: {res.status_code}, {res}")
    else:
        log_and_discord(
            f"[Chat] Could not find chatId in session. Session object:{session}"
        )


def schedule_champ_select_message(session, delay=20, message_override=None):
    """
    Schedule the champ select message to be sent after a delay without blocking the main thread.

    Args:
        session: The session object
        delay: Delay in seconds before sending the message (default: 20)
        message_override: If set, sent instead of a random entry from config \"messages\"
    """
    timer = threading.Timer(
        delay,
        send_champ_select_message,
        args=(session, message_override),
    )
    timer.start()
    print(f"[Chat] Scheduled message to be sent in {delay} seconds")
    return timer
