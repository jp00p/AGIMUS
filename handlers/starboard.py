from utils import string_utils
from common import *
from copy import deepcopy
from handlers.xp import increment_user_xp

react_threshold = 3 # how many reactions required
high_react_threshold = 5
argus_threshold = 10 # not being used yet
user_threshold = 3 # how many users required

async def handle_starboard_reactions(payload:discord.RawReactionActionEvent) -> None:

  board_dict = config["handlers"]["starboard"]["boards"]
  blocked_channels = get_channel_ids_list(config["handlers"]["starboard"]["blocked_channels"])
  boards = get_channel_ids_list(board_dict.keys())

  if payload.message_id in ALL_STARBOARD_POSTS:
    return

  # don't watch blocked channels, or the actual starboard channels
  if payload.channel_id in blocked_channels or payload.channel_id in boards or payload.member.bot:
    return

  channel = bot.get_channel(payload.channel_id)
  if channel.type != discord.ChannelType.text: # only textchannels work here for now (FUTURE ME: now i'm trying to remember why...)
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
  # the words will be in the emoji name, not the message text
  for board,match_reacts in board_dict.items():

    if match_reacts:
      #logger.info(f"CHECKING {board}")

      all_reacts = reactions
      message_reaction_people = set()
      total_reacts_for_this_match = 0

      # loop over each matching word for this board (word is in emoji name)
      for match in match_reacts:
        # loop over each reaction in the message
        for reaction in all_reacts:
          this_emoji = reaction.emoji
          if hasattr(this_emoji, "name"):
            # if its a real emoji and has one of our words or matches exactly
            if re.search(r"([_]"+ re.escape(match)+")|("+ re.escape(match)+"[_])/igm", this_emoji.name.lower()) != None or this_emoji.name == match:
              # count the users who reacted with this one
              async for user in reaction.users():
                # if they haven't already reacted with one of the matching reactions, count this reaction
                if user != message.author and user not in message_reaction_people:
                  total_reacts_for_this_match += 1
                  message_reaction_people.add(user) # and don't count them again!

      #total_people = len(message_reaction_people)
      #logger.info(f"{Fore.LIGHTWHITE_EX}{Style.BRIGHT}{board}: report for this post {message.content}...: reacts {total_reacts_for_this_match} -- total reacting people: {total_people}{Style.RESET_ALL}{Fore.RESET}")

      # Some channels have a higher react threshold than others
      adjusted_react_threshold = react_threshold
      high_react_channel_ids = get_channel_ids_list(config["handlers"]["starboard"]["high_react_channels"])
      if payload.channel_id in high_react_channel_ids:
        adjusted_react_threshold = high_react_threshold
      await add_starboard_post(message, board)
      # finally, if this match category has enough reactions and enough people, let's save it to the starboard channel!
      if total_reacts_for_this_match >= adjusted_react_threshold and len(message_reaction_people) >= user_threshold:
        if await get_starboard_post(message.id, board) is None: # checking again just in case (might be expensive)
          await add_starboard_post(message, board)
          return


