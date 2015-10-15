import json
from trueskill import rate_1vs1, Rating
from requests import get
from config import CHALLONGE_KEY

def get_tournament_data(tournament_id):
    """ Query challonge API for player and match details.

    :param tournament_id String: Challonge tournament ID
    :returns list, list: 
    """
    url = 'https://api.challonge.com/v1/tournaments/{}/{}.json'
    params = {'api_key': CHALLONGE_KEY, 'tournament_id': tournament_id}
    matches = get(url.format(tournament_id, 'matches'), params=params).json()
    players = get(url.format(tournament_id, 'participants'), params=params).json()

    return matches, players


def build_player_map(players):
    """
    :param players list: List of players with id/name data
    :returns dict: Dictionary of {'id': {'name', 'rating'}}
    """
    player_map = {}
    for player in players:
        player_id = player['participant']['id']
        name = player['participant']['name']
        # Initialize ratings for each player in player map
        player_map[player_id] = {'name': name, 'rating': Rating(0)}

    return player_map


def process_match_data(matches, player_map):
    for match_object in matches:
        match = match_object['match']
        player_1, player_2 = match['player1_id'], match['player2_id']
        player_1_rating = player_map[player_1]['rating']
        player_2_rating = player_map[player_2]['rating']

        winner = match['winner_id']
        if winner == player_1:
            player_1_rating, player_2_rating = rate_1vs1(player_1_rating, player_2_rating)
        else:
            player_2_rating, player_1_rating = rate_1vs1(player_2_rating, player_1_rating)

        # Update to new ratings
        player_map[player_1]['rating'] = player_1_rating
        player_map[player_2]['rating'] = player_2_rating
    return player_map

def transform_ts_to_dict(player_map):
    for player_id, player_object in player_map.items():
        sig, mu = player_object['rating'].sigma, player_object['rating'].mu
        player_object['rating'] = {'sigma': sig, 'mu': mu}
    return player_map

def transform_dict_to_ts(player_map):
    for player_id, player_object in player_map.items():
        sig, mu = player_object['rating']['sigma'], player_object['rating']['mu']
        player_object['rating'] = Rating(sigma=sig, mu=mu)
    return player_map

if __name__ == "__main__":
    tourney_id = '1976976'
    matches, players = get_tournament_data(tourney_id)
    pmap = build_player_map(players)
    pmap = process_match_data(matches, pmap)
    pmap = transform_ts_to_dict(pmap)
    import ipdb; ipdb.set_trace()
    print pmap
