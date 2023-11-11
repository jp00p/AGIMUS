import aiohttp
from common import *
from utils.check_role_access import role_check

@bot.slash_command(
  name="gifbomb",
  description="Send the Top 5 Gifs for your query to the channel"
)
@option(
  "query",
  str,
  description="Gif Search",
  required=True
)
@commands.check(role_check)
async def aliases(ctx:discord.ApplicationContext, query:str):
  await ctx.defer(ephemeral=True)
  channel = ctx.interaction.channel

  async with aiohttp.ClientSession() as session:
    key = os.getenv('GOOGLE_API_KEY')
    async with session.get(
      "https://tenor.googleapis.com/v2/search?q=%s&key=%s&client_key=%s&limit=5&contentfilter=medium" % (query, key)
    ) as response:
      if response.status == 200:
        await ctx.respond(embed=discord.Embed(
            title="GIF BOMB!",
            color=discord.color.blurple()
          ), ephemeral=False
        )
        data = json.loads(await response.text())
        results = data['results']
        for i in results:
          embed = discord.Embed(color=discord.Color.random())
          embed.set_image(results[i]['gif']['url'])
          embed.set_footer(text="via Tenor")
          await channel.send(embed=embed)
      else:
        await ctx.respond(embed=discord.Embed(
            title="Whoops",
            description="There was a problem requesting the Gifs from Tenor!",
            color=discord.color.red()
          ), ephemeral=True
        )
