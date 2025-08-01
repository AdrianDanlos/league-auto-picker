import requests
from urllib.parse import quote

webhook_url = "https://discord.com/api/webhooks/1400894060276748448/qflPvLqhtoymtnU4o9br3grXkV4HJIl2WYtTAY6BQ2__D5MyAbZqpv-FsW3lEKjPcAN2"


def send_discord_message(base_url, auth, game_data):
    try:
        gameflow_phase = get_gameflow_phase(base_url, auth)
        if gameflow_phase == "InProgress":
            summoner_name = quote(game_data.get("summoner_name"))
            porofessor_url = build_porofessor_url(game_data.get("region"), summoner_name)
            opgg_url = build_opgg_url(game_data.get("region"), summoner_name)

            styled_content = (
                f"```ansi\n"
                f"\u001b[1;32m🎮 ═══ GAME STARTED ═══ 🎮\u001b[0m\n"
                f"```\n"
                f"👤 **Player:** `{game_data.get('summoner_name', 'Player')}`\n"
                f"⚔️ **Champion:** `{game_data.get('picked_champion', 'None')}`\n"
                f"🛡️ **Role:** `{game_data.get('assigned_lane', 'Unknown')}`\n\n"
                f"🌍 **Porofessor:** <{porofessor_url}>\n"
                f"🌍 **OPGG:** <{opgg_url}>\n\n\n"
            )

            data = {"content": styled_content}

            response = requests.post(webhook_url, json=data)

            if response.status_code == 204:
                print("✅ Discord message sent")
            else:
                print(f"❌ Error sending discord message: {response.status_code}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def get_gameflow_phase(base_url, auth):
    try:
        response = requests.get(
            f"{base_url}/lol-gameflow/v1/gameflow-phase",
            auth=auth,
            verify=False,
        )

        if response.status_code == 200 or response.status_code == 204:
            print("✅ phase: ", response.json())
            return response.json()
        else:
            print(f"❌ Failed to get phase {response.status_code}")
            if response.text:
                print(f"📝 Error response: {response.text}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def build_porofessor_url(region, summoner_name):
    return f"https://porofessor.gg/live/{region}/{summoner_name}"


def build_opgg_url(region, summoner_name):
    return f"https://op.gg/lol/summoners/{region}/{summoner_name}/ingame"
