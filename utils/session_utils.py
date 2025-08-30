from constants import FLEX_CODE, SOLOQ_CODE


def get_assigned_lane(session):
    """Get the player's assigned lane from the session."""
    my_cell_id = session.get("localPlayerCellId")
    for participant in session.get("myTeam", []):
        if participant.get("cellId") == my_cell_id:
            return participant.get("assignedPosition")
    return None


def get_enemy_champions(session, champion_ids):
    """Get list of enemy champions that have been picked."""
    enemy_champions = []
    their_team = session.get("theirTeam", [])

    for participant in their_team:
        # Check if they have picked a champion
        if participant.get("championId") and participant.get("championId") != 0:
            # Convert champion ID to name
            champion_name = get_champion_name_by_id(
                participant.get("championId"), champion_ids
            )
            if champion_name:
                enemy_champions.append(champion_name)

    return enemy_champions


def get_banned_champion_ids(session):
    """Get list of banned champion IDs from the session."""
    banned_champs = [
        action["championId"]
        for phase in session["actions"]
        for action in phase
        if action["type"] == "ban" and action["completed"]
    ]
    return banned_champs


def get_region(session):
    """Get the region from the session."""
    return session["chatDetails"]["mucJwtDto"].get("targetRegion")


def get_queueType(session):
    """Get the queue type from the session."""
    queue_type = session.get("queueId", 0)
    if queue_type == SOLOQ_CODE:
        return "RANKED_SOLO_5x5"
    elif queue_type == FLEX_CODE:
        return "RANKED_FLEX_SR"
    return None


def is_still_our_turn_to_pick(session, my_cell_id):
    """Check if it's still our turn to pick."""
    actions = session.get("actions", [])

    print(f"[DEBUG] Checking if still our turn for cell_id: {my_cell_id}")

    # Debug: print all actions and their status
    for group_idx, action_group in enumerate(actions):
        print(f"[DEBUG] Action group {group_idx}:")
        for action_idx, action in enumerate(action_group):
            if action["type"] == "pick":
                print(
                    f"  Action {action_idx}: cellId={action['actorCellId']}, isInProgress={action['isInProgress']}, type={action['type']}"
                )

    for action_group in actions:
        for action in action_group:
            if (
                action["actorCellId"] == my_cell_id
                and action["isInProgress"]
                and action["type"] == "pick"
            ):
                print("[DEBUG] Found our active pick action - returning True")
                return True

    print("[DEBUG] No active pick action found for our cell_id - returning False")
    return False


def get_champion_name_by_id(champion_id, champion_ids):
    """Convert champion ID to name using the reverse mapping from champion_ids."""
    # Create reverse mapping from the existing champion_ids dict
    id_to_name = {v: k for k, v in champion_ids.items()}
    return id_to_name.get(champion_id)


def get_summoner_name(session):
    local_player_cell_id = session.get("localPlayerCellId")

    # Find your player info in myTeam
    for player in session.get("myTeam", []):
        if player["cellId"] == local_player_cell_id:
            game_name = player.get("gameName", "")
            tag_line = player.get("tagLine", "")

            if game_name and tag_line:
                # FIXME: This is porofessor and opgg format. If we intend to reuse this function we should be careful not to break the link
                return f"{game_name}-{tag_line}"
            elif game_name:
                return game_name
