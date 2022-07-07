from common import *
from wordcloud import STOPWORDS

# save_message_to_db() - saves a users message to the database after doing some cleanup on the message 
# strips emoji and converts message to basic ascii, shuffles words in message, sorts words in message
async def save_message_to_db(message:discord.Message):
  
  blocked_channels = get_channel_ids_list(config["handlers"]["save_message"]["blocked_channels"])
  if message.channel.id in blocked_channels:
    return
  
  user = get_user(message.author.id)
  if user["log_messages"] and user["log_messages"] == 1:
    
    # convert message to plaintext
    message_content = message.content.encode("ascii", errors="ignore").decode().strip()

    message_modified = message_content.split(" ")

    # sort words (obfuscation in db)
    message_modified = sorted(list(message_modified))

    # combine back into string
    message_content = " ".join(message_modified)
    
    remove_emoji = re.compile('<.*?>')
    special_chars = re.escape(string.punctuation)
    
    message_content = re.sub(remove_emoji, '', message_content) # strip discord emoji from message
    message_content = re.sub(r'https?:\/\/\S*', '', message_content) # strip all URLs from the content
    message_content = re.sub(r'['+special_chars+']', '', message_content) # strip any remaining special characters
    message_content = message_content.replace("  ", " ") # convert double spaces to single space
    message_content = message_content.strip()
    
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