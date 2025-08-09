import requests
from features.discord_message import get_game_data
from utils import get_auth, get_base_url
from utils import get_rank_data
from utils import shared_state
from utils.lcu_connection import get_session


def save_pre_game_lp(queue_type):
    if get_session() is None:
        return

    # save these 3 values (tier, division, lp) into global value that can be used anytime in the code
    rank_data = get_rank_data(queue_type)
    shared_state.pre_game_lp = {
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


def fetch_last_game_data():
    """
    Fetch the last game data from the api
    """
    try:
        response = requests.get(
            f"{get_base_url()}/lol-match-history/v1/products/lol/current-summoner/matches",
            auth=get_auth(),
            verify=False,
        )

        match_history = response.json()
        return match_history["games"]["games"][0]
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def get_summoner_id():
    """
    Get the summoner id from the api
    """
    response = requests.get(
        f"{get_base_url()}/lol-summoner/v1/current-summoner",
        auth=get_auth(),
        verify=False,
    )
    return response.json()["summonerId"]


def sanitize_last_game_data():
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
        latest_game_data = fetch_last_game_data()
        summoner_id = get_summoner_id()

        # Find the current player's participant ID
        participant_id = get_participant_id(latest_game_data, summoner_id)

        if participant_id is None:
            return {"error": "Could not find current player in the game"}

        # Get win/loss status
        win_loss = get_win_loss_status(latest_game_data, participant_id)
        if not win_loss:
            return {"error": "Could not get win/loss status"}

        # Get champion information
        game_data = get_game_data()
        champion = game_data["picked_champion"]
        if not champion:
            return {"error": "Could not get champion information"}

        # Get KDA statistics
        kda = get_kda_stats(latest_game_data, participant_id)
        if not kda:
            return {"error": "Could not get KDA statistics"}

        return {
            "win_loss": win_loss,
            "champion": champion,
            "kda": kda,
            "game_id": latest_game_data["gameId"],
            "game_duration": latest_game_data["gameDuration"],
            "game_mode": latest_game_data["gameMode"],
            "queue_id": latest_game_data["queueId"],
        }

    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def get_rank_changes():
    # Get queue type from game_data, with fallback
    game_data = get_game_data()
    queue_type = game_data.get("queueType")

    # Get current (post-game) rank data
    current_rank_data = get_rank_data(queue_type)
    current_tier = current_rank_data.get("tier", "Unknown")
    current_division = current_rank_data.get("division", "Unknown")
    current_lp = current_rank_data.get("lp", 0)

    # Get pre-game rank data
    pre_division = shared_state.pre_game_lp.get("division", "Unknown")
    pre_lp = shared_state.pre_game_lp.get("lp", 0)

    latest_game_data = fetch_last_game_data()
    summoner_id = get_summoner_id()
    participant_id = get_participant_id(latest_game_data, summoner_id)
    win_loss = get_win_loss_status(latest_game_data, participant_id)
    lp_change = calculate_lp_change(
        win_loss, pre_division, current_division, pre_lp, current_lp
    )

    return {
        "post_game": {
            "tier": current_tier,
            "division": current_division,
            "lp": current_lp,
        },
        "lp_change": lp_change,
    }


def calculate_lp_change(win_loss, pre_division, current_division, pre_lp, current_lp):
    if win_loss.get("won", False):
        if current_division == pre_division:
            return current_lp - pre_lp
        else:
            return 100 - pre_lp + current_lp

    else:
        if current_division == pre_division:
            return current_lp - pre_lp
        else:
            return current_lp - pre_lp - 100


def get_participant_id(latest_game, summoner_id):
    for participant_identity in latest_game["participantIdentities"]:
        if participant_identity["player"]["summonerId"] == summoner_id:
            return participant_identity["participantId"]
    return None
