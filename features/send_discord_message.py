import requests
from urllib.parse import quote
from features.send_discord_error_message import log_and_discord
from utils import get_gameflow_phase, get_rank_data

webhook_url = "https://discord.com/api/webhooks/1400894060276748448/qflPvLqhtoymtnU4o9br3grXkV4HJIl2WYtTAY6BQ2__D5MyAbZqpv-FsW3lEKjPcAN2"


def send_discord_post_game_message(game_data, rank_changes):
    try:
        data = {"game_data": game_data, "rank_changes": rank_changes}

        response = requests.post(webhook_url, json=data)

        if response.status_code == 204:
            print("✅ Discord message sent with post game stats")
        else:
            log_and_discord(
                f"❌ Error sending discord message with post game stats: {response.status_code}"
            )
    except Exception as e:
        log_and_discord(
            f"❌ Unexpected error sending discord message with post game stats: {e}"
        )


def send_discord_pre_game_message(base_url, auth, game_data):
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
