from common import *
from handlers.xp import calculate_xp_for_next_level
from commands.badges import get_user_badges
from utils.check_channel_access import access_check
import pilgram

@bot.slash_command(
  name="set_tagline",
  description="Set your profile tagline (or unset it!)"
)
@option(
  name="tagline",
  description="Your tagline (up to 60 characters, follow the server rules please!)"
)
async def set_tagline(ctx:discord.ApplicationContext, tagline:str):
  if not tagline or tagline.strip() == "":
    db = getDB()
    query = db.cursor()
    sql = "UPDATE users SET tagline = %s WHERE discord_id = %s"
    vals = ("", ctx.author.id)
    query.execute(sql, vals)
    db.commit()
    query.close()
    db.close()
    await ctx.respond(f"Your tagline has been cleared!", ephemeral=True)
  else:
    tagline = tagline[0:60].encode("ascii", errors="ignore").decode().strip()
    db = getDB()
    query = db.cursor()
    sql = "UPDATE users SET tagline = %s WHERE discord_id = %s"
    vals = (tagline, ctx.author.id)
    query.execute(sql, vals)
    db.commit()
    query.close()
    db.close()
    await ctx.respond(f"Your tagline has been updated!", ephemeral=True)
    logger.info(f"{ctx.author} has changed their tagline to: \"{tagline}\"")


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

  user_name = f"{member.display_name}"
  user_name_encode = user_name.encode("ascii", errors="ignore")
  user_name = user_name_encode.decode().strip()

  top_role = member.top_role
  top_role_name = top_role.name.encode("ascii", errors="ignore")
  top_role = top_role_name.decode().strip()

  assignments = [993234668428206114, 993234668428206113, 993234668428206112, 993234668428206111, 993234668394664015, 993234668394664014, 993234668394664013, 993234668394664012, 993234668394664011]
  assignment_names = []
  for role in member.roles:
    if role.id in assignments:
      assignment_names.append(role.name)

  if len(assignment_names) <= 0:
    second_role = "Stowaway"
  else:
    second_role = assignment_names[-1]
  user_join = member.joined_at.strftime("%d %B %Y")
  score = user["score"]
  spins = user["spins"]
  level = user["level"]
  xp = user["xp"]
  badges = get_user_badges(member.id)
  badge_count = len(badges)
  next_level = calculate_xp_for_next_level(level)
  percent_completed = (xp/next_level)

  # fonts (same font, different sizes) used for building image
  name_font = ImageFont.truetype("images/lcars3.ttf", 61)
  agimus_font = ImageFont.truetype("images/lcars3.ttf", 22)
  level_font = ImageFont.truetype("images/lcars3.ttf", 50) # also main header font
  small_button_font = ImageFont.truetype("images/lcars3.ttf", 24)
  big_button_font = ImageFont.truetype("images/lcars3.ttf", 28)
  title_font = ImageFont.truetype("images/lcars3.ttf", 34) # also subtitle font and score font
  xp_font = ImageFont.truetype("images/lcars3.ttf", 32)
  entry_font = ImageFont.truetype("images/lcars3.ttf", 40)


  # build black BG
  # draw XP bar
  # load & color & paste template parts
  # add text
  # add lcars frame
  # add photo, stickers, etc

  base_bg = Image.new(mode="RGBA", size=(787, 1024))
  padd_bg = Image.new(size=(700, 839), color="black", mode="RGBA")
  base_bg.paste(padd_bg, (41, 50), padd_bg)

  profile_color = member.color.to_rgb()
  if member.color.value == 0:
    # default to white lcars
    profile_color = (255, 255, 255)


  template_pieces = [
    "./images/profiles/template_pieces/lcars/lighter-pieces.png",
    "./images/profiles/template_pieces/lcars/pieces-1.png",
    "./images/profiles/template_pieces/lcars/pieces-2.png",
    "./images/profiles/template_pieces/lcars/pieces-3.png",
    "./images/profiles/template_pieces/lcars/xp-bar.png"
  ]

  # will probably need a better lightening method
  profile_shades = [
    (random.randint(25,40), random.randint(25,40), random.randint(25,40)), # lighten up the first element
    (random.randint(-25,25), random.randint(-25,25), random.randint(-25,25)),
    (random.randint(-45,45), random.randint(-45,45), random.randint(-45,45)),
    (random.randint(-35,35), random.randint(-35,35), random.randint(-35,35)),
    (random.randint(128,128), random.randint(128,128), random.randint(128,128)), # lighten up the xp element too
  ]

  lcars_colors = []
  admiral_colors = [
    (255, 255, 0),
    (0, 164, 164),
    (200, 200, 0),
    (0, 128, 128),
    (200, 200, 0)
  ]

  # adjust shades of colors!
  for i in range(len(profile_shades)):
    logger.info(f"Profile colors: {profile_color[0]} {profile_color[1]} {profile_color[2]}")
    logger.info(f"Current shades: {profile_shades[i]} {profile_shades[i][0]} {profile_shades[i][1]} {profile_shades[i][2]}")
    r = sorted([profile_color[0]+profile_shades[i][0], 0, 255])[1]
    g = sorted([profile_color[1]+profile_shades[i][1], 0, 255])[1]
    b = sorted([profile_color[2]+profile_shades[i][2], 0, 255])[1]
    lcars_colors.append((r,g,b))

  if profile_color == (12, 13, 14):
    lcars_colors = admiral_colors

  draw = ImageDraw.Draw(base_bg) # pencil time
  
  # draw xp progress
  w, h = 244, 26
  x, y = 394, 839
  shape =(x+32, y, min(percent_completed, 1)*(w)+x, h+y)
  draw.rectangle(shape, fill=lcars_colors[2])

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
  draw.text( (250, 598), f"{user_join}", fill="white", font=entry_font, align="left")

  draw.text( (485, 698), f"BADGES: {badge_count:03d}", fill="black", font=small_button_font, align="center")
  draw.text( (624, 698), f"SPINS: {spins:04d}", fill="black", font=small_button_font, align="center")
  draw.text( (510, 755), f"RECREATIONAL CREDITS:", fill="black", font=big_button_font, align="center")
  draw.text( (555, 783), f"{score:08d}", fill="black", font=title_font, align="center")

  draw.text( (388, 850), f"XP: {xp:05d}", fill="black", font=xp_font, align="right", anchor="rm")
  #draw.text( (397, 840), f"{xp}", fill="black", font=title_font, align="left")

  avatar = member.display_avatar.with_size(128)
  await avatar.save("./images/profiles/"+str(member.id)+"_a.png") 
  avatar_image = Image.open("./images/profiles/"+str(member.id)+"_a.png")
  avatar_image = avatar_image.convert("RGBA")
  avatar_image.resize((128,128))
  base_bg.paste(avatar_image, (79, 583))

  screen_glare = Image.open("./images/profiles/template_pieces/lcars/screen-glare.png").convert("RGBA")
  base_bg.paste(screen_glare, (0, 0), screen_glare)

  padd_frame = Image.open("./images/profiles/template_pieces/lcars/padd-frame.png").convert("RGBA")
  base_bg.paste(padd_frame, (0, 0), padd_frame)

  if user["profile_badge"]:
    sticker_image = Image.open("./images/profiles/template_pieces/lcars/sticker-1.png").convert("RGBA")
    sticker_mask  = Image.open("./images/profiles/template_pieces/lcars/sticker-1-mask.png").convert("L").resize(sticker_image.size)
    sticker       = Image.open(f"./images/profiles/badges/{user['profile_badge']}").convert("RGBA").resize(sticker_image.size)
    sticker_bg    = Image.open("./images/profiles/template_pieces/lcars/sticker-bg.png").convert("RGBA")
    composed  = Image.composite(sticker_image, sticker, sticker_mask).convert("RGBA")
    sticker_bg.paste(composed, (0, 0), composed)
    sticker_bg = sticker_bg.rotate(random.randint(-6,6), expand=True, resample=Image.BICUBIC)
    sticker_bg.save(f"./images/profiles/usersticker{member.id}.png")
    base_bg.paste(sticker_bg, (406+random.randint(-10,5), 886+random.randint(-3,3)), sticker_bg)

  if user["profile_card"]:
    profile_card = user['profile_card'].replace(" ", "_")
    photo_image = Image.open("./images/profiles/template_pieces/lcars/photo-frame.png").convert("RGBA")
    photo_content = Image.open(f"./images/profiles/polaroids/{profile_card}.jpg").convert("RGBA")
    photo_content = pilgram.nashville(photo_content).convert("RGBA")
    photo_content.thumbnail((263, 200), Image.ANTIALIAS)
    photo_content = photo_content.crop((0,0,200,200))
    photo_glare = Image.open("./images/profiles/template_pieces/lcars/photo-glare.png").convert("RGBA")
    photo_content.paste(photo_glare, (0, 0), photo_glare)

    rotation = random.randint(-7, 7)
    photo_image.rotate(rotation, expand=True, resample=Image.BICUBIC)
    photo_content.rotate(rotation, expand=True, resample=Image.BICUBIC)
    base_bg.paste(photo_content, (6+20, 164+10), photo_content)
    base_bg.paste(photo_image, (6+random.randint(-1,1), 164+random.randint(-5,5)), photo_image)
  
  base_w, base_h = base_bg.size
  base_bg = base_bg.resize((int(base_w*2), int(base_h*2)))
  # finalize image
  base_bg.save("./images/profiles/drunkshimodanumber"+str(member.id)+".png")
  discord_image = discord.File("./images/profiles/drunkshimodanumber"+str(member.id)+".png")
  await ctx.followup.send(file=discord_image, ephemeral=not public)
