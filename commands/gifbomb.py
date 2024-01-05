import aiohttp
from common import *
from utils.check_role_access import role_check
from utils.check_channel_access import access_check

@bot.slash_command(
  name="gifbomb",
  description="Send the 3 Gifs for your query to the channel"
)
@commands.check(access_check)
@commands.check(role_check)
async def gifbomb(ctx:discord.ApplicationContext, query:str):
  await ctx.defer(ephemeral=False)
  channel = ctx.interaction.channel

  async with aiohttp.ClientSession() as session:
    key = os.getenv('GOOGLE_API_KEY')
    ckey = os.getenv('GOOGLE_CX')
    async with session.get(
      "https://tenor.googleapis.com/v2/search?q=%s&key=%s&client_key=%s&limit=3&contentfilter=medium&random=true" % (query, key, ckey)
    ) as response:
      if response.status == 200:
        await ctx.respond(embed=discord.Embed(
            title="GIF BOMB!",
            color=discord.Color.blurple()
          ), ephemeral=False
        )
        data = json.loads(await response.text())
        results = data['results']
        for r in results:
          embed = discord.Embed(color=discord.Color.random())
          image_url = r['media_formats']['gif']['url']
          embed.set_image(url=image_url)
          embed.set_footer(text="via Tenor")
          await channel.send(embed=embed)
      else:
        await ctx.respond(embed=discord.Embed(
            title="Whoops",
            description="There was a problem requesting the Gifs from Tenor!",
            color=discord.Color.red()
          ), ephemeral=True
        )
