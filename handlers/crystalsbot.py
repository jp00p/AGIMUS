from common import *
from utils.media_utils import get_media_file
from utils.string_utils import *

PERCENTAGE_THRESHOLD = 15

# handle_loudbot(message) - responds to uppercase messages
# message[required]: discord.Message
async def handle_crystalsbot(message:discord.Message):

  if message.author.bot:
    return

  if "crystalsbot" not in config["handlers"]:
    return

  if not config["handlers"]["crystalsbot"]["enabled"]:
    return

  allowed_channels = get_channel_ids_list(config["handlers"]["loudbot"]["allowed_channels"])
  if message.channel.id not in allowed_channels:
    return

  if is_crystals(message.content):
    if random.randint(0,100) < PERCENTAGE_THRESHOLD:
      if random.randint(0,100) < 25:
        try:
          drop_metadata = {
            "file": "data/drops/crystals.mp4",
            "description": "Crystals!",
            "url": "https://i.imgur.com/vKxEek3.mp4"
          }
          filename = get_media_file(drop_metadata)
          await message.reply(file=discord.File(filename))
        except Exception as err:
          pass
      else:
        crystals_replies = [
          "CRYSTALS!",
          "# CRYSTALS!"
          "## CRYSTALS!"
          "### CRYSTALS!"
          "-# CRYSTALS!"
        ]
        await message.reply(random.choice(crystals_replies))
