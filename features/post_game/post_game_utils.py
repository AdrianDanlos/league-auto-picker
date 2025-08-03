import requests
from features.pick_and_ban import game_data
from lcu_connection import auth, base_url
from utils import get_rank_data


def fetch_ranked_tiers_and_divisions():
    """
    Fetch ranked tiers and divisions from Data Dragon API.
    Returns a dictionary with tier information and their divisions.
    """
    try:
        # Get the latest version from Data Dragon
        version_response = requests.get(
            "https://ddragon.leagueoflegends.com/api/versions.json"
        )
        version_response.raise_for_status()
        version = version_response.json()[0]

        # Fetch ranked data from Data Dragon
        ranked_data_url = (
            f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/ranked.json"
        )
        ranked_response = requests.get(ranked_data_url)
        ranked_response.raise_for_status()

        ranked_data = ranked_response.json()

        # Extract tiers and divisions
        tiers_and_divisions = {}

        # Data Dragon ranked data structure may vary, so we'll create a comprehensive mapping
        # Standard ranked tiers in League of Legends
        standard_tiers = {
            "IRON": ["IV", "III", "II", "I"],
            "BRONZE": ["IV", "III", "II", "I"],
            "SILVER": ["IV", "III", "II", "I"],
            "GOLD": ["IV", "III", "II", "I"],
            "PLATINUM": ["IV", "III", "II", "I"],
            "EMERALD": ["IV", "III", "II", "I"],
            "DIAMOND": ["IV", "III", "II", "I"],
            "MASTER": [],
            "GRANDMASTER": [],
            "CHALLENGER": [],
        }

        # If Data Dragon provides specific tier data, use it
        if "tiers" in ranked_data:
            for tier_info in ranked_data["tiers"]:
                tier_name = tier_info.get("name", "").upper()
                divisions = tier_info.get("divisions", [])
                if tier_name and divisions:
                    tiers_and_divisions[tier_name] = divisions
        else:
            # Fallback to standard tiers
            tiers_and_divisions = standard_tiers

        return {"tiers_and_divisions": tiers_and_divisions, "version": version}

    except requests.RequestException as e:
        print(f"Error fetching ranked data from Data Dragon: {e}")
        # Return standard tiers as fallback
        return {
            "tiers_and_divisions": {
                "IRON": ["IV", "III", "II", "I"],
                "BRONZE": ["IV", "III", "II", "I"],
                "SILVER": ["IV", "III", "II", "I"],
                "GOLD": ["IV", "III", "II", "I"],
                "PLATINUM": ["IV", "III", "II", "I"],
                "EMERALD": ["IV", "III", "II", "I"],
                "DIAMOND": ["IV", "III", "II", "I"],
                "MASTER": [],
                "GRANDMASTER": [],
                "CHALLENGER": [],
            },
            "version": "fallback",
        }
    except Exception as e:
        print(f"Unexpected error in fetch_ranked_tiers_and_divisions: {e}")
        return None


def save_pre_game_lp(queue_type):
    # save these 3 values (tier, division, lp) into global value that can be used anytime in the code
    rank_data = get_rank_data(base_url, auth, queue_type)
    global pre_game_lp
    pre_game_lp = {
        "tier": rank_data.get("tier"),
        "division": rank_data.get("division"),
        "lp": rank_data.get("lp"),
    }


