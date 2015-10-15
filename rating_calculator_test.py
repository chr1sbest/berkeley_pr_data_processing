import json
from rating_calculator import(build_player_map, process_match_data,
                              transform_ts_to_dict, transform_dict_to_ts)
from trueskill import Rating


# Load .json files locally instead of querying Challonge API
with open('matches.json', 'r') as matches_data:
    MATCHES = json.load(matches_data)

with open('players.json', 'r') as player_data:
    PLAYERS = json.load(player_data)


def test_player_map():
    pmap = build_player_map(PLAYERS)
    for id, player_object in pmap.items():
        # Test that all players are set to rating 0
        assert player_object['rating'].mu == 0


def test_transform_ts_to_dict():
    pmap = build_player_map(PLAYERS)
    #TODO


def test_transform_dict_to_ts():
    pmap = build_player_map(PLAYERS)
    #TODO


def test_process_map_data():
    pass
    #TODO
