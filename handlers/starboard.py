from commands.common import *

react_threshold = 3 # how many reactions required
argus_threshold = 10
user_threshold = 3 # how many users required

board_dict = config["handlers"]["starboard"]["boards"]
blocked_channels = get_channel_ids_list(config["handlers"]["starboard"]["blocked_channels"])
boards = get_channel_ids_list(board_dict.keys())


async def handle_starboard_reactions(payload:discord.RawReactionActionEvent):  

  # don't watch blocked channels, or the actual starboard channels
  if payload.channel_id in blocked_channels or payload.channel_id in boards or payload.member.bot:
    return True

  channel = client.get_channel(payload.channel_id)
  if channel.type != discord.ChannelType.text: # only textchannels work here for now
    return True
  message = await channel.fetch_message(payload.message_id)
  reactions = message.reactions
  reacting_user = payload.member
  reaction = payload.emoji

  

  # don't count users adding reacts to their own posts
  if message.author == reacting_user:
    return True
  
  # weird edge case where reaction can be a string (never seen it happen)
  if isinstance(reaction, str):
    logger.info(f"{Style.BRIGHT}{Fore.YELLOW}WHOA THE REACTION IS A STRING{Fore.RESET}{Style.RESET_ALL}")
    return True

  # don't bother doing anything if there's not enough reactons total
  if len(reactions) < react_threshold:
    logger.info("Total reactions: " + len(reactions))
    return True

  for board, match_reacts in board_dict.items():
    if check_starboard_post_exists(message.id, board) is not None:
      return True


  # it might be safe to see if this is a starboard-worthy post now
  # each starboard can have a set of words to match against, 
  # here we loop over each board and then each word that board has
  for board,match_reacts in board_dict.items():
    
    if match_reacts:
      logger.info(f"CHECKING {board}")
       
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
                  message_reaction_people.add(user) # and don't count it again!
      
      
      total_people = len(message_reaction_people)
      logger.info(f"{Fore.LIGHTWHITE_EX}{Style.BRIGHT}{board}: report for this post {message.content}...: reacts {total_reacts_for_this_match} -- total reacting people: {total_people}{Style.RESET_ALL}{Fore.RESET}")

      # finally, if this match category has enough reactions and enough people, let's save it to the starboard channel!
      if total_reacts_for_this_match >= react_threshold and len(message_reaction_people) >= user_threshold:
        if check_starboard_post_exists(message.id, board) is None: # checking again just in case (might be expensive)
          await add_starboard_post(message, board)
  
  return True # returning True so the reaction comes through anyway

async def add_starboard_post(message, board):
  logger.info(f"ADDING A POST TO THE STARBOARD: {board}")
  # add post to DB
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO starboard_posts (message_id, user_id, board_channel) VALUES (%s, %s, %s);"
  vals = (message.id, message.author.id, board)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

  board_channel = get_channel_id(board)

  # repost in appropriate board
  embed = discord.Embed(description=message.content)
  embed.set_author(
    name=message.author.display_name,
    icon_url=message.author.avatar_url
  )
  if len(message.attachments) > 0:
    embed.set_image(url=message.attachments[0].url)
  channel = client.get_channel(board_channel)
  await channel.send(content=message.channel.mention, embed=embed)


def check_starboard_post_exists(message_id, board):
  logger.info(f"CHECKING IF POST ALREADY EXISTS IN {board}")
  db = getDB()
  query = db.cursor()
  sql = "SELECT board_channel FROM starboard_posts WHERE message_id = %s and board_channel = %s"
  vals = (message_id, board)
  query.execute(sql, vals)
  message = query.fetchone()
  logger.info(f"DB RESULT: {message}")
  db.commit()
  query.close()
  db.close()
  return message
