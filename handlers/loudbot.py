import errno
from common import *
from utils.string_utils import *


# handle_loudbot(message) - responds to uppercase messages
# message[required]: discord.Message
async def handle_loudbot(message:discord.Message):
  
  if message.author.bot:
    return

  if "loudbot" not in config["handlers"]:
    return

  if not config["handlers"]["loudbot"]["enabled"]:
    return

  blocked_channels = get_channel_ids_list(config["handlers"]["loudbot"]["blocked_channels"])
  if message.channel.id in blocked_channels:
    return

  if is_loud(message.content):
    await put_shout(message)
    await message.reply(await get_shout())

async def get_shout():
  sql = "SELECT shout FROM shouts ORDER BY RAND() LIMIT 1;"
  db = getDB()
  query = db.cursor()
  query.execute(sql)
  shout = query.fetchone()
  yell = shout[0]
  logger.info(f"YELL: {yell}")
  return yell

async def put_shout(message):
  message_content = strip_tags(message.content)
  message_content = re.sub(r'https?:\/\/\S*', '', message_content)
  logger.info("SHOUT: " + message_content)
  db = getDB()
  query = db.cursor()
  sql = "INSERT IGNORE INTO shouts (user_discord_id, channel_id, shout) VALUES (%s, %s, %s)"
  vals = (message.author.id, message.channel.id, message_content)
  query.execute(sql, vals)
  last_id = query.lastrowid
  db.commit()
  query.close()
  db.close()
  return last_id
  
