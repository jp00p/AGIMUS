import aiohttp
from common import *
from utils.check_channel_access import access_check
from utils.timekeeper import check_timekeeper, set_timekeeper

@bot.slash_command(
  name="gifbomb",
  description="Send 3 randomized Gifs for your query to the channel"
)
@commands.check(access_check)
async def gifbomb(ctx:discord.ApplicationContext, query:str):
  await ctx.defer(ephemeral=True)
  channel = ctx.interaction.channel

  allowed = await check_timekeeper(ctx, 120)

  if allowed:
    await ctx.respond(
      embed=discord.Embed(
        title="BOMBS AWAY!!! 💣",
        color=discord.Color.blurple()
      )
    )

    async with aiohttp.ClientSession() as session:
      key = os.getenv('GOOGLE_API_KEY')
      client_key = os.getenv('GOOGLE_CX')
      params = {'q': query, 'key': key, 'client_key': client_key, 'limit': 13, 'contentfilter': 'medium'}
      async with session.get(
        "https://tenor.googleapis.com/v2/search",
        params=params
      ) as response:
        if response.status == 200:
          await ctx.respond(embed=discord.Embed(
              title="GIF BOMB!",
              description=f"{ctx.author.mention} lobs:\n\n> {query}",
              color=discord.Color.blurple()
            )
          )
          data = json.loads(await response.text())
          results = random.sample(data['results'], 3)
          for r in results:
            embed = discord.Embed(color=discord.Color.random())
            image_url = r['media_formats']['gif']['url']
            embed.set_image(url=image_url)
            embed.set_footer(text="via Tenor")
            await channel.send(embed=embed)
          set_timekeeper(ctx)
        else:
          await ctx.respond(embed=discord.Embed(
              title="Whoops",
              description="There was a problem requesting the Gifs from Tenor!",
              color=discord.Color.red()
            ), ephemeral=True
          )
  else:
    await ctx.followup.send(embed=discord.Embed(
        title="Denied!",
        description="Too soon since last gifbomb! Give it a minute, Turbo!",
        color=discord.Color.red()
      ), ephemeral=True
    )
