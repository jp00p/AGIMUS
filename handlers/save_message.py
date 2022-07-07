from common import *
from wordcloud import STOPWORDS

# save_message_to_db() - saves a users message to the database after doing some cleanup on the message 
# strips emoji and converts message to basic ascii, shuffles words in message, sorts words in message
async def save_message_to_db(message:discord.Message):
  
  blocked_channels = get_channel_ids_list(config["handlers"]["save_message"]["blocked_channels"])
  if message.channel.id in blocked_channels:
    return
  
  user = get_user(message.author.id)
  if user["log_messages"] == 1:
    message_content = message.content.encode("ascii", errors="ignore").decode().strip()
    message_randomized = message_content.split(" ")
    random.shuffle(message_randomized)
    message_randomized = sorted(message_randomized)
    message_content = " ".join(message_randomized)
    remove_emoji = re.compile('<.*?>')
    message_content = re.sub(remove_emoji, '', message_content) # strip discord emoji from message
    chars = re.escape(string.punctuation)
    message_content = re.sub(r'['+chars+']', '', message_content) # strip special characters
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