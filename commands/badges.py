from common import *
import textwrap
import time
import math
from utils.check_channel_access import access_check


f = open(config["handlers"]["xp"]["badge_data"])
badge_data = json.loads(f.read())
f.close()

async def all_badges_autocomplete(ctx:discord.AutocompleteContext):
  all_badges = [key.replace('_', ' ').replace('.png', '') for key in badge_data.keys()]
  return [badge for badge in all_badges if ctx.value.lower() in badge.lower()]

@bot.slash_command(
  name="badges",
  description="Show off all your badges!"
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
async def badges(ctx:discord.ApplicationContext, public:str):
  public = bool(public == "yes")
  await ctx.defer(ephemeral=not public)
  showcase_image = generate_badge_showcase_for_user(ctx.author)
  await ctx.followup.send(file=showcase_image, ephemeral=not public)


# slash command to get common badge stats
@bot.slash_command(
  name="badge_stats",
  description="See the server-wide badge statistics"
)
async def badge_stats(ctx:discord.ApplicationContext):
  results = {}
  results = run_badge_stats_queries()
  embed = discord.Embed(color=discord.Color.random(), description="", title="")
  embed.add_field(name="Total badges collected on the USS Hood", value=f"{results['total_badges'][0]['count']}")
  embed.add_field(name="Most popular badge somehow", value=f'{results["most_collected"][0]["badge_name"].replace("_", " ").replace(".png", "")} ({results["most_collected"][0]["count"]} collected)')
  embed.add_field(name="Crew member with the most badges right now", value=f"{results['number_one'][0]['name']} ({results['number_one'][0]['count']})")
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

# big expensive function that generates a nice grid of images for the user
# returns discord.file
def generate_badge_showcase_for_user(user:discord.User):
  text_wrapper = textwrap.TextWrapper(width=22)
  badge_list = get_user_badges(user.id)
  title_font = ImageFont.truetype("fonts/tng_credits.ttf", 68)
  credits_font = ImageFont.truetype("fonts/tng_credits.ttf", 42)
  badge_font = ImageFont.truetype("fonts/context_bold.ttf", 28)
  
  badge_size = 200
  badge_padding = 40
  badge_margin = 10
  badge_slot_size = badge_size + (badge_padding * 2) # size of badge slot size (must be square!)
  badges_per_row = 6

  base_width = (badge_slot_size+badge_margin) * badges_per_row
  base_height = math.ceil((len(badge_list) / badges_per_row)) * (badge_slot_size + badge_margin)

  header_height = badge_size
  image_padding = 50

  # create base image to paste all badges on to
  # what if they have 900 badges?
  badge_base_image = Image.new("RGBA", (base_width+(image_padding*2), base_height+header_height+(image_padding*2)), (200, 200, 200))
  badge_bg_image = Image.open("./images/stars/" + random.choice(os.listdir("./images/stars/")))

  base_w, base_h = badge_base_image.size
  bg_w, bg_h = badge_bg_image.size

  for i in range(0, base_w, bg_w):
    for j in range(0, base_h, bg_h):
      badge_base_image.paste(badge_bg_image, (i, j))

  draw = ImageDraw.Draw(badge_base_image)

  draw.text( (base_width/2, 100), f"{user.display_name.encode('ascii', errors='ignore').decode().strip()}'s Badge collection", fill="white", font=title_font, anchor="mm", align="center")
  draw.text( (base_width/2, base_h-50), f"Total of {len(badge_list)} badges collected on the USS Hood", fill="white", font=credits_font, anchor="mm", align="center",stroke_width=2,stroke_fill="#000000")

  start_x = image_padding
  current_x = start_x
  current_y = header_height
  counter = 0
  badge_border_color = random.choice(["#774466", "#6688CC", "#BB4411", "#0011EE"])

  for badge in badge_list:
    # todo: create slot border/stuff, lcars stuff

    # slot
    s = Image.new("RGBA", (badge_slot_size, badge_slot_size), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(s)
    badge_draw.rounded_rectangle( (0, 0, badge_slot_size, badge_slot_size), fill="#000000", outline=badge_border_color, width=4, radius=32 )

    # badge
    b = Image.open(f"./images/badges/{badge}").convert("RGBA")
    b = b.resize((190, 190))

    w, h = b.size # badge size
    offset_x = min(0, (badge_size+badge_padding+2)-w) # center badge x
    offset_y = 5
    badge_name = text_wrapper.wrap(badge.replace("_", " ").replace(".png", ""))
    wrapped_badge_name = ""
    for i in badge_name[:-1]:
      wrapped_badge_name = wrapped_badge_name + i + "\n"
    wrapped_badge_name += badge_name[-1]
    # add badge to slot
    s.paste(b, (badge_padding+offset_x, offset_y), b)
    badge_draw.text( (int(badge_slot_size/2), 222), f"{wrapped_badge_name}", fill="white", font=badge_font, anchor="mm", align="center")

    # add slot to base image
    badge_base_image.paste(s, (current_x, current_y), s)

    current_x += badge_slot_size + badge_margin
    counter += 1

    if counter % badges_per_row == 0:
      # typewriter sound effects:
      current_x = start_x # ding!
      current_y += badge_slot_size + badge_margin # ka-chunk
      counter = 0 #...

  badge_base_image.save(f"./images/profiles/badge_list_{user.id}.png")

  while True:
    time.sleep(0.05)
    if os.path.isfile(f"./images/profiles/badge_list_{user.id}.png"):
      break

  discord_image = discord.File(f"./images/profiles/badge_list_{user.id}.png")
  return discord_image


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
    "most_collected" : "SELECT badge_name, COUNT(id) as count FROM badges GROUP BY badge_name ORDER BY count DESC LIMIT 1;",
    "total_badges" : "SELECT COUNT(id) as count FROM badges;",
    "number_one" : "SELECT name, COUNT(badges.id) as count FROM users JOIN badges ON users.discord_id = badges.user_discord_id GROUP BY discord_id ORDER BY COUNT(badges.id) DESC LIMIT 1;"
    #"today" : "SELECT * FROM badges WHERE time_created > DATE('now', '-1 day')"
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