async def add_starboard_post(message, board) -> None:
  global ALL_STARBOARD_POSTS

  # can't really re-embed tenor gifs quicky and they aren't REALLY starboard worthy imo
  # so even if they post a really well-reacted-to tenor gif, it won't make it up here
  # feel free to suggest changes to this policy i made up randomly!
  if len(message.attachments) <= 0 and message.content.lower().startswith("https://tenor.com/"):
    return
  
  await increment_user_xp(message.author, 2, "starboard_post", message.channel) # give em that sweet sweet xp first
  ALL_STARBOARD_POSTS.append(message.id) # add post ID to in-memory list
  board_channel_id = get_channel_id(board) 
  insert_starboard_post(message.id, message.author.id, board_channel_id) # add post to DB
  
  provider_name, message_str, embed_image_url, embed_title, embed_desc, embed_thumb = ["" for i in range(6)] # initialize all the blank strings
  jumplink = f"[View original message]({message.jump_url}) from {message.channel.name}"
  author_thumb = "https://i.imgur.com/LdNH7MK.png" # default author thumb
  footer_thumb = "https://i.imgur.com/Y8T9Yxa.jpg" # default footer thumb
  original_fields = None
  date_posted = message.created_at.strftime("%A %B %-d, %Y")

  if len(message.embeds) > 0:
    # if the original message contains an embed (e.g. twitter post, youtube post, etc)
    original = message.embeds[0].to_dict()
    original_fields = original.get("fields")
    
    message_without_url = message.content.lower().replace(original["url"].lower(), '').strip()
    if message_without_url != "":
      embed_desc = f"> {message_without_url}\n"

    # trying my best to show a nice reference URL
    if original.get("provider") and original["provider"].get("name"):
      provider_name = original["provider"]["name"]
    if original.get("url") and provider_name:
      embed_desc += f"(via [{provider_name}]({original['url']}))\n"
    elif original.get("url") and original.get("title"):
      embed_desc += f"\n(via [{original['title']}]({original['url']}))"
    elif original.get("url"):
      embed_desc += f"\n(via {original['url']})"

    if original.get("image") and original["image"].get("proxy_url"):
      embed_image_url = original["image"]["proxy_url"]
    elif original.get("thumbnail") and original["thumbnail"].get("proxy_url"):
      embed_thumb = original["thumbnail"]["proxy_url"]

    if original.get("title"):
      embed_title = original["title"]
    if original.get("description"):
      embed_desc += f"\n{original['description'][0:240]}" # only get as much as a tweet from the original, we have limited space!
    
  else:
    # normal message, ez
    embed_desc = f"{message.content}\n"
    embed_title = f""
  
  # build our starboard embed now!
  star_embed = discord.Embed(
    color=discord.Color.random(),
    description=embed_desc[0:1024],
    title=embed_title,
  )

  # add fields if there were any
  if original_fields:
    for field in original_fields:
      star_embed.add_field(name=field["name"], value=field["value"])
  
  # add author's avatar as thumb if they have one
  if message.author.avatar is not None:
    author_thumb = message.author.avatar.url

  star_embed.set_author(
    name=message.author.display_name,
    icon_url=author_thumb
  )
  
  star_embed.set_footer(
    text=f"Posted on {date_posted}",
    icon_url=footer_thumb
  )
  
  if embed_image_url != "":
    star_embed.set_image(url=embed_image_url)
  elif len(message.attachments) > 0:
    # build attachments
    for attachment in message.attachments:
      if attachment.content_type.startswith("video"):
        star_embed.description += f"\n[video file]({attachment.proxy_url})\n"
      if embed_image_url == "" and attachment.content_type.startswith("image"):
        embed_image_url = attachment.proxy_url
  
  if embed_image_url != "":
    star_embed.set_image(url=embed_image_url)

  if embed_thumb != "":
    star_embed.set_thumbnail(url=embed_thumb)
  
  star_embed.description += f"\n{get_emoji('combadge')}\n\n{jumplink}"

  channel = bot.get_channel(board_channel_id)
  await channel.send(content=message_str, embed=star_embed) # send main embed
  await message.add_reaction(random.choice(["🌟","⭐","✨"])) # react to original post
  logger.info(f"{Fore.RED}AGIMUS{Fore.RESET} has added {message.author.display_name}'s post to {Style.BRIGHT}{board}{Style.RESET_ALL}!")


def insert_starboard_post(message_id, user_id, channel_id) -> None:
  """ 
  inserts a post into the DB - only saves the message ID, user ID and channel ID 
  """
  with getDB() as db:
    query = db.cursor()
    sql = "INSERT INTO starboard_posts (message_id, user_id, board_channel) VALUES (%s, %s, %s);"
    vals = (message_id, user_id, channel_id)
    query.execute(sql, vals)
    db.commit()

def get_starboard_post(message_id, board) -> tuple:
  """
  returns the post's channel ID or None if not found
  """
  with getDB() as db:
    query = db.cursor()
    sql = "SELECT board_channel FROM starboard_posts WHERE message_id = %s and board_channel = %s"
    vals = (message_id, board)
    query.execute(sql, vals)
    message = query.fetchone()
  return message

def get_all_starboard_posts() -> list:
  """
  returns a list of all starboard post IDs
  """
  posts = []
  with getDB() as db:
    query = db.cursor(dictionary=True)
    sql = "SELECT message_id FROM starboard_posts"
    query.execute(sql)
    for post in query.fetchall():
      posts.append(int(post["message_id"]))
  return posts
