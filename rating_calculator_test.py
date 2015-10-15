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


def test_transforms():
    # Test initial Rating
    pmap = build_player_map(PLAYERS)
    first_player = pmap.keys()[0] # Rating of first id
    rating =  pmap[first_player]['rating']
    assert type(rating) == type(Rating())
    
    # Test that rating has been serialized to dict
    pmap = transform_ts_to_dict(pmap)
    first_player = pmap.keys()[0] # Rating of first id
    rating =  pmap[first_player]['rating']
    assert type(rating) == dict

    # Test that rating has been deserialized back to Rating
    pmap = transform_dict_to_ts(pmap)
    first_player = pmap.keys()[0] # Rating of first id
    rating =  pmap[first_player]['rating']
    assert type(rating) == type(Rating())


def test_process_map_data():
    pmap = build_player_map(PLAYERS)
    process_match_data(MATCHES, pmap)
    for id, player_object in pmap.items():
        # Test that players are no longer rated 0
        assert player_object['rating'].mu != 0
