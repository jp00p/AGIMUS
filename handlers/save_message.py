from common import *
from utils import string_utils
from wordcloud import STOPWORDS

# save_message_to_db() - saves a users message to the database after doing some cleanup on the message 
# strips emoji and converts message to basic ascii, shuffles words in message, sorts words in message
# used for wordcloud only at the moment!
async def save_message_to_db(message:discord.Message):
  
  blocked_channels = get_channel_ids_list(config["handlers"]["save_message"]["blocked_channels"])
  if message.channel.id in blocked_channels:
    return
  
  user = get_user(message.author.id)
  if user["log_messages"] and user["log_messages"] == 1:
    
    # convert message to plaintext
    message_content = string_utils.plaintext(message.content)

    message_modified = set(message_content.split(" "))

    # sort words (obfuscation in db)
    message_modified = sorted(list(message_modified))

    # combine back into string
    message_content = " ".join(message_modified)

    
    message_content = string_utils.strip_emoji(message_content)
    message_content = string_utils.strip_urls(message_content)
    message_content = string_utils.strip_punctuation(message_content)
    message_content = message_content.replace("  ", " ") # convert double spaces to single space
    message_content = message_content.strip()
    
    if message_content.strip() == "":
      return None

    with AgimusDB() as query:
      sql = "INSERT INTO message_history (user_discord_id, channel_id, message_text) VALUES (%s, %s, %s)"
      vals = (message.author.id, message.channel.id, message_content)
      query.execute(sql, vals)
      last_id = query.lastrowid
    return last_id