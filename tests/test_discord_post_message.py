import requests

webhook_url = "https://discord.com/api/webhooks/1400894060276748448/qflPvLqhtoymtnU4o9br3grXkV4HJIl2WYtTAY6BQ2__D5MyAbZqpv-FsW3lEKjPcAN2"


try:

    # create dummy game_data and rank_changes objs
    game_data = {
        "win_loss": {"won": True},
        "champion": {"name": "Kled"},
        "kda": {"kills": 10, "deaths": 5, "assists": 8},
    }
    rank_changes = {
        "post_game": {"tier": "IRON", "division": "IV", "lp": 100},
        "lp_change": 10,
    }

    summoner_name = "N3 Machine"

    # Extract data from game_data
    win_loss = game_data.get("win_loss", {})
    champion = game_data.get("champion", {})
    kda = game_data.get("kda", {})

    # Extract data from rank_changes
    post_game = rank_changes.get("post_game", {})
    lp_change = rank_changes.get("lp_change", 0)

    # Format the content string
    result_emoji = "✅" if win_loss.get("won", False) else "❌"
    result_text = "Victory" if win_loss.get("won", False) else "Defeat"
    champion_name = champion.get("name", "Unknown")

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
        f"{result_emoji} {result_text} – {champion_name} | {lp_change_text} LP\n\n"
        f"⚔️ KDA: {kills}/{deaths}/{assists} ({kda_ratio})\n\n"
        f"🏆 {tier} {division} / {current_lp} LP"
        "```"
    )

    data = {"content": content}

    response = requests.post(webhook_url, json=data)

    if response.status_code == 204:
        print("✅ Discord message sent with post game stats")
    else:
        print(
            f"❌ Error sending discord message with post game stats: {response.status_code}"
        )
except Exception as e:
    print(f"❌ Unexpected error sending discord message with post game stats: {e}")
