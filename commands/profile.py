from common import *
from handlers.xp import calculate_xp_for_next_level
from commands.badges import get_user_badges
from utils.badge_utils import db_get_user_badge_names
from utils.check_channel_access import access_check
import pilgram

filters = ["_1977", "aden", "brannan", "brooklyn", "clarendon", "earlybird", "gingham", "hudson", "inkwell", "kelvin", "lark", "lofi", "maven", "mayfair", "moon", "nashville", "perpetua", "reyes", "rise", "slumber", "stinson", "toaster", "valencia", "walden", "willow", "xpro2"]

@bot.slash_command(
  name="set_tagline",
  description="Set your profile tagline (or unset it!)"
)
@option(
  name="tagline",
  description="Your tagline (up to 60 characters, follow the server rules please!)",
  required=False
)
# set a user's tagline for their profile card
# users can also unset it by sending an empty string
async def set_tagline(ctx:discord.ApplicationContext, tagline:str):
  if not tagline or tagline.strip() == "":

    db = getDB()
    query = db.cursor()
    sql = "REPLACE INTO profile_taglines (tagline, user_discord_id) VALUES (%(tagline)s, %(user_discord_id)s)"
    vals = {"tagline" : "", "user_discord_id" : ctx.author.id}
    logger.info(f"CLEARING TAGLINE {sql}")
    query.execute(sql, vals)
    db.commit()
    query.close()
    db.close()
    await ctx.respond(f"Your tagline has been cleared!", ephemeral=True)
  else:
    tagline = tagline[0:60].encode("ascii", errors="ignore").decode().strip()
    db = getDB()
    query = db.cursor()
    sql = "REPLACE INTO profile_taglines (tagline, user_discord_id) VALUES (%(tagline)s, %(user_discord_id)s)"
    vals = {"tagline" : tagline, "user_discord_id" : ctx.author.id}
    logger.info(f"UPDATING TAGLINE {sql} {vals}")
    query.execute(sql, vals)
    db.commit()
    query.close()
    db.close()
    await ctx.respond(f"Your tagline has been updated!", ephemeral=True)
    logger.info(f"{ctx.author} has changed their tagline to: \"{tagline}\"")


def user_badges_autocomplete(ctx:discord.AutocompleteContext):
  user_badges = [b['badge_filename'].replace('_', ' ').replace('.png', '') for b in db_get_user_badge_names(ctx.interaction.user.id)]
  if len(user_badges) == 0:
    user_badges = ["You don't have any badges yet!"]
  user_badges.sort()
  user_badges.insert(0, '[CLEAR BADGE]')

  return [result for result in user_badges if ctx.value.lower() in result.lower()]


@bot.slash_command(
  name="set_profile_badge",
  description="Set your featured profile badge (or unset it!)"
)
@option(
  name="badge",
  description="Your badge name",
  required=False,
  autocomplete=user_badges_autocomplete
)
# set a user's badge for their profile card
async def set_profile_badge(ctx:discord.ApplicationContext, badge:str):
  # Remove badge if desired by user
  remove = bool(badge == '[CLEAR BADGE]')
  if remove:
    db_remove_user_profile_badge(ctx.author.id)
    await ctx.respond(embed=discord.Embed(
      title="Cleared Profile Badge",
      color=discord.Color.green(),
    ), ephemeral=True)
    return

  # Check to make sure they own the badge
  user_badges = [b['badge_filename'].replace('_', ' ').replace('.png', '') for b in db_get_user_badge_names(ctx.author.id)]
  if badge not in user_badges:
    await ctx.respond(embed=discord.Embed(
      title="Unable To Set Featured Profile Badge",
      description="You don't appear to have that badge yet!",
      color=discord.Color.red()
    ), ephemeral=True)
    return

  # If it looks good, go ahead and add the badge to their profile
  badge_filename = db_get_badge_filename_for_badge(badge)
  db_add_user_profile_badge(ctx.author.id, badge_filename)
  await ctx.respond(
    embed=discord.Embed(
      title="Your featured profile badge has been updated!",
      description=f"You've successfully set \"{badge}\" as your profile badge.\n\nUse `/profile` to check it out!",
      color=discord.Color.green()
    ),
    ephemeral=True
  )
  logger.info(f"{ctx.author} has changed their profile badge to: \"{badge}\"")



