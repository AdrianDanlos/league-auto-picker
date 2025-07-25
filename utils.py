# flake8: noqa: E501
def get_pick_order(session, cell_id):
    """
    Returns the pick order (1-based index) for the given cell_id based on your team's pick actions.
    """
    actions = session.get("actions", [])
    my_team_cell_ids = {p["cellId"] for p in session.get("myTeam", [])}
    pick_order = 1
    for action_group in actions:
        for action in action_group:
            if action["type"] == "pick" and action["actorCellId"] in my_team_cell_ids:
                if action["actorCellId"] == cell_id:
                    return pick_order
                pick_order += 1
    return None