import asyncio
import random
import re
from typing import Dict, List

import discord
from colorama import Fore, Style

from common import config, logger, get_channel_id, get_channel_ids_list, get_emoji, bot, ALL_STARBOARD_POSTS
from handlers.xp import increment_user_xp
from utils.database import AgimusDB

react_threshold = 3 # how many reactions required
high_react_threshold = 5
user_threshold = 3 # how many users required

db_lock = asyncio.Lock()

async def handle_starboard_reactions(payload:discord.RawReactionActionEvent) -> None:
  board_patterns = generate_board_compiled_patterns(config["handlers"]["starboard"]["boards"])
  blocked_channels = get_channel_ids_list(config["handlers"]["starboard"]["blocked_channels"])
  board_ids = get_channel_ids_list(board_patterns.keys())
  high_react_channel_ids = get_channel_ids_list(config["handlers"]["starboard"]["high_react_channels"])

  # don't watch the actual starboard channels, or if the react came from the bot itself, eject
  if payload.channel_id in board_ids or payload.member.bot:
    return

  channel = bot.get_channel(payload.channel_id)
  if channel.type != discord.ChannelType.text: # only textchannels work here for now (we don't starboard viewscreen chat)
    return
  message = await channel.fetch_message(payload.message_id)
  reaction = payload.emoji

  # don't count users adding reacts to their own posts
  if message.author == payload.member:
    return

  # weird edge case where reaction can be a string (never seen it happen)
  if isinstance(reaction, str):
    logger.info(f"{Style.BRIGHT}{Fore.YELLOW}WHOA THE REACTION IS A STRING{Fore.RESET}{Style.RESET_ALL}")
    return

  # it might be safe to see if this is a starboard-worthy post now
  # each starboard can have a set of words to match against,
  # here we loop over each board and then each word that board has
  # the words will be in the emoji name, not the message text
  for board, match_reacts in board_patterns.items():
    board_posts = ALL_STARBOARD_POSTS.get(board)
    if board_posts is not None and payload.message_id in board_posts:
      continue

    if payload.channel_id in blocked_channels:
      # We're looking at a message from a globally blocked channel, check overrides
      blocked_channels_overrides = config["handlers"]["starboard"]["blocked_channels_override"].get(board)
      if blocked_channels_overrides is None:
        # We have no overrides for this board so go ahead and move to the next board
        continue
      else:
        # Overrides present, check
        override_channel_ids = get_channel_ids_list(blocked_channels_overrides)
        if payload.channel_id not in override_channel_ids:
          # The message wasn't from an overridden channel so confirmed that we should skip this board
          continue
        # Otherwise, move forward with the remnaining code for this board iteration

    all_reacts = message.reactions
    message_reaction_people = set()
    total_reacts_for_this_match = 0

    # loop over each matching word for this board (word is in emoji name)
    for match in match_reacts:
      # loop over each reaction in the message
      for reaction in all_reacts:
        this_emoji = reaction.emoji
        if hasattr(this_emoji, "name"):
          # if its a named emoji and does not have one of our words or matches exactly, skip
          if match.search(this_emoji.name.lower()) is None:
            continue
        # raw emoji like :black_heart: have no name attribute, but can do direct match comparison
        elif match.search(this_emoji) is None:
          continue

        # count the users who reacted with this one
        async for user in reaction.users():
          # if they haven't already reacted with one of the matching reactions, count this reaction
          if user != message.author and user not in message_reaction_people:
            total_reacts_for_this_match += 1
            message_reaction_people.add(user) # and don't count them again!

    # total_people = len(message_reaction_people)
    # logger.info(f"{Fore.LIGHTWHITE_EX}{Style.BRIGHT}{board}: report for this post {message.content}...: reacts {total_reacts_for_this_match} -- total reacting people: {total_people}{Style.RESET_ALL}{Fore.RESET}")

    # Some channels have a higher react threshold than others
    adjusted_react_threshold = react_threshold
    if payload.channel_id in high_react_channel_ids:
      adjusted_react_threshold = high_react_threshold
    # finally, if this match category has enough reactions and enough people, let's save it to the starboard channel!
    if total_reacts_for_this_match >= adjusted_react_threshold and len(message_reaction_people) >= user_threshold:
      async with db_lock:
        if await db_get_starboard_post(message.id, board) is None: # checking again just in case (might be expensive)
          await add_starboard_post(message, board)
          return


