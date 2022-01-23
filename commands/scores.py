from .common import *

# scores() - Entrypoint for !scores command
# message[required]: discord.Message
# This function is the main entrypoint of the !scores command
# and will return the leaderboard for the top 25 players
async def scores(message:discord.Message):
  scores = get_high_scores()
  table = []
  table.append(["SCORE", "NAME", "SPINS", "JACKPOTS"])
  for player in scores:
    table.append([player["score"], player["name"], player["spins"], player["jackpots"]])
    #msg += "{0} - {1} (Spins: {2} Jackpots: {3})\n".format(player["score"], player["name"], player["spins"], player["jackpots"])
  msg = tabulate(table, headers="firstrow")
  await message.channel.send("```"+msg+"```")


# get_high_scores()
# This function takes no arguments
# and returns the top 25 users ordered by their score value
def get_high_scores():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM users ORDER BY score DESC LIMIT 25"
  query.execute(sql)
  scores = query.fetchall()
  return scores
