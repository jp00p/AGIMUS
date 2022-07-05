import datetime

from common import *

# TODO: 
# react to original post?
# add more details to starboard post?

react_threshold = 3 # how many reactions required
argus_threshold = 10
user_threshold = 3 # how many users required

board_dict = config["handlers"]["starboard"]["boards"]
blocked_channels = get_channel_ids_list(config["handlers"]["starboard"]["blocked_channels"])
boards = get_channel_ids_list(board_dict.keys())


async def handle_starboard_reactions(payload:discord.RawReactionActionEvent):

  if payload.message_id in ALL_STARBOARD_POSTS:
    return

  # don't watch blocked channels, or the actual starboard channels
  if payload.channel_id in blocked_channels or payload.channel_id in boards or payload.member.bot:
    return

  channel = bot.get_channel(payload.channel_id)
  if channel.type != discord.ChannelType.text: # only textchannels work here for now
    return
  message = await channel.fetch_message(payload.message_id)
  reactions = message.reactions
  reacting_user = payload.member
  reaction = payload.emoji

  # don't count users adding reacts to their own posts
  if message.author == reacting_user:
    return
  
  # weird edge case where reaction can be a string (never seen it happen)
  if isinstance(reaction, str):
    logger.info(f"{Style.BRIGHT}{Fore.YELLOW}WHOA THE REACTION IS A STRING{Fore.RESET}{Style.RESET_ALL}")
    return

  # it might be safe to see if this is a starboard-worthy post now
  # each starboard can have a set of words to match against, 
  # here we loop over each board and then each word that board has
  for board,match_reacts in board_dict.items():
    
    if match_reacts:
      #logger.info(f"CHECKING {board}")
       
      all_reacts = reactions
      message_reaction_people = set()
      total_reacts_for_this_match = 0

      # loop over each matching word for this board
      for match in match_reacts:
        # loop over each reaction in the message
        for reaction in all_reacts:
          this_emoji = reaction.emoji
          if hasattr(this_emoji, "name"):           
            # if its a real emoji and has one of our words or matches exactly
            if re.search(r"([_]"+ re.escape(match)+")|("+ re.escape(match)+"[_])/igm", this_emoji.name.lower()) != None or this_emoji.name.lower() == match:
              # count the users who reacted with this one
              async for user in reaction.users():
                # if they haven't already reacted with one of the matching reactions, count this reaction
                if user != message.author and user not in message_reaction_people:
                  total_reacts_for_this_match += 1
                  message_reaction_people.add(user) # and don't count them again!
      
      
      #total_people = len(message_reaction_people)
      #logger.info(f"{Fore.LIGHTWHITE_EX}{Style.BRIGHT}{board}: report for this post {message.content}...: reacts {total_reacts_for_this_match} -- total reacting people: {total_people}{Style.RESET_ALL}{Fore.RESET}")

      # finally, if this match category has enough reactions and enough people, let's save it to the starboard channel!
      if total_reacts_for_this_match >= react_threshold and len(message_reaction_people) >= user_threshold:
        if await get_starboard_post(message.id, board) is None: # checking again just in case (might be expensive)
          await add_starboard_post(message, board)
  

async def add_starboard_post(message, board):
  global ALL_STARBOARD_POSTS

  #logger.info(f"ADDING A POST TO THE STARBOARD: {board}")
  # add post to DB
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO starboard_posts (message_id, user_id, board_channel) VALUES (%s, %s, %s);"
  vals = (message.id, message.author.id, board)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()
  
  ALL_STARBOARD_POSTS.append(message.id)
  
  board_channel = get_channel_id(board)

  # repost in appropriate board
  embed_description = f"{message.content}\n\n[View original message]({message.jump_url})"
  embed = discord.Embed(description=embed_description, color=discord.Color.random())
  embed.set_author(
    name=message.author.display_name,
    icon_url=message.author.avatar.url
  )

  date_posted = message.created_at.strftime("%A %B %-d, %Y")
  embed.set_footer(
    text=f"{date_posted}"
  )
  if len(message.attachments) > 0:
    embed.set_image(url=message.attachments[0].url)
  channel = bot.get_channel(board_channel)
  await channel.send(content=message.channel.mention, embed=embed)
  logger.info(f"{Fore.RED}AGIMUS{Fore.RESET} has added a post to the {board} channel! [Original post by {message.author.display_name} in {message.channel.name}")


async def get_starboard_post(message_id, board):
  #logger.info(f"CHECKING IF POST ALREADY EXISTS IN {board}")
  db = getDB()
  query = db.cursor()
  sql = "SELECT board_channel FROM starboard_posts WHERE message_id = %s and board_channel = %s"
  vals = (message_id, board)
  query.execute(sql, vals)
  message = query.fetchone()
  #logger.info(f"DB RESULT: {message}")
  db.commit()
  query.close()
  db.close()
  return message

def get_all_starboard_posts():
  posts = []
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT message_id FROM starboard_posts"
  query.execute(sql)
  for post in query.fetchall():
    posts.append(int(post["message_id"]))
  db.commit()
  query.close()
  db.close()
  return posts
