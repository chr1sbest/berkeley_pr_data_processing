"""
Before nightly processing
1) Get players and matches data from challonge -> store in "tournaments" collection
2) Build mock users records -> store in "users" collection

Nightly processing
1) Iterate over each user record. For each object in the user's "particpated_as" field,
   apply the user's facebook_id to all of the matches from that tournament.
2) Sort all tournaments by date
3) Build map of {fb_id: rating} -> run TrueSkill on matches chronologically.
4) Sort by rating to produce Rankings -> rankings.json 
5) Store all of that user's matches in their user record.
6) Upsert ratings to user records & upsert ranking to user record.
"""

users = [
    {
        u'_id': ObjectId('563ea53be843cd48d9e58889'),
        u'admin': False,
        u'facebook_id': u'glitter_facebook_id',
        u'participated_as': [{u'name': u'Glitter', u'tournament_id': 1976976}],
        u'primary_tag': u'Glitter'
    },
    {
        u'_id': ObjectId('563ea53be843cd48d9e5888a'),
        u'admin': False,
        u'facebook_id': u'ralph_facebook_id',
        u'participated_as': [{u'name': u'Ralph', u'tournament_id': 1976976}],
        u'primary_tag': u'Ralph'
    }
]

# Get all tournament data from mongo and hold a copy locally to modify
tournaments = [tourney for tourney in tournaments_collection.find()]

for user in users:
    fb_id = user['facebook_id']
    for participant_record in user['participated_as']:
        name = participant_record['name']
        tournament_id = participant_record['tournament']
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

# Replace tournament data
for tourney in tournaments:
    tourney_id = tourney['tournament_id']
    tournaments_collection.replace_one({'tournament_id': tourney_id}, tourney)


sorted_tournaments = tournaments.sort(lambda x: x['created_at'])
sorted_matches = 
