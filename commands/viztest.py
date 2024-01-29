import time
import plotly.graph_objects as go

from common import *
from utils.check_channel_access import access_check

@bot.slash_command(
  name="viztest",
  description="Testing, Testing"
)
@commands.check(access_check)
async def viztest(ctx:discord.ApplicationContext):
  await ctx.defer(ephemeral=True)
  d = {
    'ten-forward': 1000,
    'temba-his-arms-wide': 385,
    'animal-holophotography': 30,
    'general-trek': 939,
    'replimat': 399
  }

  sorted_data = sorted(d.items(), key=lambda x:x[1], reverse=True)
  labels = [t[0] for t in sorted_data]
  values = [t[1] for t in sorted_data]

  logger.info(f"labels: {labels}")
  logger.info(f"values: {values}")

  filename = f"fig-u{ctx.author.id}-t{int(time.time())}.png"
  filepath = f"./images/viz/{filename}"

  fig = go.Figure(data=[
    go.Pie(
      labels=labels,
      values=values,
      direction='clockwise',
      hole=.3,
      sort=False
    )
  ])
  fig.update_traces(
    textfont_size=20,
    marker=dict(
      colors=['#FF0000', '#B14110', '#FFFFFF', '#878787', '#1A1A1A'],
      line=dict(color='#000000', width=3)
    )
  )
  fig.update_layout(
    plot_bgcolor='rgba(0, 0, 0, 0)',
    paper_bgcolor='rgba(0, 0, 0, 0)',
    showlegend=False,
    margin=dict(
      t=0,
      b=0,
      l=0,
      r=0
    )
  )
  fig.write_image(filepath)

  while True:
    time.sleep(0.05)
    if os.path.isfile(filepath):
      break

  discord_image = discord.File(fp=filepath, filename=filename)
  embed = discord.Embed(
    title=f"Top Channels",
    description=f"{ctx.author.mention}'s Top Channels!",
    color=discord.Color.blurple()
  )
  embed.set_image
  embed.set_image(url=f"attachment://{filename}")
  await ctx.followup.send(embed=embed, file=discord_image)

