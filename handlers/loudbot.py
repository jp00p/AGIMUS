import errno
from common import *
from utils.string_utils import *


PERCENTAGE_THRESHOLD = 10

# handle_loudbot(message) - responds to uppercase messages
# message[required]: discord.Message
async def handle_loudbot(message:discord.Message):

  if message.author.bot:
    return

  if "loudbot" not in config["handlers"]:
    return

  if not config["handlers"]["loudbot"]["enabled"]:
    return

  if not await get_enabled_setting(message):
    return

  allowed_channels = get_channel_ids_list(config["handlers"]["loudbot"]["allowed_channels"])
  if message.channel.id not in allowed_channels:
    return

  if is_loud(message.content):
    await put_shout(message)
    if random.randint(0,100) < PERCENTAGE_THRESHOLD:
      await message.reply(await get_shout())

async def get_enabled_setting(message):
  
  with AgimusDB() as query:
    sql = "SELECT loudbot_enabled FROM users WHERE discord_id = %s;"
    vals = (message.author.id,)
    query.execute(sql, vals)
    result = query.fetchone()
  return result[0]

async def get_shout():
  
  with AgimusDB() as query:
    sql = "SELECT shout FROM shouts ORDER BY RAND() LIMIT 1;"
    query.execute(sql)
    shout = query.fetchone()
    yell = shout[0]
  logger.info(f"YELL: {yell}")
  return yell

async def put_shout(message):
  message_content = strip_tags(message.content)
  message_content = re.sub(r'https?:\/\/\S*', '', message_content)
  logger.info("SHOUT: " + message_content)
  with AgimusDB() as query:
    sql = "INSERT IGNORE INTO shouts (user_discord_id, channel_id, shout) VALUES (%s, %s, %s)"
    vals = (message.author.id, message.channel.id, message_content)
    query.execute(sql, vals)
    last_id = query.lastrowid
  return last_id

