import os
import re

import psutil
import pytest
import requests
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RUN_LCU_INTEGRATION = os.getenv("RUN_LCU_INTEGRATION_TESTS") == "1"
pytestmark = pytest.mark.skipif(
    not RUN_LCU_INTEGRATION,
    reason="Set RUN_LCU_INTEGRATION_TESTS=1 to run live LCU integration tests.",
)


def get_lcu_credentials():
    """Get League Client credentials from running process."""
    for proc in psutil.process_iter(["cmdline"]):
        if proc.info["cmdline"] and "LeagueClientUx.exe" in proc.info["cmdline"][0]:
            cmdline = " ".join(proc.info["cmdline"])
            port = re.search(r"--app-port=(\d+)", cmdline).group(1)
            token = re.search(r"--remoting-auth-token=([\w-]+)", cmdline).group(1)
            return port, token
    raise RuntimeError("League client not found.")


def test_send_discord_pre_game_message_live():
    """
    Optional live test that posts a sample pre-game style message to Discord.

    Requires:
      - RUN_LCU_INTEGRATION_TESTS=1
      - DISCORD_WEBHOOK_URL set
      - League client running locally
    """
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        pytest.skip("DISCORD_WEBHOOK_URL is required for this integration test.")

    tier = "UNRANKED"
    division = ""
    wins = 0
    losses = 0

    port, token = get_lcu_credentials()
    base_url = f"https://127.0.0.1:{port}"
    auth = requests.auth.HTTPBasicAuth("riot", token)

    ranked_stats_response = requests.get(
        f"{base_url}/lol-ranked/v1/current-ranked-stats",
        auth=auth,
        verify=False,
        timeout=10,
    )
    ranked_stats = ranked_stats_response.json()

    queue_map = ranked_stats.get("queueMap", {})
    soloq = queue_map.get("RANKED_SOLO_5x5", {})
    tier = soloq.get("tier", tier)
    division = soloq.get("division", division)
    wins = soloq.get("wins", wins)
    losses = soloq.get("losses", losses)

    message = (
        "```ansi\n"
        "\u001b[1;32m🎮 ═══ GAME STARTED ═══ 🎮\u001b[0m\n"
        "```\n"
        "👤 **Player:** `Sample Player`\n"
        "⚔️ **Champion:** `Kled`\n"
        "🛡️ **Role:** `Top Lane`\n\n"
        "🏆 **Good luck and have fun!** 🏆\n"
        "🌍 **Porofessor:** <https://porofessor.gg/live/euw/sample-0000>\n"
        f"📊 **Rank:** {tier} {division} | **Wins:** {wins} | **Losses:** {losses}"
    )

    response = requests.post(
        webhook_url,
        json={"content": message},
        timeout=10,
    )
    assert response.status_code == 204
