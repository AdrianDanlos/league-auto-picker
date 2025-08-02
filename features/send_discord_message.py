import requests
from urllib.parse import quote

from features.send_discord_error_message import log_and_discord

webhook_url = "https://discord.com/api/webhooks/1400894060276748448/qflPvLqhtoymtnU4o9br3grXkV4HJIl2WYtTAY6BQ2__D5MyAbZqpv-FsW3lEKjPcAN2"


def send_discord_message(base_url, auth, game_data):
    try:
        tier, division, wins, loses = get_rank_data(
            base_url, auth, game_data.get("queueType", "Unknown")
        ).values()
        gameflow_phase = get_gameflow_phase(base_url, auth)
        if gameflow_phase == "InProgress":
            summoner_name = quote(game_data.get("summoner_name", "Unknown"))
            region = game_data.get("region", "Unknown")

            porofessor_url = build_porofessor_url(region, summoner_name)
            opgg_url = build_opgg_url(region, summoner_name)

            styled_content = (
                f"```ansi\n"
                f"\n\n"
                f"\u001b[1;32m🎮 ═══ GAME STARTED ═══ 🎮\u001b[0m\n"
                f"```\n"
                f"👤 **Player:** `{game_data.get('summoner_name', 'Player')}`\n"
                f"⚔️ **Champion:** `{game_data.get('picked_champion', 'None')}`\n"
                f"🛡️ **Role:** `{game_data.get('assigned_lane', 'Unknown')}`\n"
                f"🏆 **Queue:** {game_data.get('queueType', 'Unknown')}\n"
                f"📊 **Rank:** {tier} {division} | **Wins:** {wins} | **Losses:** {loses}\n\n"
                f"🌍 **Porofessor:** <{porofessor_url}>\n"
                f"🌍 **OPGG:** <{opgg_url}>\n\n\n"
            )

            data = {"content": styled_content}

            response = requests.post(webhook_url, json=data)

            if response.status_code == 204:
                print("✅ Discord message sent")
            else:
                log_and_discord(
                    f"❌ Error sending discord message: {response.status_code}"
                )

    except Exception as e:
        log_and_discord(f"❌ Unexpected error sending discord message: {e}")


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
            log_and_discord(
                f"❌ Failed to get phase {response.status_code}, {response.text}"
            )

    except Exception as e:
        log_and_discord(f"❌ Unexpected error sending discord message: {e}")


def build_porofessor_url(region, summoner_name):
    region_converted = region
    if region == "eu1":
        region_converted = "euw"
    if region == "sa1":
        region_converted = "sg"

    return f"https://porofessor.gg/live/{region_converted}/{summoner_name}"


def build_opgg_url(region, summoner_name):
    region_converted = region
    if region == "eu1":
        region_converted = "euw"
    if region == "sa1":
        region_converted = "sea"
    return f"https://op.gg/lol/summoners/{region_converted}/{summoner_name}/ingame"


def get_rank_data(base_url, auth, queueType):
    try:
        response = requests.get(
            f"{base_url}/lol-ranked/v1/current-ranked-stats",
            auth=auth,
            verify=False,
        )

        if response.status_code == 200 or response.status_code == 204:
            player_data = response.json()
            ranked_data = player_data["queueMap"][queueType]
            return {
                "tier": ranked_data.get("tier", "Unknown"),
                "division": ranked_data.get("division", "Unknown"),
                "wins": ranked_data.get("wins", 0),
                "loses": ranked_data.get("losses", 0),
            }
        else:
            log_and_discord(
                f"❌ Failed to get rank data {response.status_code}, {response.text}"
            )

    except Exception as e:
        log_and_discord(f"❌ Unexpected error sending discord message: {e}")
