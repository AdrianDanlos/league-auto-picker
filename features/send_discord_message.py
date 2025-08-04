import requests
from urllib.parse import quote
from features.send_discord_error_message import log_and_discord
from utils import get_gameflow_phase, get_rank_data

webhook_url = "https://discord.com/api/webhooks/1400894060276748448/qflPvLqhtoymtnU4o9br3grXkV4HJIl2WYtTAY6BQ2__D5MyAbZqpv-FsW3lEKjPcAN2"


def send_discord_post_game_message(last_game_data, rank_changes, summoner_name):
    try:
        print("🟡 last_game_data: ", last_game_data)
        print("🟡 rank_changes: ", rank_changes)

        # Extract data from last_game_data
        win_loss = last_game_data.get("win_loss", {})
        champion = last_game_data.get("champion", {})
        kda = last_game_data.get("kda", {})

        # Extract data from rank_changes
        post_game = rank_changes.get("post_game", {})
        lp_change = rank_changes.get("lp_change", 0)

        # Format the content string
        result_emoji = "✅" if win_loss.get("won", False) else "❌"
        result_text = "Victory" if win_loss.get("won", False) else "Defeat"

        # KDA calculation
        kills = kda.get("kills", 0)
        deaths = kda.get("deaths", 0)
        assists = kda.get("assists", 0)
        kda_ratio = round((kills + assists) / max(deaths, 1), 2)

        # Rank information
        tier = post_game.get("tier", "Unknown")
        division = post_game.get("division", "Unknown")
        current_lp = post_game.get("lp", 0)

        # LP change with sign
        lp_change_text = f"+{lp_change}" if lp_change > 0 else f"{lp_change}"

        # Build the formatted content
        content = (
            "```diff\n"
            f"🎮 {summoner_name}\n\n"
            f"{result_emoji} {result_text} – {champion} | {lp_change_text} LP\n\n"
            f"⚔️ KDA: {kills}/{deaths}/{assists} ({kda_ratio})\n\n"
            f"🏆 {tier} {division} / {current_lp} LP"
            "```"
        )

        data = {"content": content}

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
        tier, division, wins, loses, lp = get_rank_data(
            base_url, auth, game_data.get("queueType", "Unknown")
        ).values()
        gameflow_phase = get_gameflow_phase(base_url, auth)
        print("🟡 gameflow_phase before sending dc message: ", gameflow_phase)
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
