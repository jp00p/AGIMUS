from common import *

def get_random_weyounsday_meme():
  memes = [
    "https://i.imgur.com/jbtLVZc.gif",
    "https://i.imgur.com/JOb8GUB.png",
    "https://i.imgur.com/cR7tTY4.png",
    "https://i.imgur.com/EDrONLC.png",
    "https://i.imgur.com/HEBw3KL.png",
    "https://i.imgur.com/rUaPKCV.jpeg",
    "https://i.imgur.com/1RdyWlC.png",
    "https://i.imgur.com/p8mCLSt.png",
    "https://i.imgur.com/RIsuDEo.jpeg",
    "https://i.imgur.com/1KSqnuo.png",
    "https://i.imgur.com/Ry7bKz4.png",
    "https://i.imgur.com/1wlwrwO.png",
    "https://i.imgur.com/MhjmltM.png",
    "https://i.imgur.com/XYyjXwZ.jpeg",
    "https://i.imgur.com/7ERyRzd.png",
    "https://i.imgur.com/BEAh7wt.png",
    "https://i.imgur.com/QEkxYW5.png",
    "https://i.imgur.com/7lKla53.jpeg",
    "https://i.imgur.com/DMChNoP.png",
    "https://i.imgur.com/ivXRHrv.png"
  ]

  return random.choice(memes)

def weyounsday_task(bot):

  async def weyounsday():
    enabled = config["tasks"]["weyounsday"]["enabled"]
    if not enabled:
      return

    embed = discord.Embed(
      title="It's Weyounsday My Dudes!",
      color=discord.Color.blurple()
    )
    embed.set_image(url=get_random_weyounsday_meme())
    channel_ids = get_channel_ids_list(config["tasks"]["weyounsday"]["channels"])
    for channel_id in channel_ids:
      channel = bot.get_channel(channel_id)
      await channel.send(embed=embed)

  return {
    "task": weyounsday,
    "crontab": config["tasks"]["weyounsday"]["crontab"]
  }

