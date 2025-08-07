import requests
from features.discord_message import get_game_data
from utils import get_auth, get_base_url
from utils import get_rank_data

# Global variable to store pre-game LP data
pre_game_lp = {"tier": "Unknown", "division": "Unknown", "lp": 0}


def fetch_ranked_tiers_and_divisions():
    """
    Get ranked tiers and divisions for League of Legends.
    Returns a dictionary with tier information and their divisions.
    """
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

    return {
        "tiers_and_divisions": standard_tiers,
        "version": "standard",
    }


def save_pre_game_lp(queue_type):
    # save these 3 values (tier, division, lp) into global value that can be used anytime in the code
    rank_data = get_rank_data(queue_type)
    global pre_game_lp
    pre_game_lp = {
        "tier": rank_data.get("tier"),
        "division": rank_data.get("division"),
        "lp": rank_data.get("lp"),
    }


def get_win_loss_status(latest_game, participant_id):
    """
    Extract win/loss status for a specific participant from game data.

    Args:
        latest_game: The game data dictionary from the API
        participant_id: The participant ID to check

    Returns:
        Dictionary with win status and result, or None if not found
    """
    try:
        # Find the participant in the game
        participant = None
        for p in latest_game.get("participants", []):
            if p.get("participantId") == participant_id:
                participant = p
                break

        if not participant:
            return None

        # Check if the participant won
        won = participant.get("stats", {}).get("win", False)

        return {"won": won, "result": "Victory" if won else "Defeat"}
    except Exception as e:
        print(f"Error getting win/loss status: {e}")
        return None


def get_kda_stats(latest_game, participant_id):
    """
    Extract KDA statistics for a specific participant from game data.

    Args:
        latest_game: The game data dictionary from the API
        participant_id: The participant ID to check

    Returns:
        Dictionary with KDA statistics, or None if not found
    """
    try:
        # Find the participant in the game
        participant = None
        for p in latest_game.get("participants", []):
            if p.get("participantId") == participant_id:
                participant = p
                break

        if not participant:
            return None

        # Get KDA stats from participant stats
        stats = participant.get("stats", {})
        kills = stats.get("kills", 0)
        deaths = stats.get("deaths", 0)
        assists = stats.get("assists", 0)

        # Calculate KDA ratio (avoid division by zero)
        kda_ratio = (kills + assists) / deaths if deaths > 0 else (kills + assists)

        return {
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda_ratio": round(kda_ratio, 2),
        }
    except Exception as e:
        print(f"Error getting KDA statistics: {e}")
        return None


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
            f"{get_base_url()}/lol-match-history/v1/products/lol/current-summoner/matches",
            auth=get_auth(),
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
            f"{get_base_url()}/lol-summoner/v1/current-summoner",
            auth=get_auth(),
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

        # Get win/loss status
        win_loss = get_win_loss_status(latest_game, current_participant_id)
        if not win_loss:
            return {"error": "Could not get win/loss status"}

        # Get champion information
        game_data = get_game_data()
        champion = game_data["picked_champion"]
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

    # Get queue type from game_data, with fallback
    game_data = get_game_data()
    queue_type = game_data.get("queueType") if game_data else "RANKED_SOLO_5x5"

    # Get current (post-game) rank data
    current_rank_data = get_rank_data(queue_type)
    current_tier = current_rank_data.get("tier", "Unknown")
    current_division = current_rank_data.get("division", "Unknown")
    current_lp = current_rank_data.get("lp", 0)

    # Get pre-game rank data
    pre_tier = pre_game_lp.get("tier", "Unknown")
    pre_division = pre_game_lp.get("division", "Unknown")
    pre_lp = pre_game_lp.get("lp", 0)

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
