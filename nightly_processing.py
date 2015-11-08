"""
Before nightly processing
1) Get players and matches data from challonge -> store in "tournaments" collection
2) Build mock users records -> store in "users" collection

Nightly processing
1) Iterate over each user record. For each object in the user's "particpated_as" field,
   apply the user's facebook_id to all of the matches from that tournament.
2) Sort all tournaments by date
3) Build map of {fb_id: rating} -> run TrueSkill on matches chronologically.
4) Store all of that user's matches in their user record.
5) Sort by rating to produce Rankings -> rankings.json 
6) Upsert ratings to user records & upsert ranking to user record.
"""
import trueskill
import json
import pymongo

from collections import defaultdict

# Initialize pymongo pointers
client = pymongo.MongoClient()
tournaments_collection = client['production']['tournaments']
user_collection = client['production']['users']
users = [x for x in user_collection.find()]

# Get all tournament data from mongo and hold a copy locally to modify
tournaments = [tourney for tourney in tournaments_collection.find()]

# Iterate over each user and the tourneys they have participated in so that
# we can update info on those tournament matches to reflect this user's facebook id.
for user in users:
    fb_id = user['facebook_id']
    for participant_record in user['participated_as']:
        name = participant_record['name']
        tournament_id = participant_record['tournament_id']

        # Iterate over list of tournaments until we find the correct tournament
        # Would be ideal for tournaments to be in dict instead of list...
        for t in tournaments:
            if t['tournament_id'] == tournament_id:
                tourney = t
                break

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

# # Replace tournament data
# for tourney in tournaments:
#     tourney_id = tourney['tournament_id']
#     tournaments_collection.replace_one({'tournament_id': tourney_id}, tourney)

# Get a list of all matches sorted chronologically
tournaments.sort(lambda x: x['created_at'])
ratings_map = {}
for tournament in tournaments:
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

    # Clear placeholder tournament participants. Only keep fb_ids.
    ratings_map = {k: v for (k, v) in ratings_map.iteritems() if type(k) == unicode}


# Build map of {player: [matches]}
player_matches = defaultdict(list)
for tournament in tournaments:
    for match in tournament['matches']:
        winner, loser = match['match']['winner_id'], match['match']['loser_id']
        # If the participants of the match have facebook_ids (string) then we
        # will add their match to their list of matches.
        if type(winner) == unicode:
            player_matches[winner].append(match['match'])
        if type(loser) == unicode:
            player_matches[loser].append(match['match'])

# Update matches on user record
for fb_id, matches in player_matches.items():
    user_collection.update_one({'facebook_id': fb_id},
                           {'$set': {'matches': matches}})


# Sort ratings map by rating
all_ratings = [(key, val) for key, val in ratings_map.items()]
all_ratings.sort(reverse=True)

# Create rankings.json from map
rankings = []
for index, (fb_id, rating) in enumerate(all_ratings):
    rank = index + 1
    rankings.append({'id': fb_id, 'rating': rating.mu, 'rank': rank})
    # Update user data with new rank and rating
    user_collection.update_one({'facebook_id': fb_id},
                           {'$set': {'rank': rank, 'rating': rating.mu}})

with open('current_rankings.json', 'w') as ranking_file:
    ranking_file.write(json.dumps(rankings))
