# flake8: noqa: E501
import requests


def send_champ_select_message(session, base_url, auth):
    message = "Let's win this so hard they uninstall the game!"

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
