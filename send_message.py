import requests
import random
import json
import threading


def send_champ_select_message(session, base_url, auth):
    # Load messages from config file
    with open("config.json", "r") as f:
        config = json.load(f)

    messages = config.get("messages", [])
    if not messages:
        print("[Chat] No messages found in config file")
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
        url = f"{base_url}/lol-chat/v1/conversations/{chat_id}/messages"
        res = requests.post(url, json={"body": message}, auth=auth, verify=False)
        if res.status_code == 200:
            print(f"[Chat] Sent message: {message}")
        else:
            print(f"[Chat] Failed to send message: {res.status_code}, {res}")
    else:
        print("[Chat] Could not find chatId in session. Session object:")
        print(session)


def schedule_champ_select_message(session, base_url, auth, delay=15):
    """
    Schedule the champ select message to be sent after a delay without blocking the main thread.

    Args:
        session: The session object
        base_url: The base URL for the API
        auth: Authentication credentials
        delay: Delay in seconds before sending the message (default: 15)
    """
    timer = threading.Timer(
        delay, send_champ_select_message, args=(session, base_url, auth)
    )
    timer.start()
    print(f"[Chat] Scheduled message to be sent in {delay} seconds")
    return timer
