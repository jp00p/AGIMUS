from common import *

emojis = config["emojis"]

def get_random_weyounsday_meme():
  memes = [
    "https://i.imgur.com/jbtLVZc.gif",
    "https://i.imgur.com/JOb8GUB.png",
    "https://i.imgur.com/cR7tTY4.png"
  ]

  return random.choice(memes)

def weyounsday_task(client):

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
      channel = client.get_channel(id=channel_id)
      await channel.send(embed=embed)

  return {
    "task": weyounsday,
    "crontab": config["tasks"]["weyounsday"]["crontab"]
  }