async def add_starboard_post(message, board) -> None:
  global ALL_STARBOARD_POSTS

  # can't really re-embed tenor gifs quicky and they aren't REALLY starboard worthy imo
  # so even if they post a really well-reacted-to tenor gif, it won't make it up here
  # feel free to suggest changes to this policy i made up randomly!
  if len(message.attachments) <= 0 and message.content.lower().startswith("https://tenor.com/"):
    return

  await increment_user_xp(message.author, 2, "starboard_post", message.channel, "Getting a Clip Show Device post") # give em that sweet sweet xp first
  if ALL_STARBOARD_POSTS.get(board) is None:
    ALL_STARBOARD_POSTS[board] = []
  ALL_STARBOARD_POSTS[board].append(int(message.id))

  board_channel_id = get_channel_id(board)
  channel = bot.get_channel(board_channel_id) # where it will be posted
  await db_insert_starboard_post(message.id, message.author.id, board) # add post to DB

  provider_name, message_str, embed_image_url, embed_title, embed_desc, embed_thumb = ["" for i in range(6)] # initialize all the blank strings
  jumplink = f"[View original message]({message.jump_url}) from {message.channel.mention}"
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
    embed_desc = message.content
    embed_title = f""

  star_description = ""
  if embed_desc:
    embed_desc = "\n> ".join(l for l in embed_desc.splitlines() if l)
    if len(embed_desc) > 1024:
      star_description = f"> {embed_desc[0:1024]}..."
    else:
      star_description = f"> {embed_desc}"

  # build our starboard embed now!
  star_embed = discord.Embed(
    color=discord.Color.random(),
    description=star_description,
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

  star_file = None

  if embed_image_url != "":
    star_embed.set_image(url=embed_image_url)
  elif len(message.attachments) > 0:
    # build attachments
    attachment = message.attachments[0]
    if attachment.content_type.startswith("video"):
      star_file = await attachment.to_file(spoiler=attachment.is_spoiler())
    else:
      if attachment.is_spoiler():
        # Since we can't embed images as spoilers, attach the file rather than embedding it
        star_file = await attachment.to_file(spoiler=True)
      elif attachment.content_type.startswith("image"):
        star_embed.set_image(url=attachment.proxy_url)

  if embed_thumb != "":
    star_embed.set_thumbnail(url=embed_thumb)

  star_embed.description += f"\n{get_emoji('combadge')}\n\n{jumplink}"


  await channel.send(content=message_str, embed=star_embed, file=star_file)
  await message.add_reaction(random.choice(["🌟","⭐","✨"])) # react to original post
  logger.info(f"{Fore.RED}AGIMUS{Fore.RESET} has added {message.author.display_name}'s post to {Style.BRIGHT}{board}{Style.RESET_ALL}!")


async def db_insert_starboard_post(message_id, user_id, channel_id) -> None:
  """
  inserts a post into the DB - only saves the message ID, user ID and channel ID
  """
  async with AgimusDB() as query:
    sql = "INSERT INTO starboard_posts (message_id, user_id, board_channel) VALUES (%s, %s, %s);"
    vals = (message_id, user_id, channel_id)
    await query.execute(sql, vals)

async def db_get_starboard_post(message_id, board):
  """
  returns the post's channel ID or None if not found
  """
  async with AgimusDB() as query:
    sql = "SELECT board_channel FROM starboard_posts WHERE message_id = %s and board_channel = %s"
    vals = (message_id, board)
    await query.execute(sql, vals)
    message = await query.fetchone()
  return message

async def db_get_all_starboard_posts() -> list:
  """
  returns a list of all starboard post IDs
  """
  posts = {}
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT board_channel, message_id FROM starboard_posts"
    await query.execute(sql)
    for result in await query.fetchall():
      if posts.get(result['board_channel']) is None:
        posts[result['board_channel']] = []
      posts[result['board_channel']].append(int(result["message_id"]))
  return posts


def generate_board_compiled_patterns(board_emoji: dict) -> Dict[str, List[re.Pattern]]:
  """
  Generate information about the various starboards ahead of time.  Returns a dict where the keys are the board names,
  and the values are arrays of compiled regular expressions.
  """
  result = {}
  for name, emoji_list in board_emoji.items():
    result[name] = []
    for fragment in emoji_list:
      result[name].append(re.compile(rf"(^|_){re.escape(fragment.lower())}(_|$)"))
  return result

