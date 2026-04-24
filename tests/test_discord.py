import requests
import psutil
import re
import os
from dotenv import load_dotenv

load_dotenv()


def get_lcu_credentials():
    """Get League Client credentials from running process"""
    for proc in psutil.process_iter(["cmdline"]):
        if proc.info["cmdline"] and "LeagueClientUx.exe" in proc.info["cmdline"][0]:
            cmdline = " ".join(proc.info["cmdline"])
            port = re.search(r"--app-port=(\d+)", cmdline).group(1)
            token = re.search(r"--remoting-auth-token=([\w-]+)", cmdline).group(1)
            return port, token
    raise RuntimeError("League client not found.")


webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

# Initialize variables with default values
tier = "UNRANKED"
division = ""
wins = 0
loses = 0

try:
    # Get LCU credentials
    port, token = get_lcu_credentials()
    base_url = f"https://127.0.0.1:{port}"
    auth = requests.auth.HTTPBasicAuth("riot", token)

    r = requests.get(
        f"{base_url}/lol-ranked/v1/current-ranked-stats", auth=auth, verify=False
    )

    # Parse the JSON response
    stats_data = r.json()
    print(f"🔍 stats: {stats_data}")

    # Extract ranked stats
    if "queueMap" in stats_data and "RANKED_SOLO_5x5" in stats_data["queueMap"]:
        ranked_data = stats_data["queueMap"]["RANKED_SOLO_5x5"]
        tier = ranked_data.get("tier", "UNRANKED")
        division = ranked_data.get("division", "")
        wins = ranked_data.get("wins", 0)
        loses = ranked_data.get("losses", 0)

except Exception as e:
    print(f"❌ Error getting stats: {e}")

# Mensaje que quieres enviar
mensaje = (
    "```ansi\n"
    "\u001b[1;32m🎮 ═══ GAME STARTED ═══ 🎮\u001b[0m\n"
    "```\n"
    "👤 **Player:** `N3 Machine`\n"
    "⚔️ **Champion:** `Kled`\n"
    "🛡️ **Role:** `Top Lane`\n\n"
    "🏆 **Good luck and have fun!** 🏆\n"
    "🌍 **Porofessor:** <https://porofessor.gg/live/euw/n3%20essential-0000>\n"
    f"📊 **Rank:** {tier} {division} | **Wins:** {wins} | **Losses:** {loses}"
)

data = {"content": mensaje}

if not webhook_url:
    print("⚠️ DISCORD_WEBHOOK_URL is not set. Skipping send.")
else:
    response = requests.post(webhook_url, json=data)

    if response.status_code == 204:
        print("✅ Mensaje enviado con éxito")
    else:
        print(f"❌ Error al enviar mensaje: {response.status_code}")
        print(f"❌ Error al enviar mensaje: {response.text}")
