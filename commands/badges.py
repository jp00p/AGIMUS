import textwrap
import time
import math

from common import *
from utils.badge_utils import generate_paginated_badge_images, db_set_user_badge_page_color_preference
from utils.check_channel_access import access_check


f = open(config["handlers"]["xp"]["badge_data"])
badge_data = json.loads(f.read())
f.close()

async def all_badges_autocomplete(ctx:discord.AutocompleteContext):
  all_badges = [key.replace('_', ' ').replace('.png', '') for key in badge_data.keys()]
  return [badge for badge in all_badges if ctx.value.lower() in badge.lower()]

@bot.slash_command(
  name="badges",
  description="Show off all your badges! Please be mindful of posting very large collections publicly."
)
@option(
  name="public",
  description="Show to public?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="No",
      value="no"
    ),
    discord.OptionChoice(
      name="Yes",
      value="yes"
    )
  ]
)
@option(
  name="color",
  description="Which colorscheme would you like?",
  required=False,
  choices = [
    discord.OptionChoice(name=color_choice, value=color_choice.lower())
    for color_choice in ["Green", "Orange", "Purple", "Teal"]
  ]
)
async def badges(ctx:discord.ApplicationContext, public:str, color:str):
  public = bool(public == "yes")
  await ctx.defer(ephemeral=not public)

  badges = os.listdir("./images/badges/")
  badge_list = get_user_badges(ctx.author.id)

  all_badges = []
  for badge in badge_list:
    # badge_filename = badge.replace(" ", "_").replace("/", "-").replace(":", "-")
    record = {
      'badge_name': badge.replace("_", " ").replace(".png", ""),
      'badge_filename': badge,
    }
    all_badges.append(record)

  # Set up text values for paginated pages
  total_badges = len(badges)
  title = f"{ctx.author.display_name.encode('ascii', errors='ignore').decode().strip()}'s Badge Collection"
  collected = f"{len(badge_list)} TOTAL ON THE USS HOOD"
  filename_prefix = f"badge_list_{ctx.author.id}-page-"

  if color:
    db_set_user_badge_page_color_preference(ctx.author.id, "sets", color)
  badge_images = await generate_paginated_badge_images(ctx.author, 'showcase', all_badges, total_badges, title, collected, filename_prefix)

  embed = discord.Embed(
    title=f"Badge Collection",
    description=f"{ctx.author.mention} has collected {len(all_badges)} of {len(badges)}!",
    color=discord.Color(0x54B145)
  )

  # If we're doing a public display, use the images directly
  # Otherwise private displays can use the paginator
  if not public:
    buttons = [
      pages.PaginatorButton("prev", label="   ⬅   ", style=discord.ButtonStyle.primary, disabled=bool(len(all_badges) <= 30), row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="   ➡   ", style=discord.ButtonStyle.primary, disabled=bool(len(all_badges) <= 30), row=1),
    ]

    set_pages = [
      pages.Page(files=[image], embeds=[embed])
      for image in badge_images
    ]
    paginator = pages.Paginator(
        pages=set_pages,
        show_disabled=True,
        show_indicator=True,
        use_default_buttons=False,
        custom_buttons=buttons,
        loop_pages=True
    )
    await paginator.respond(ctx.interaction, ephemeral=True)
  else:
    # We can only attach up to 10 files per message, so if it's public send them in chunks
    file_chunks = [badge_images[i:i + 10] for i in range(0, len(badge_images), 10)]
    for chunk_index, chunk in enumerate(file_chunks):
      # Only post the embed on the last chunk
      if chunk_index + 1 == len(file_chunks):
        await ctx.followup.send(embed=embed, files=chunk, ephemeral=not public)
      else:
        await ctx.followup.send(files=chunk, ephemeral=not public)


