import json
from requests import get
from config import CHALLONGE_KEY
import pymongo

client = pymongo.MongoClient()

def get_tournament_data(tournament_id):
    """ Query challonge API for player and match details.

    :param tournament_id String: Challonge tournament ID
    :returns list, list: 
    """
    url = 'https://api.challonge.com/v1/tournaments/{}/{}.json'
    params = {'api_key': CHALLONGE_KEY, 'tournament_id': tournament_id}
    matches = get(url.format(tournament_id, 'matches'), params=params)
    players = get(url.format(tournament_id, 'participants'), params=params)

    return {
        'players': players,
        'matches': matches,
        'tournament_id': tournament_id,
        'created_at': players[-1]['created_at']
    }

def upload_tournament_data(data, client=client):
    tournaments_collection = client['production']['tournaments']
    tournaments_collection.insert(data)