# slash_profile() - Entrypoint for /profile command
# This function is the main entrypoint of the /profile command
# and will return a user's profile card
@bot.slash_command(
  name="profile",
  description="Show your own profile card"
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

async def profile(ctx:discord.ApplicationContext, public:str):
  public = bool(public == "yes")
  await ctx.defer(ephemeral=not public)

  member = ctx.author # discord obj
  user = get_user(member.id) # our DB
  logger.info(f"{Fore.CYAN}{member.display_name} is looking at their own {Back.WHITE}{Fore.BLACK}profile card!{Back.RESET}{Fore.RESET}")

  # clean up username
  user_name = f"{member.display_name}"
  user_name_encode = user_name.encode("ascii", errors="ignore")
  user_name = user_name_encode.decode().strip()

  # get rank
  ranks = ["admiral", "captain", "commander", "lieutenant", "ensign", "cadet"]
  top_role = "Merchant"
  for role in member.roles:
    rolename = role.name.encode("ascii", errors="ignore").decode().strip().lower()
    for rank in ranks:
      if rolename == rank:
        top_role = rank.capitalize()
        break


  # find their assignment (vanity role)
  assignments = [846843197836623972, 765301878309257227, 846844057892421704, 846844534217769000, 847986805571059722, 846847075911991326, 846844634579730463, 846845685357871124, 902717922475126854]
  assignment_names = []
  for role in member.roles:
    if role.id in assignments:
      assignment_names.append(role.name)
  # no vanity role, give them this one
  if len(assignment_names) <= 0:
    second_role = "Stowaway"
  else:
    second_role = assignment_names[-1]

  user_join = member.joined_at.strftime("%d %B %Y")
  user_join_stardate = calculate_stardate(member.joined_at)
  score = user["score"]
  spins = user["spins"]
  level = user["level"]
  xp = user["xp"]
  badges = get_user_badges(member.id)
  badge_count = len(badges)
  next_level = calculate_xp_for_next_level(level)
  prev_level = 0
  if level > 1:
    prev_level = calculate_xp_for_next_level(level-1)

  percent_completed = (((xp - prev_level)*100) / (next_level - prev_level))/100  # for calculating width of xp bar

  # fonts (same font, different sizes) used for building image
  name_font = ImageFont.truetype("fonts/lcars3.ttf", 61)
  agimus_font = ImageFont.truetype("fonts/lcars3.ttf", 22)
  level_font = ImageFont.truetype("fonts/lcars3.ttf", 50) # also main header font
  small_button_font = ImageFont.truetype("fonts/lcars3.ttf", 30)
  big_button_font = ImageFont.truetype("fonts/lcars3.ttf", 28)
  title_font = ImageFont.truetype("fonts/lcars3.ttf", 34) # also subtitle font and score font
  xp_font = ImageFont.truetype("fonts/lcars3.ttf", 32)
  entry_font = ImageFont.truetype("fonts/lcars3.ttf", 40)

  # build the base bg
  base_bg = Image.new(mode="RGBA", size=(787, 1024))
  padd_bg = Image.new(size=(700, 839), color="black", mode="RGBA")
  base_bg.paste(padd_bg, (41, 50), padd_bg)

  # get user profile color
  profile_color = member.color.to_rgb()
  if member.color.value == 0:
    # default to white lcars
    profile_color = (255, 255, 255)

  # list of all template pieces we'll be coloring
  template_pieces = [
    "./images/profiles/template_pieces/lcars/lighter-pieces.png",
    "./images/profiles/template_pieces/lcars/pieces-1.png",
    "./images/profiles/template_pieces/lcars/pieces-2.png",
    "./images/profiles/template_pieces/lcars/pieces-3.png",
    "./images/profiles/template_pieces/lcars/xp-bar.png"
  ]

  # modifiers for the lcars pieces
  profile_shades = [
    (random.randint(25,40), random.randint(25,40), random.randint(25,40)), # lighten up the first element
    (random.randint(-25,25), random.randint(-25,25), random.randint(-25,25)),
    (random.randint(-45,45), random.randint(-45,45), random.randint(-45,45)),
    (random.randint(-35,35), random.randint(-35,35), random.randint(-35,35)),
    (random.randint(-5,5), random.randint(-5,5), random.randint(-5,5))
  ]

  lcars_colors = []
  # special colors just for Sara
  admiral_colors = [
    (255, 255, 0),
    (0, 164, 164),
    (200, 200, 0),
    (0, 128, 128),
    (200, 200, 0)
  ]

  # adjust shades of colors!
  for i in range(len(profile_shades)):
    #logger.info(f"Profile colors: {profile_color[0]} {profile_color[1]} {profile_color[2]}")
    #logger.info(f"Current shades: {profile_shades[i]} {profile_shades[i][0]} {profile_shades[i][1]} {profile_shades[i][2]}")
    r = sorted([profile_color[0]+profile_shades[i][0], 0, 255])[1]
    g = sorted([profile_color[1]+profile_shades[i][1], 0, 255])[1]
    b = sorted([profile_color[2]+profile_shades[i][2], 0, 255])[1]
    lcars_colors.append((r,g,b))

  if profile_color == (12, 13, 14):
    # special Sara colors
    lcars_colors = admiral_colors

  draw = ImageDraw.Draw(base_bg) # pencil time

  # draw xp progress bar
  w, h = 244-32, 26
  x, y = 394+32, 839
  shape =(x, y, (percent_completed*w)+x, h+y)
  draw.rectangle(shape, fill=lcars_colors[0])

  # draw each lcars piece
  for i in range(len(template_pieces)):
    image = Image.open(template_pieces[i])
    image = image.convert("RGBA")
    image_data = np.array(image) # load image data into bytes array
    # replace white in the base template with the user's color
    red, green, blue, alpha = image_data.T # ignore alpha
    white_areas = (red >= 75) & (green >= 75) & (blue >= 75)
    image_data[..., :-1][white_areas.T] = lcars_colors[i] # magic
    image = Image.fromarray(image_data)
    image = image.convert("RGBA")
    base_bg.paste(image, (0, 0), image)

  # draw all the texty bits
  draw.text( (283, 80), f"USS HOOD PERSONNEL FILE #{member.discriminator}", fill=random.choice(lcars_colors), font=level_font, align="right")
  draw.text( (79, 95), f"AGIMUS MAIN TERMINAL", fill="#dd4444", font=agimus_font, align="center",)
  draw.text( (470, 182), f"{user_name[0:32]}", fill="white", font=name_font, align="center", anchor="ms")
  if user['tagline']:
    draw.text( (470, 233), f"\"{user['tagline']}\"", fill="white", font=entry_font, align="center", anchor="ms")
  draw.text( (578, 381), f"LEVEL: {user['level']:03d}", fill="white", font=level_font, align="right" )
  title_color = random.choice(lcars_colors[1:3])
  draw.text( (250, 385), f"CURRENT RANK:", fill=title_color, font=title_font, align="left")
  draw.text( (250, 418), f"{top_role}", fill="white", font=entry_font, align="left")
  draw.text( (250, 478), f"CURRENT ASSIGNMENT:", fill=title_color, font=title_font, align="left")
  draw.text( (250, 508), f"{second_role} / USS Hood NCC-42296", fill="white", font=entry_font, align="left")
  draw.text( (250, 568), f"DUTY STARTED:", fill=title_color, font=title_font, align="left")
  # TODO: come back to this
  #draw.text( (250, 598), f"STARDATE: {user_join_stardate}", fill="white", font=entry_font, align="left")
  draw.text( (250, 598), f"{user_join}", fill="white", font=entry_font, align="left")
  draw.text( (350, 740), f"BADGES: {badge_count:03d}", fill="black", font=small_button_font, align="center")
  draw.text( (350, 791), f"SPINS: {spins:04d}", fill="black", font=small_button_font, align="center")
  draw.text( (507, 751), f"RECREATIONAL CREDITS:", fill="black", font=big_button_font, align="center")
  draw.text( (554, 781), f"{score:08d}", fill="black", font=title_font, align="center")
  draw.text( (388, 850), f"XP: {xp:05d}", fill="black", font=xp_font, align="right", anchor="rm")

  # add users avatar to card
  avatar = member.display_avatar.with_size(128)
  await avatar.save("./images/profiles/"+str(member.id)+"_a.png")
  avatar_image = Image.open("./images/profiles/"+str(member.id)+"_a.png")
  avatar_image = avatar_image.convert("RGBA")
  avatar_image.resize((128,128))
  base_bg.paste(avatar_image, (79, 583))

  # add screen glare to screen
  screen_glare = Image.open("./images/profiles/template_pieces/lcars/screen-glare.png").convert("RGBA")
  base_bg.paste(screen_glare, (0, 0), screen_glare)

  # add PADD frame to whole image
  padd_frame = Image.open("./images/profiles/template_pieces/lcars/padd-frame.png").convert("RGBA")
  base_bg.paste(padd_frame, (0, 0), padd_frame)

  # put sticker on
  if len(user["stickers"]) > 0 and user['stickers'][0]['sticker']:
    sticker_image = Image.open("./images/profiles/template_pieces/lcars/sticker-1.png").convert("RGBA")
    sticker_mask  = Image.open("./images/profiles/template_pieces/lcars/sticker-1-mask.png").convert("L").resize(sticker_image.size)
    sticker       = Image.open(f"./images/profiles/stickers/{user['stickers'][0]['sticker']}").convert("RGBA").resize(sticker_image.size)
    sticker_bg    = Image.open("./images/profiles/template_pieces/lcars/sticker-bg.png").convert("RGBA")
    composed  = Image.composite(sticker_image, sticker, sticker_mask).convert("RGBA")
    sticker_bg.paste(composed, (0, 0), composed)
    sticker_bg = sticker_bg.rotate(random.randint(-6,6), expand=True, resample=Image.BICUBIC)
    sticker_bg.save(f"./images/profiles/usersticker{member.id}.png")
    base_bg.paste(sticker_bg, (406+random.randint(-10,5), 886+random.randint(-3,3)), sticker_bg)

  # put badge on
  if len(user["badges"]) > 0 and user['badges'][0]['badge_filename']:
    badge_filename = user['badges'][0]['badge_filename']
    user_badges = db_get_user_badge_names(user['discord_id'])
    if badge_filename not in [b['badge_filename'] for b in user_badges]:
      # Catch if the user had a badge present that they no longer have, if so clear it from the table
      db_remove_user_profile_badge(user['discord_id'])
      if user["receive_notifications"]:
        try:
          await ctx.author.send(
            embed=discord.Embed(
              title="Profile Badge No Longer Present",
              description=f"Just a heads up, you had a badge on your profile previously, \"{badge_filename.replace('_', ' ').replace('.png', '')}\", which is no longer in your inventory.\n\nYou can set a new featured badge with `/set_profile_badge`!",
              color=discord.Color.red()
            )
          )
        except discord.Forbidden as e:
          logger.info(f"Unable to send notification to {ctx.author.display_name} regarding their cleared profile badge, they have their DMs closed.")
    else:
      # Otherwise go ahead and stamp the badge on their profile PADD
      badge_image = Image.open(f"./images/badges/{badge_filename}").convert("RGBA").resize((170, 170))
      base_bg.paste(badge_image, (540, 550), badge_image)


  # put polaroid on
  if user["photo"]:
    profile_photo = user['photo'].replace(" ", "_")
    photo_image = Image.open("./images/profiles/template_pieces/lcars/photo-frame.png").convert("RGBA")
    photo_content = Image.open(f"./images/profiles/polaroids/{profile_photo}.jpg").convert("RGBA")

    photo_filter = getattr(pilgram, random.choice(filters))
    photo_content = photo_filter(photo_content).convert("RGBA")

    photo_content.thumbnail((263, 200), Image.ANTIALIAS)
    photo_content = photo_content.crop((0,0,200,200))
    # photo_glare = Image.open("./images/profiles/template_pieces/lcars/photo-glare.png").convert("RGBA")
    # photo_content.paste(photo_glare, (0, 0), photo_glare)
    rotation = random.randint(-7, 7)
    photo_image.rotate(rotation, expand=True, resample=Image.BICUBIC)
    photo_content.rotate(rotation, expand=True, resample=Image.BICUBIC)
    base_bg.paste(photo_content, (6+22, 164+10), photo_content)
    base_bg.paste(photo_image, (6+random.randint(-1,1), 164+random.randint(-5,5)), photo_image)

  base_w, base_h = base_bg.size
  base_bg = base_bg.resize((int(base_w*2), int(base_h*2))) # makes it more legible maybe

  # finalize image
  base_bg.save("./images/profiles/drunkshimodanumber"+str(member.id)+".png")
  discord_image = discord.File("./images/profiles/drunkshimodanumber"+str(member.id)+".png")
  await ctx.followup.send(file=discord_image, ephemeral=not public)


# Queries
def db_remove_user_profile_badge(user_id):
  db = getDB()
  query = db.cursor()
  sql = "REPLACE INTO profile_badges (badge_filename, user_discord_id) VALUES (%(badge_filename)s, %(user_discord_id)s)"
  vals = {"badge_filename" : "", "user_discord_id" : user_id}
  logger.info(f"CLEARING PROFILE BADGE {sql}")
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_add_user_profile_badge(user_id, badge):
  db = getDB()
  query = db.cursor()
  sql = "REPLACE INTO profile_badges (badge_filename, user_discord_id) VALUES (%(badge_filename)s, %(user_discord_id)s)"
  vals = {"badge_filename" : badge, "user_discord_id" : user_id}
  logger.info(f"UPDATING PROFILE BADGE {sql} {vals}")
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

# Given a badge name, retrieves the badge_filename
def db_get_badge_filename_for_badge(badge_name):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT badge_filename FROM badge_info WHERE badge_name = %s"
  vals = (badge_name,)
  query.execute(sql, vals)
  row = query.fetchone()
  db.commit()
  query.close()
  db.close()

  return row['badge_filename']