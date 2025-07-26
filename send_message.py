# flake8: noqa: E501
import requests
import random


def send_champ_select_message(session, base_url, auth):
    messages = [
        "yo team let's run it up - we bout to diff these kids",
        "sup team, time to gap them - this one's free",
        "waddup squad, let's farm some LP real quick",
        "ay team we finna smash these plebs no cap",
        "yooo let's get this dub, bout to be ez clap",
        "what's good team, time to int their mental fr",
        "lesgooo team we bout to turbo stomp - free win",
        "ay team let's cook these bots, gonna be a banger",
        "yoo squad time to gap check - they're not ready",
        "sup team we finna hard carry this lobby ngl",
    ]

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
            print(f"[Chat] Failed to send message: {res.status_code}")
    else:
        print("[Chat] Could not find chatId in session. Session object:")
        print(session)