def get_last_game_data():
    """
    Get the last game data and extract win/loss status, champion played, and KDA.

    Returns:
        Dictionary containing:
        - win_loss: Dictionary with win status and result
        - champion: Dictionary with champion information
        - kda: Dictionary with KDA statistics
        - error: Error message if something goes wrong
    """
    try:
        # Get the last game data from the api
        response = requests.get(
            f"{base_url}/lol-match-history/v1/products/lol/current-summoner/matches",
            auth=auth,
            verify=False,
        )

        if response.status_code != 200:
            return {"error": f"Failed to get match history: {response.status_code}"}

        match_history = response.json()

        # Check if there are any games
        if not match_history.get("games", {}).get("games", []):
            return {"error": "No games found in match history"}

        # Get the most recent game (first in the list)
        latest_game = match_history["games"]["games"][0]

        # Get current summoner's summonerId to find their participant ID
        summoner_response = requests.get(
            f"{base_url}/lol-summoner/v1/current-summoner",
            auth=auth,
            verify=False,
        )

        if summoner_response.status_code != 200:
            return {
                "error": f"Failed to get current summoner: {summoner_response.status_code}"
            }

        current_summoner = summoner_response.json()
        current_summoner_id = current_summoner["summonerId"]

        # Find the current player's participant ID
        current_participant_id = None
        for participant_identity in latest_game["participantIdentities"]:
            if participant_identity["player"]["summonerId"] == current_summoner_id:
                current_participant_id = participant_identity["participantId"]
                break

        if current_participant_id is None:
            return {"error": "Could not find current player in the game"}

        # Import the utility functions from formatthis.py
        from tests.formatthis import (
            get_win_loss_status,
            get_champion_played,
            get_kda_stats,
        )

        # Get win/loss status
        win_loss = get_win_loss_status(latest_game, current_participant_id)
        if not win_loss:
            return {"error": "Could not get win/loss status"}

        # Get champion information
        champion = get_champion_played(latest_game, current_participant_id)
        if not champion:
            return {"error": "Could not get champion information"}

        # Get KDA statistics
        kda = get_kda_stats(latest_game, current_participant_id)
        if not kda:
            return {"error": "Could not get KDA statistics"}

        return {
            "win_loss": win_loss,
            "champion": champion,
            "kda": kda,
            "game_id": latest_game["gameId"],
            "game_duration": latest_game["gameDuration"],
            "game_mode": latest_game["gameMode"],
            "queue_id": latest_game["queueId"],
        }

    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def get_rank_changes():
    ranked_tiers_and_divisions = fetch_ranked_tiers_and_divisions()

    # Get current (post-game) rank data
    tier, division, lp = get_rank_data(
        base_url, auth, game_data.get("queueType")
    ).values()
    current_tier = tier
    current_division = division
    current_lp = lp

    # Get pre-game rank data
    pre_tier = pre_game_lp.get("tier")
    pre_division = pre_game_lp.get("division")
    pre_lp = pre_game_lp.get("lp")

    # Use the fetched ranked tiers and divisions data
    tiers_data = ranked_tiers_and_divisions.get("tiers_and_divisions", {})

    # Extract tier order from the data
    tier_order = list(tiers_data.keys())

    # Define division order for comparison (standard across all tiers)
    division_order = ["IV", "III", "II", "I"]

    def get_tier_value(tier_name):
        """Get numerical value for tier comparison"""
        if tier_name in tier_order:
            return tier_order.index(tier_name)
        return -1

    def get_division_value(div_name):
        """Get numerical value for division comparison"""
        if div_name in division_order:
            return division_order.index(div_name)
        return -1

    def calculate_rank_difference(
        pre_tier, pre_division, pre_lp, current_tier, current_division, current_lp
    ):
        """Calculate the difference in rank between pre-game and post-game"""

        # Handle special cases for Master+ tiers (no divisions)
        if pre_tier in ["MASTER", "GRANDMASTER", "CHALLENGER"] and current_tier in [
            "MASTER",
            "GRANDMASTER",
            "CHALLENGER",
        ]:
            pre_rank_value = get_tier_value(pre_tier)
            current_rank_value = get_tier_value(current_tier)
            return current_rank_value - pre_rank_value

        # Handle promotion from Diamond to Master+
        if pre_tier == "DIAMOND" and pre_division == "I" and pre_lp >= 100:
            if current_tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
                return get_tier_value(current_tier) - get_tier_value("DIAMOND")

        # Handle demotion from Master+ to Diamond
        if current_tier == "DIAMOND" and current_division == "I":
            if pre_tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
                return get_tier_value("DIAMOND") - get_tier_value(pre_tier)

        # Standard tier/division comparison
        pre_tier_value = get_tier_value(pre_tier)
        current_tier_value = get_tier_value(current_tier)

        # If tiers are different, calculate based on tier difference
        if pre_tier_value != current_tier_value:
            tier_diff = current_tier_value - pre_tier_value
            return tier_diff

        # Same tier, compare divisions
        pre_div_value = get_division_value(pre_division)
        current_div_value = get_division_value(current_division)

        if pre_div_value != current_div_value:
            div_diff = current_div_value - pre_div_value
            return div_diff

        # Same tier and division, compare LP
        return current_lp - pre_lp

    # Calculate the rank difference
    rank_difference = calculate_rank_difference(
        pre_tier, pre_division, pre_lp, current_tier, current_division, current_lp
    )

    # Determine if it's a promotion, demotion, or LP change
    if rank_difference > 0:
        change_type = "promotion"
        change_description = f"Promoted from {pre_tier} {pre_division} to {current_tier} {current_division}"
    elif rank_difference < 0:
        change_type = "demotion"
        change_description = f"Demoted from {pre_tier} {pre_division} to {current_tier} {current_division}"
    else:
        change_type = "lp_change"
        lp_change = current_lp - pre_lp
        if lp_change > 0:
            change_description = (
                f"Gained {lp_change} LP in {current_tier} {current_division}"
            )
        elif lp_change < 0:
            change_description = (
                f"Lost {abs(lp_change)} LP in {current_tier} {current_division}"
            )
        else:
            change_description = f"No LP change in {current_tier} {current_division}"

    return {
        "pre_game": {"tier": pre_tier, "division": pre_division, "lp": pre_lp},
        "post_game": {
            "tier": current_tier,
            "division": current_division,
            "lp": current_lp,
        },
        "change_type": change_type,
        "change_description": change_description,
        "rank_difference": rank_difference,
        "lp_change": current_lp - pre_lp,
    }
