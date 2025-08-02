import requests

from features.send_discord_error_message import log_and_discord


def select_default_runes(base_url, auth):
    try:
        response = requests.post(
            f"{base_url}/lol-perks/v1/rune-recommender-auto-select",
            auth=auth,
            verify=False,
        )

        if response.status_code == 200 or response.status_code == 204:
            print("✅ Successfully set current rune page to reccommended one")
        else:
            log_and_discord(
                f"❌ Failed to set current rune page to reccomended one (Status: {response.status_code}, {response.text})"
            )

    except Exception as e:
        log_and_discord(f"❌ Unexpected error setting default runes and summs: {e}")


def select_summoner_spells(base_url, auth, config, champion, assigned_lane):
    # Get champion-specific summoner spells, fallback to Default if not found
    summs_config = config.get("summs", {}).get(assigned_lane, {})
    champion_summs = summs_config.get(champion, summs_config.get("Default", {}))

    try:
        response = requests.patch(
            f"{base_url}/lol-champ-select/v1/session/my-selection",
            auth=auth,
            json=champion_summs,
            verify=False,
        )

        if response.status_code == 200 or response.status_code == 204:
            print(f"✅ Successfully set the summoner spells:{champion_summs}")
        else:
            log_and_discord(
                f"❌ Failed to set the summoner spells (Status: {response.status_code}, {response.text})"
            )

    except Exception as e:
        log_and_discord(f"❌ Unexpected error setting default runes and summs: {e}")