# slash command to get common badge stats
@bot.slash_command(
  name="badge_statistics",
  description="See the server-wide badge statistics"
)
async def badge_statistics(ctx:discord.ApplicationContext):
  results = {}
  results = run_badge_stats_queries()
  top_collectors = [res for res in results["top_collectors"]]
  top_three = [res for res in results["most_collected"]]
  embed = discord.Embed(color=discord.Color.random(), description="", title="")
  embed.add_field(name="Total badges collected\non the USS Hood", value=f"{results['total_badges'][0]['count']}", inline=True)
  embed.add_field(name=f"{get_emoji('combadge')}", value="⠀", inline=True)
  embed.add_field(name="Badges collected today", value=f"{results['badges_today'][0]['count']}", inline=True)
  embed.add_field(name="Top 3 most-collected badges", value=str("\n".join(f"{t['badge_name'].replace('_', ' ').replace('.png', '')} ({t['count']})" for t in top_three)), inline=True)
  embed.add_field(name=f"{get_emoji('combadge')}", value="⠀", inline=True)
  embed.add_field(name="Top 3 badge collectors", value=str("\n".join(f"{t['name']} ({t['count']})" for t in top_collectors)), inline=True)
  await ctx.respond(embed=embed, ephemeral=False)

@bot.slash_command(
  name="gift_badge",
  description="Give a user a random badge (admin only)"
)
@commands.has_permissions(administrator=True)
@option(
  "user",
  discord.User,
  description="Which user to gift the badge to",
  required=True
)
# give a random badge to a user
async def gift_badge(ctx:discord.ApplicationContext, user:discord.User):
  notification_channel_id = get_channel_id(config["handlers"]["xp"]["notification_channel"])
  logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}gift a random badge{Style.RESET_ALL} to {user.display_name}")

  badge = give_user_badge(user.id)

  channel = bot.get_channel(notification_channel_id)
  embed_title = "You got rewarded a badge!"
  thumbnail_image = random.choice(config["handlers"]["xp"]["celebration_images"])
  embed_description = f"{user.mention} has been gifted a badge by {ctx.author.mention}!"
  message = f"{user.mention} - Nice work, you got a free badge!"
  await send_badge_reward_message(message, embed_description, embed_title, channel, thumbnail_image, badge, user)
  await ctx.respond("Your gift has been sent!", ephemeral=True)

@gift_badge.error
async def gift_badge_error(ctx, error):
  if isinstance(error, commands.MissingPermissions):
    await ctx.respond("Sorry, you do not have permission to do that!", ephemeral=True)
  else:
    await ctx.respond("Sensoars indicate some kind of ...*error* has occured!", ephemeral=True)


@bot.slash_command(
  name="gift_specific_badge",
  description="Give a user a specific badge (admin only)"
)
@commands.has_permissions(administrator=True)
@option(
  "user",
  discord.User,
  description="Which user to gift the badge to",
  required=True
)
@option(
  name="specific_badge",
  description="The name of the Badge to Gift",
  required=True,
  autocomplete=all_badges_autocomplete
)
# give a random badge to a user
async def gift_specific_badge(ctx:discord.ApplicationContext, user:discord.User, specific_badge:str):
  notification_channel_id = get_channel_id(config["handlers"]["xp"]["notification_channel"])
  logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}gift {specific_badge}{Style.RESET_ALL} to {user.display_name}")

  specific_badge_filename = f"{specific_badge.replace(' ', '_')}.png"
  badge_info = badge_data.get(specific_badge_filename)
  if badge_info == None:
    await ctx.respond(f"Can't send {specific_badge}, it doesn't look like that badge exists!", ephemeral=True)
    return
  else:
    user_badges = get_user_badges(user.id)
    if specific_badge not in user_badges:
      badge = specific_badge_filename
      give_user_specific_badge(user.id, specific_badge_filename)

  channel = bot.get_channel(notification_channel_id)
  embed_title = "You got rewarded a badge!"
  thumbnail_image = random.choice(config["handlers"]["xp"]["celebration_images"])
  embed_description = f"{user.mention} has been gifted a badge by {ctx.author.mention}!"
  message = f"{user.mention} - Nice work, you got a free badge!"
  await send_badge_reward_message(message, embed_description, embed_title, channel, thumbnail_image, badge, user)
  await ctx.respond("Your gift has been sent!", ephemeral=True)


