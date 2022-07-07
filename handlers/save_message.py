from common import *

async def save_message_to_db(message:discord.Message):
  user = get_user(message.author.id)
  if user["log_messages"] == 1:
    message_content = message.content.encode("ascii", errors="ignore").decode().strip()
    remove_emoji = re.compile('<.*?>')
    message_content = re.sub(remove_emoji, '', message_content)
    if message_content.strip() == "":
      return None

    db = getDB()
    query = db.cursor()
    sql = "INSERT INTO message_history (user_discord_id, channel_id, message_text) VALUES (%s, %s, %s)"
    vals = (message.author.id, message.channel.id, message_content)
    query.execute(sql, vals)
    last_id = query.lastrowid
    db.commit()
    query.close()
    db.close()
    return last_id