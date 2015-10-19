import json
from IPython.core.debugger import Tracer
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
    matches = get(url.format(tournament_id, 'matches'), params=params)
    players = get(url.format(tournament_id, 'participants'), params=params)

    return matches.json(), players.json()

#def consolidate_user_ids(*jsonFiles):
#    """ Consolidates user_ids from many tournaments
#
#    """
#    consolidated_ids ={}
#    initial = 0
#    for jsonFile in jsonFiles:
#        if initial == 0:
#            consolidated_ids = get_player_ids(jsonFile)
#            continue
#        nextIdList = get_player_ids(jsonFile)
#            


def get_player_ids(jsonFile):
    """ Gets user_ids from Json File.

    :param Json File String: name of the json file as a string
    :returns dictionary of {player_id from tournament : user_id}
    """
    with open(jsonFile) as data:
        players = json.load(data)
    player_ids = {}
    for player in players:
        player_ids[player['participant']['id']] = player['participant']['user_id'], player['participant']['id']
    return player_ids

def get_player_page(player_ids):
    """ Using player ids, creates player page.

    :param Json with player_ids added
    :returns dictionary playerPages with {player_id: matches}
    Tournament name is currently hard-coded, can't figure out how to relate tournament id int into string form

    """
    
    playerPages = {}
    for player in player_ids:
        playerPages[player_ids[player][0]] = []
        curMatch = []
        for match in matches:
            if player == match['match']['player1_id'] or player ==match['match']['player2_id']:
                if player == match['match']['player1_id']:
                    opponent = match['match']['player2_id']
                else:
                    opponent = match['match']['player1_id']
                opponent = player_ids[opponent][0]
                winner = match['match']['winner_id']
                if winner == player:
                    outcome = 'win'
                else:
                    outcome = 'lose'
                tournament = match['match']['tournament_id']
                if str(tournament) == '1976976':
                    tournament = 'hacksmoney'
                
                curMatch= {'opp' : opponent, 'outcome' : outcome, 'tournament' : tournament}
                matches = {}
                playerPages[player_ids[player][0]].append(curMatch)
    #write to json
    with open('player_ids_test.json', 'w') as outfile:
        json.dump(playerPages, outfile)
    return playerPages
    


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
    """ Iterate over matches to recalculate trueskill ratings for each
    participant.

    :param players list: List of players with id/name data
    :param matches list: List of matches with player id's and winner_id
    :returns dict: Dictionary of {'id': {'name', 'rating'}}
    """
    for match_object in matches:
        match = match_object['match']
        player_1, player_2 = match['player1_id'], match['player2_id']
        player_1_rating = player_map[player_1]['rating']
        player_2_rating = player_map[player_2]['rating']

        # Recalculate TrueSkill ratings of the winner and loser
        winner = match['winner_id']
        if winner == player_1:
            player_1_rating, player_2_rating = rate_1vs1(player_1_rating, player_2_rating)
        else:
            player_2_rating, player_1_rating = rate_1vs1(player_2_rating, player_1_rating)

        # Update the new ratings
        player_map[player_1]['rating'] = player_1_rating
        player_map[player_2]['rating'] = player_2_rating

    return player_map


def transform_ts_to_dict(player_map):
    """ Serialize TrueSkill Ratingobjects into a dictionary """
    for player_id, player_object in player_map.items():
        sig, mu = player_object['rating'].sigma, player_object['rating'].mu
        player_object['rating'] = {'sigma': sig, 'mu': mu}
    return player_map


def transform_dict_to_ts(player_map):
    """ Deserialize python dictionary into respective TrueSkill Rating"""
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
    player_ids = get_player_ids('hacksmoneyUser_ids.json')
    playerPage = get_player_page(player_ids)