@gift_specific_badge.error
async def gift_specific_badge_error(ctx, error):
  if isinstance(error, commands.MissingPermissions):
    await ctx.respond("Sorry, you do not have permission to do that!", ephemeral=True)
  else:
    await ctx.respond("Sensoars indicate some kind of ...*error* has occured!", ephemeral=True)


async def send_badge_reward_message(message:str, embed_description:str, embed_title:str, channel, thumbnail_image:str, badge:str, user:discord.User):
  badge_info = badge_data.get(badge)
  badge_name = badge.replace("_", " ").replace(".png", "")
  star_str = "⭐\u00A0"*9
  if badge_info:
    badge_url = badge_info["badge_url"]
    embed_description += f"\n\n**{badge_name}**\n{badge_url}"
  embed_description += f"\n{star_str}\n"
  embed=discord.Embed(title=embed_title, description=embed_description, color=discord.Color.random())
  embed.set_thumbnail(url=thumbnail_image)
  embed.set_footer(text="See all your badges by typing /badges - disable this by typing /disable_xp")
  if badge_info:
    embed.set_image(url=f"{badge_info['image_url']}")
    await channel.send(content=message, embed=embed)
  else:
    embed_filename = str(user.id) + str(abs(hash(badge_name))) + ".png"
    discord_image = discord.File(fp=f"./images/badges/{badge}", filename=embed_filename)
    embed.set_image(url=f"attachment://{embed_filename}")
    await channel.send(content=message, file=discord_image, embed=embed)


# give_user_badge(user_discord_id)
# user_discord_id[required]:int
# pick a badge, update badges DB, return badge name
def give_user_badge(user_discord_id:int):
  # list files in images/badges directory
  badges = os.listdir("./images/badges/")
  # get the users current badges
  user_badges = get_user_badges(user_discord_id)
  badge_choice = random.choice(badges)
  # don't give them a badge they already have
  while badge_choice in user_badges:
    badge_choice = random.choice(badges)
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO badges (user_discord_id, badge_name) VALUES (%s, %s)"
  vals = (user_discord_id, badge_choice)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()
  return badge_choice

def give_user_specific_badge(user_discord_id:int, badge_choice:str):
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO badges (user_discord_id, badge_name) VALUES (%s, %s)"
  vals = (user_discord_id, badge_choice)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()
  return badge_choice

# get_user_badges(user_discord_id)
# user_discord_id[required]: int
# returns a list of badges the user has
def get_user_badges(user_discord_id:int):
  db = getDB()
  query = db.cursor()
  sql = "SELECT badge_name FROM badges WHERE user_discord_id = %s ORDER BY badge_name ASC"
  vals = (user_discord_id,)
  query.execute(sql, vals)
  badges = [badge[0] for badge in query.fetchall()]
  db.commit()
  query.close()
  db.close()
  return badges

def run_badge_stats_queries():
  queries = {
    "most_collected" : "SELECT badge_name, COUNT(id) as count FROM badges GROUP BY badge_name ORDER BY count DESC LIMIT 3;",
    "total_badges" : "SELECT COUNT(id) as count FROM badges;",
    "badges_today" : "SELECT COUNT(id) as count FROM badges WHERE time_created > NOW() - INTERVAL 1 DAY;",
    "top_collectors" : "SELECT name, COUNT(badges.id) as count FROM users JOIN badges ON users.discord_id = badges.user_discord_id GROUP BY discord_id ORDER BY COUNT(badges.id) DESC LIMIT 3;"
  }
  db = getDB()
  results = {}
  for name,sql in queries.items():
    query = db.cursor(dictionary=True)
    query.execute(sql)
    results[name] = query.fetchall()
    db.commit()
    query.close()
  db.close()
  return results