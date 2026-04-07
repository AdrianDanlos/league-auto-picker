from utils.champion_utils import get_final_local_champion_id_from_session


def test_final_champion_prefers_myteam_over_pick_action():
    """After a trade, myTeam reflects the new champion; pick action may still show the old one."""
    session = {
        "localPlayerCellId": 2,
        "myTeam": [
            {"cellId": 0, "championId": 10},
            {"cellId": 2, "championId": 157},
        ],
        "actions": [
            [
                {
                    "actorCellId": 2,
                    "type": "pick",
                    "completed": True,
                    "championId": 103,
                }
            ]
        ],
    }
    assert get_final_local_champion_id_from_session(session) == 157


def test_final_champion_falls_back_to_pick_when_myteam_slot_empty():
    session = {
        "localPlayerCellId": 1,
        "myTeam": [
            {"cellId": 1, "championId": 0},
        ],
        "actions": [
            [
                {
                    "actorCellId": 1,
                    "type": "pick",
                    "completed": True,
                    "championId": 84,
                }
            ]
        ],
    }
    assert get_final_local_champion_id_from_session(session) == 84


def test_final_champion_none_session():
    assert get_final_local_champion_id_from_session(None) is None


def test_final_champion_no_matching_data():
    session = {
        "localPlayerCellId": 9,
        "myTeam": [],
        "actions": [[]],
    }
    assert get_final_local_champion_id_from_session(session) is None
