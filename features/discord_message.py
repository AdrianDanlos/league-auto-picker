import requests
import time
import os
from urllib.parse import quote
from dotenv import load_dotenv
from utils.logger import log_and_discord
from utils import get_gameflow_phase, get_rank_data, LeagueClientDisconnected
from utils import (
    get_assigned_lane,
    get_region,
    get_queueType,
    get_summoner_name,
)
from utils import shared_state

load_dotenv()

_IN_GAME_PHASES = frozenset({"GameStart", "InProgress", "Reconnect"})


def _post_to_discord_with_retries(content, max_attempts=3, delay_seconds=1.5):
    """Post message to Discord with retry support for transient failures."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return False

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                webhook_url,
                json={"content": content},
                timeout=(4, 10),
            )
            if response.status_code == 204:
                return True

            if response.status_code == 429:
                retry_after = delay_seconds
                if response.headers.get("Content-Type", "").startswith(
                    "application/json"
                ):
                    payload = response.json()
                    retry_after = payload.get("retry_after", delay_seconds)
                time.sleep(max(retry_after, delay_seconds))
                continue

            # Retry 5xx errors; log and stop for other HTTP statuses.
            if 500 <= response.status_code < 600 and attempt < max_attempts:
                time.sleep(delay_seconds)
                continue

            log_and_discord(
                f"❌ Error sending discord message: {response.status_code} - {response.text}"
            )
            return False
        except requests.exceptions.RequestException as e:
            if attempt < max_attempts:
                time.sleep(delay_seconds)
                continue
            log_and_discord(f"❌ Error sending discord message after retries: {e}")
            return False

    return False


def send_discord_post_game_message(last_game_data, rank_changes, summoner_name):
    try:
        player_name = summoner_name or "Player"

        # If rank_changes is None (client disconnected), don't send the message
        if rank_changes is None:
            return False

        # If upstream data fetch is not ready yet, retry on next poll.
        if not isinstance(last_game_data, dict) or last_game_data.get("error"):
            return False

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
            f"🎮 {player_name}\n\n"
            f"{result_emoji} {result_text} – {champion} | {lp_change_text} LP\n\n"
            f"⚔️ KDA: {kills}/{deaths}/{assists} ({kda_ratio})\n\n"
            f"🏆 {tier} {division} / {current_lp} LP"
            "```"
        )

        if _post_to_discord_with_retries(content):
            print("✅ Discord message sent with post game stats")
            return True
        return False
    except LeagueClientDisconnected:
        return False
    except Exception as e:
        log_and_discord(
            "❌ Unexpected error sending discord message "
            f"with post game stats: {e}"
        )
        return False


def send_discord_pre_game_message(game_data):
    try:
        rank_data = get_rank_data(game_data.get("queueType", "Unknown"))
        tier = rank_data.get("tier", "Unknown")
        division = rank_data.get("division", "Unknown")
        wins = rank_data.get("wins", 0)
        loses = rank_data.get("loses", 0)
        # Phase can stay in GameStart briefly before moving to InProgress.
        phase_retries = 90
        while phase_retries > 0:
            gameflow_phase = get_gameflow_phase()
            if gameflow_phase in _IN_GAME_PHASES:
                break
            phase_retries -= 1
            time.sleep(1)
        else:
            return False

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
            f"📊 **Rank:** {tier} {division} | "
            f"**Wins:** {wins} | **Losses:** {loses}\n\n"
            f"🌍 **Porofessor:** <{porofessor_url}>\n"
            f"🌍 **OPGG:** <{opgg_url}>\n\n\n"
        )

        if _post_to_discord_with_retries(styled_content):
            print("✅ Discord message sent")
            return True
        return False

    except LeagueClientDisconnected:
        return False
    except Exception as e:
        log_and_discord(f"❌ Unexpected error sending discord message: {e}")
        return False


def send_discord_champ_select_started_message(session):
    """Send a lightweight Discord message when champion select starts."""
    try:
        player_name = get_summoner_name(session) or "Player"
        content = (
            "```ansi\n"
            f"\u001b[1;32m🎮 ═══ CHAMP SELECT STARTED ═══ 🎮\u001b[0m\n"
            "```\n"
            f"👤 **Player:** `{player_name}`\n"
            "⚔️ **Status:** Champion select is live!"
        )
        if _post_to_discord_with_retries(content):
            print("✅ Discord champ select start message sent")
    except LeagueClientDisconnected:
        return
    except Exception as e:
        log_and_discord(
            "❌ Unexpected error sending champ select start "
            f"discord message: {e}"
        )


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


def create_discord_message(best_pick, session):
    """Create Discord message data for the picked champion."""
    # Make the variable accessible to the entrypoint
    shared_state.game_data["picked_champion"] = best_pick
    shared_state.game_data["summoner_name"] = get_summoner_name(session)
    shared_state.game_data["assigned_lane"] = get_assigned_lane(session)
    shared_state.game_data["region"] = get_region(session)
    shared_state.game_data["queueType"] = get_queueType(session)


def get_game_data():
    """Get the current game data for Discord messaging."""
    return shared_state.game_data
