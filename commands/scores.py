from common import *
from utils.check_channel_access import access_check

@bot.slash_command(
  name="scores",
  description="Get the leaderboard for the top 25 players"
)
@commands.check(access_check)
async def scores(ctx:discord.ApplicationContext):
  """
  This function is the main entrypoint of the /scores command
  """
  scores = get_high_scores()
  # table = []
  # table.append(["SCORE", "NAME", "SPINS", "JACKPOTS"])
  embed = discord.Embed(
    title="Scores Leaderboard",
    description="Top 25 Players",
    color=discord.Color.blurple()
  )
  for idx, player in enumerate(scores):
    embed.add_field(
      name=f"#{idx+1} - {player['name']}",
      value=f"Score: **{player['score']}** - Spins: **{player['spins']}** - Jackpots: **{player['jackpots']}**",
      inline=False
    )
    # table.append([player["score"], player["name"], player["spins"], player["jackpots"]])
  # msg = tabulate(table, headers="firstrow")
  # await ctx.respond("```"+msg+"```")
  await ctx.respond(embed=embed)


def get_high_scores():
  """
  returns the top 25 users ordered by their score value
  """
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM users ORDER BY score DESC LIMIT 25"
  query.execute(sql)
  scores = query.fetchall()
  return scores
