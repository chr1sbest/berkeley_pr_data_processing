import json
from IPython.core.debugger import Tracer
from trueskill import rate_1vs1, Rating
from requests import get
from config import CHALLONGE_KEY
from pprint import pprint

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


def add_uids_to_players(players):
    """ Adds global user_id to players gotten from get_tournament_data and dumps to file
    Currently no way to merge players who enter as different tags
    
    :param players List: list of players
    """
    for player in players:
        player['participant']['user_id'] = player['participant']['name'].lower()
    filename = str(players[0]['participant']['tournament_id']) + '.json'
    with open(filename, 'w') as outfile:
        json.dump(players, outfile)
     


def get_player_ids_consolidated(*jsonFiles):
    """ Gets player ids from all tournaments

    :param jsonFiles from tournaments
    :returns dictionary {player_id (from one tourney) : user_id (across all tourneys)}
    """
    pids = []
    playerIds = {}
    for tournament in jsonFiles:
        idsFromTourney = get_player_ids(tournament)
        for ids in idsFromTourney:
            playerIds[ids] = idsFromTourney[ids]
    return playerIds


def get_player_ids(jsonFile):
    """ Gets user_ids from Json File. Helper function for the get_player_ids_consolidated function

    :param Json File String: name of the json file as a string
    :returns dictionary of {player_id from tournament : user_id}
    """
    with open(jsonFile) as data:
        players = json.load(data)
    player_ids = {}
    for player in players:
        player_ids[player['participant']['id']] = player['participant']['user_id']
    return player_ids


def get_all_matches(*tournament_ids):
    """ Gets all the matches from all tournaments
    :param tournament ids of all tournaments that we want data from
    :returns list of all matches across tournaments inputted
    """
    tournament_data = []
    matchList = []
    for tournament in tournament_ids:
        matches2, players = get_tournament_data(tournament)
        for match in matches2:
            matchList.append(match)
    return matchList


def player_page_helper(playerPages):
    """ Takes playerPage dictionary with matches from players in different tournies and consoldiates them under 1 player
    :params playerPages dictionary
    :returns consolidated dictionary
    """
    seenBefore = {}
    finalPages = {}
    for player in playerPages:
        if playerPages[player]['user_id'] not in finalPages:
            finalPages[playerPages[player]['user_id']] = {}
            finalPages[playerPages[player]['user_id']]['user_id'] = playerPages[player]['user_id']
            finalPages[playerPages[player]['user_id']]['matches'] = []
            finalPages[playerPages[player]['user_id']]['matches'] = playerPages[player]['matches']
        else:
            for match2 in playerPages[player]['matches']:
                finalPages[playerPages[player]['user_id']]['matches'].append(match2)
    for page in finalPages:
        win = 0
        loss = 0
        for match in finalPages[page]['matches']:
            if match['outcome'] == 'win':
                win += 1
            else:
                loss += 1
        finalPages[page]['winloss'] = str(win) + '/' + str(loss)
        finalPages[page]['matchesPlayed'] = len(finalPages[page]['matches'])
    with open('finalpages.json', 'w') as outfile:
        json.dump(finalPages, outfile)
    return finalPages

def get_player_page(player_ids, matches):
    """ Using player ids, creates player page.
    Player page has date, tournament, outcome, player, w/l ratio

    :param Json with player_ids added
    :returns dictionary playerPages with {player_id: matches}
    Tournament name is currently hard-coded, can't figure out how to relate tournament id int into string form

    """
    playerPages = {}
    for player in player_ids:
        playerPages[player] = {}
        playerPages[player]['user_id'] = player_ids[player]
        playerPages[player]['matches'] = []
        curMatch = []
        for match in matches:
            if player == match['match']['player1_id'] or player == match['match']['player2_id']:
                if player == match['match']['player1_id']:
                    opponent = match['match']['player2_id']
                else:
                    opponent = match['match']['player1_id']
                opponent = player_ids[opponent]
                winner = match['match']['winner_id']
                if winner == player:
                    outcome = 'win'
                else:
                    outcome = 'loss'
                tournament = match['match']['tournament_id']
                if str(tournament) == '1976976':
                    tournament = 'bw1'
                if str(tournament) == '1924093':
                    tournament = 'bw2'
                if str(tournament) == '1995306':
                    tournament = 'bw3'
                else:
                    tournament = 'hacks$'
                date = match['match']['created_at']
                curMatch= {'opp' : opponent, 'outcome' : outcome, 'tournament' : tournament, 'date': date}
                playerPages[player]['matches'].append(curMatch)
    #write to json
    #with open('player_ids_test.json', 'w') as outfile:
    #    json.dump(playerPages, outfile)
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
    tourney_id = 'sabfa2015bw1'
    matches, players = get_tournament_data(tourney_id)
    pmap = build_player_map(players)
    pmap = process_match_data(matches, pmap)
    pmap = transform_ts_to_dict(pmap)
    t1,t2,t3,t4 = 'sabfa2015bw1', 'sabfa2015bw2', 'calhacksmoney', 'sabfa2015bw3'
    matchList = get_all_matches(t1,t2,t3,t4)
    pids = get_player_ids_consolidated('bw2User_id.json', 'hacksmoneyUser_ids.json', '1924093.json', '1995306.json')
    playerPages = get_player_page(pids, matchList)
    final = player_page_helper(playerPages)
