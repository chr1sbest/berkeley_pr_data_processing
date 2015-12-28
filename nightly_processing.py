"""
Get Data
==========
- Get players and matches data from challonge -> "tournaments" collection
- Get user records for tournaments they entered and the tags they have 
   participated as-> store in "users" collection

Fix Challonge Matches
==========
- For every match in every tourney, first we will replace all winner and loser id's
   with the tag that the player entered as.
- For each tag that the user has participated in a specific tourney as, we will
   apply the user's facebook_id to the winner/loser id for all matches from
   that tournament.

Apply TrueSkill Algorithm
=========
1) Sort all tournaments by date
2) Build map of {id: rating}. "id" is preferably facebook_id but can also be their
   tag that they have entered the tournament as.
3) Run TrueSkill on matches chronologically.

Upsert Data
=========
- Store all of a user's matches on their user record.
- Sort by rating to produce Rankings -> data/current_rankings.json 
- Upsert ratings to user records & upsert ranking to user record.
"""
import json
import pymongo
import trueskill

from collections import defaultdict

def update_all_tournament_matches(tournament):
    """ Update all tournament matches for a tournament to use the tag that the
    player entered as rather than an id. """
    # Build a map of player_id to player_name
    id_to_name = {}
    for player in tournament['players']:
        player_details = player['participant']
        id_to_name[player_details['id']] = \
            player_details['display_name_with_invitation_email_address']

    # Update winner and loser id to player_name from player_id
    for match_object in tournament['matches']:
        match = match_object['match']
        match['winner_id'] = id_to_name[match['winner_id']]
        match['loser_id'] = id_to_name[match['loser_id']]
    return tournament


def update_registered_user_matches(tournaments, user):
    """ Iterate over each user and the tourneys they have participated in so
    that we can update info on those tournament matches to reflect this user's
    facebook id. """
    fb_id = user['facebook_id']
    for participant_record in user['participated_as']:
        name = participant_record['name']
        tournament_id = participant_record['tournament_id']
        tourney = tournaments[tournament_id]

        # Iterate over list of players until we find the correct player
        # Would be ideal for participants to be in dict instead of list...
        for player in tourney['players']:
            if player['participant']['name'] == name:
                player_id = player['participant']['id']
                break

        # Iterate over matches and replace the player_id with facebook_id
        for match_object in tourney['matches']:
            match = match_object['match']
            # Replace id's with their facebook id
            if match['winner_id'] == player_id:
                match['winner_id'] = fb_id
            elif match['loser_id'] == player_id:
                match['loser_id'] = fb_id
    return tournaments


def update_player_trueskill(tournament, ratings_map):
    # Calculate TrueSkill from each map
    for match in tournament['matches']:
        winner, loser = match['match']['winner_id'], match['match']['loser_id']
        # If the user exists in our map, we will take their current rating.
        # Otherwise we will initialize a 0 Rating placeholder player.
        winner_rating = ratings_map.get(winner, trueskill.Rating(0))
        loser_rating = ratings_map.get(loser, trueskill.Rating(0))
        winner_rating, loser_rating = trueskill.rate_1vs1(winner_rating, loser_rating)
        # Update the dictionary with new ratings
        ratings_map[winner] = winner_rating
        ratings_map[loser] = loser_rating

    return ratings_map


def build_user_matches_list(tournament, player_matches):
    for match in tournament['matches']:
        winner, loser = match['match']['winner_id'], match['match']['loser_id']
        # If the participants of the match have facebook_ids (string) then we
        # will add their match to their list of matches.
        if type(winner) == unicode:
            player_matches[winner].append(match['match'])
        if type(loser) == unicode:
            player_matches[loser].append(match['match'])
    return player_matches


if __name__ == "__main__":
    # Initialize pointers to Mongo collections
    client = pymongo.MongoClient()
    tournaments_collection = client['production']['tournaments']
    user_collection = client['production']['users']

    users = [x for x in user_collection.find()]
    tournaments = {tourney['tournament_id']: tourney for \
                   tourney in tournaments_collection.find()}

    # Update tournaments to use player_name instead of player_id
    for tid, tournament in tournaments.items():
        tournaments[tid] = update_all_tournament_matches(tournament)

    # Update player_id to be facebook_id in all matches in all tournaments
    for user in users:
        update_registered_user_matches(tournaments, user)

    # Iterate over each tournament chronologically and update trueskill
    ordered_tournaments = tournaments.values()
    ordered_tournaments.sort(lambda x: x['created_at'])
    ratings_map = {}
    for tournament in ordered_tournaments:
        update_player_trueskill(tournament, ratings_map)

    # Update list of matches on each individual fb_user record
    player_matches = defaultdict(list)
    for tournament in ordered_tournaments:
        build_user_matches_list(tournament, player_matches)
    for fb_id, matches in player_matches.items():
        user_collection.update_one({'facebook_id': fb_id},
                                   {'$set': {'matches': matches}})

    # Update rankings for each user record and write to json file
    rankings = []
    all_ratings = [(key, val) for key, val in ratings_map.items()]
    all_ratings.sort(key=lambda x: x[1], reverse=True)
    for index, (fb_id, rating) in enumerate(all_ratings):
        rank = index + 1
        rankings.append({'id': fb_id, 'rating': rating.mu, 'rank': rank})
        # Update user data with new rank and rating
        update_command = {'$set': {'rank': rank, 'rating': rating.mu}}
        user_collection.update_one({'facebook_id': fb_id}, update_command)

    with open('data/current_rankings.json', 'w') as ranking_file:
        ranking_file.write(json.dumps(rankings))
