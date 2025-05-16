from enum import Enum
import pilgram
import string

from common import *
from handlers.echelon_xp import xp_progress_within_level
from queries.badge_instances import *
from queries.crystal_instances import db_get_user_attuned_and_harmonized_crystals
from queries.echelon_xp import db_get_echelon_progress, db_get_legacy_xp_data
from utils.badge_utils import *
from utils.image_utils import draw_dynamic_text, generate_singular_badge_slot, buffer_image_to_discord_file, encode_webp
from utils.prestige import *

f = open(config["commands"]["shop"]["data"])
shop_data = json.load(f)
f.close()

def get_sticker_name_from_filename(filename):
  stickers = shop_data['stickers']
  sticker_name = ''
  for s in stickers:
    if s['file'] == filename:
      sticker_name = s['name']
      break

  return sticker_name

def get_sticker_filename_from_name(name):
  stickers = shop_data['stickers']
  sticker_filename = ''
  for s in stickers:
    if s['name'] == name:
      sticker_filename = s['file']
      break

  return sticker_filename

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
async def autocomplete_profile_badges(ctx: discord.AutocompleteContext):
  user_id = ctx.interaction.user.id
  prestige_level = int(ctx.options['prestige'])

  user_badge_instances = await db_get_user_badge_instances(user_id, prestige=prestige_level)

  results = [
    discord.OptionChoice(
      name=b['badge_name'],
      value=str(b['badge_instance_id'])
    )
    for b in user_badge_instances
  ]

  filtered = [r for r in results if ctx.value.lower() in r.name.lower()]
  if not filtered:
    filtered = [
      discord.OptionChoice(
        name="[ No Valid Options ]",
        value=None
      )
    ]
  return filtered

async def user_photos_autocomplete(ctx:discord.AutocompleteContext):
  user_photos = [s['item_name'] for s in await db_get_user_profile_photos_from_inventory(ctx.interaction.user.id)]
  if len(user_photos) == 0:
    user_photos = ["You don't have any additional photos yet!"]
    return user_photos

  user_photos.sort()
  user_photos.insert(0, '[CLEAR PHOTO]')

  return [result for result in user_photos if ctx.value.lower() in result.lower()]

async def user_stickers_autocomplete(ctx:discord.AutocompleteContext):
  user_stickers = [s['item_name'] for s in await db_get_user_profile_stickers_from_inventory(ctx.interaction.user.id)]
  if len(user_stickers) == 0:
    user_stickers = ["You don't have any additional stickers yet!"]
    return user_stickers

  user_stickers.sort()
  user_stickers.insert(0, '[CLEAR STICKER]')

  return [result for result in user_stickers if ctx.value.lower() in result.lower()]

async def user_styles_autocomplete(ctx:discord.AutocompleteContext):
  user_styles = [s['item_name'] for s in await db_get_user_profile_styles_from_inventory(ctx.interaction.user.id)]
  if len(user_styles) == 0:
    user_styles = ["You don't have any additional styles yet!"]
    return user_styles

  user_styles.sort()
  user_styles.insert(0, 'Default')

  return [result for result in user_styles if ctx.value.lower() in result.lower()]

async def photo_filters_autocomplete(ctx:discord.AutocompleteContext):
  filters = Profile.filters
  return ['random', 'none'] + filters


# __________                _____.__.__         _________
# \______   \_______  _____/ ____\__|  |   ____ \_   ___ \  ____   ____
#  |     ___/\_  __ \/  _ \   __\|  |  | _/ __ \/    \  \/ /  _ \ / ___\
#  |    |     |  | \(  <_> )  |  |  |  |_\  ___/\     \___(  <_> ) /_/  >
#  |____|     |__|   \____/|__|  |__|____/\___  >\______  /\____/\___  /
#                                             \/        \/      /_____/
class Profile(commands.Cog):
  filters = ["_1977", "aden", "brannan", "brooklyn", "clarendon", "earlybird", "gingham", "hudson", "inkwell", "kelvin", "lark", "lofi", "maven", "mayfair", "moon", "nashville", "perpetua", "reyes", "rise", "slumber", "stinson", "toaster", "valencia", "walden", "willow", "xpro2"]
  def __init__(self, bot):
    self.bot = bot

  profile = discord.SlashCommandGroup("profile", "Commands for displaying and customizing your profile")

  @profile.command(
    name="display",
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
  async def display(self, ctx:discord.ApplicationContext, public:str):
    """
    This function is the main entrypoint of the `/profile display` command
    and will return a user's profile card
    """
    public = bool(public == "yes")
    await ctx.defer(ephemeral=not public)

    member = ctx.author # discord obj
    member_id = str(member.id)
    user = await get_user(member_id) # our DB

    logger.info(f"{Fore.CYAN}{member.display_name} is looking at their own {Back.WHITE}{Fore.BLACK}profile card!{Back.RESET}{Fore.RESET}")

    # get rank
    ranks = ["admiral", "captain", "commander", "lt. commander", "lieutenant", "ensign", "cadet"]
    top_role = "Merchant"
    for role in member.roles:
      rolename = role.name.encode("ascii", errors="ignore").decode().strip().lower()
      for rank in ranks:
        if rolename == rank:
          top_role = string.capwords(rank)
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

    # User Stats
    echelon_progress = await db_get_echelon_progress(member_id)
    xp = echelon_progress.get('current_xp', 0)
    level = echelon_progress.get('current_level', 0)
    prestige_tier = echelon_progress.get('current_prestige_tier', 0)
    badges = await db_get_user_badge_instances(member_id)
    badge_count = len(badges)
    crystals = await db_get_user_attuned_and_harmonized_crystals(member_id)
    crystals_count = len(crystals)

    # Figure out their XP percentage towards their next Echelon Level:
    _, xp_into_level, xp_required = xp_progress_within_level(xp)
    percent_completed = xp_into_level / xp_required if xp_required else 0

    # Legacy XP Data
    legacy_xp_data = await db_get_legacy_xp_data(member_id)
    legacy_xp = legacy_xp_data.get('legacy_xp', 0)
    legacy_level = legacy_xp_data.get('legacy_level', 0)

    # fonts (same font, different sizes) used for building image
    name_font = ImageFont.truetype("fonts/lcars3.ttf", 61)
    agimus_font = ImageFont.truetype("fonts/lcars3.ttf", 22) # also legacy level/xp font
    level_font = ImageFont.truetype("fonts/lcars3.ttf", 50) # also main header font
    small_button_font = ImageFont.truetype("fonts/lcars3.ttf", 25)
    big_button_font = ImageFont.truetype("fonts/lcars3.ttf", 28)
    title_font = ImageFont.truetype("fonts/lcars3.ttf", 34) # also subtitle font and score font
    xp_font = ImageFont.truetype("fonts/lcars3.ttf", 30)
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
    # adjust shades of colors!
    for i in range(len(profile_shades)):
      #logger.info(f"Profile colors: {profile_color[0]} {profile_color[1]} {profile_color[2]}")
      #logger.info(f"Current shades: {profile_shades[i]} {profile_shades[i][0]} {profile_shades[i][1]} {profile_shades[i][2]}")
      r = sorted([profile_color[0]+profile_shades[i][0], 0, 255])[1]
      g = sorted([profile_color[1]+profile_shades[i][1], 0, 255])[1]
      b = sorted([profile_color[2]+profile_shades[i][2], 0, 255])[1]
      lcars_colors.append((r,g,b))

    if top_role == "Admiral":
      # special Sara colors
      lcars_colors  = [
        (66, 63, 69),
        (183, 183, 183),
        (216, 216, 216),
        (81, 81, 81),
        (123, 123, 123)
      ]

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
    draw.text( (283, 80), f"USS HOOD PERSONNEL FILE #{member_id[-4:]}", fill=random.choice(lcars_colors), font=level_font, align="right")
    draw.text( (79, 95), f"AGIMUS MAIN TERMINAL", fill="#dd4444", font=agimus_font, align="center",)

    # Draw User's Display Name and Tagline if present (Dynamic Sizes, Supports Emoji)
    await draw_dynamic_text(
      canvas=base_bg,
      draw=draw,
      position=(470, 150),
      text=member.display_name,
      max_width=940,
      font_obj=name_font,
      starting_size=54,
      min_size=20,
      fill=(255, 255, 255),
      centered=True
    )
    if user['profile_tagline']:
      tagline = user['profile_tagline']
      await draw_dynamic_text(
        canvas=base_bg,
        draw=draw,
        position=(470, 215),
        text=f'"{tagline}"',
        max_width=940,
        font_obj=entry_font,
        starting_size=40,
        min_size=15,
        fill=(255, 255, 255),
        centered=True
      )

    draw.text( (514 , 382), f"ECHELON: {level:04d}", fill="white", font=level_font, align="right")
    title_color = random.choice(lcars_colors[1:3])
    if legacy_xp_data:
      draw.text( (515, 430), f"LEGACY LEVEL:", fill=title_color, font=agimus_font, align="left")
      draw.text( (600, 430), f"{legacy_level}", fill="white", font=agimus_font, align="left")
      draw.text( (515, 455), f"LEGACY XP:", fill=title_color, font=agimus_font, align="left")
      draw.text( (584, 455), f"{legacy_xp}", fill="white", font=agimus_font, align="left")

    draw.text( (250, 385), f"CURRENT RANK:", fill=title_color, font=title_font, align="left")
    draw.text( (250, 418), f"{top_role}", fill="white", font=entry_font, align="left")
    draw.text( (250, 478), f"CURRENT ASSIGNMENT:", fill=title_color, font=title_font, align="left")
    draw.text( (250, 508), f"{second_role} / USS Hood NCC-42296", fill="white", font=entry_font, align="left")
    draw.text( (250, 568), f"DUTY STARTED:", fill=title_color, font=title_font, align="left")
    draw.text( (250, 598), f"{user_join}", fill="white", font=entry_font, align="left")
    draw.text( (400, 750), f"BADGES: {badge_count:04d}", fill="black", font=small_button_font, align="center", anchor="mm")
    draw.text( (400, 800), f"CRYSTALS: {crystals_count:04d}", fill="black", font=small_button_font, align="center", anchor="mm")
    draw.text( (595, 758), f"PRESTIGE TIER:", fill="black", font=big_button_font, align="center", anchor="mm")
    draw.text( (595, 788), f"{PRESTIGE_TIERS[prestige_tier]}", fill="black", font=title_font, align="center", anchor="mm")
    draw.text( (388, 851), f"ECHELON XP: {xp:07d}", fill="black", font=xp_font, align="right", anchor="rm")

    # add users avatar to card
    avatar = member.display_avatar.with_size(128)
    await avatar.save("./images/profiles/"+member_id+"_a.png")
    avatar_image = Image.open("./images/profiles/"+member_id+"_a.png")
    avatar_image = avatar_image.convert("RGBA")
    base_bg.paste(avatar_image, (79, 583))

    # add screen glare to screen
    screen_glare = Image.open("./images/profiles/template_pieces/lcars/screen-glare.png").convert("RGBA")
    base_bg.paste(screen_glare, (0, 0), screen_glare)

    # add PADD frame to whole image
    padd_style = await db_get_user_profile_style(member.id)
    frame_filename = f"padd-frame-{padd_style}.png"

    padd_frame = Image.open(f"./images/profiles/template_pieces/lcars/{frame_filename}").convert("RGBA")
    base_bg.paste(padd_frame, (0, 0), padd_frame)

    # put sticker on
    if len(user["stickers"]) > 0 and user['stickers'][0]['sticker'] and user['stickers'][0]['sticker'] != "none":
      sticker_selection = user['stickers'][0]['sticker']
      if '.png' not in sticker_selection:
        sticker_selection = get_sticker_filename_from_name(sticker_selection)
      sticker_image = Image.open("./images/profiles/template_pieces/lcars/sticker-1.png").convert("RGBA")
      sticker_mask  = Image.open("./images/profiles/template_pieces/lcars/sticker-1-mask.png").convert("L").resize(sticker_image.size)
      sticker       = Image.open(f"./images/profiles/stickers/{sticker_selection}").convert("RGBA").resize(sticker_image.size)
      sticker_bg    = Image.open("./images/profiles/template_pieces/lcars/sticker-bg.png").convert("RGBA")
      composed  = Image.composite(sticker_image, sticker, sticker_mask).convert("RGBA")
      sticker_bg.paste(composed, (0, 0), composed)
      sticker_bg = sticker_bg.rotate(random.randint(-6,6), expand=True, resample=Image.BICUBIC)
      sticker_bg.save(f"./images/profiles/usersticker{member.id}.png")
      sticker_offset = 406
      if padd_style == "Latinum":
        sticker_offset = 466
      base_bg.paste(sticker_bg, (sticker_offset+random.randint(-10,5), 886+random.randint(-3,3)), sticker_bg)

    # put polaroid on
    if user["profile_photo"] and user["profile_photo"] != "none":
      profile_photo = user['profile_photo'].replace(" ", "_")
      photo_image = Image.open("./images/profiles/template_pieces/lcars/photo-frame.png").convert("RGBA")
      photo_content = Image.open(f"./images/profiles/polaroids/{profile_photo}.jpg").convert("RGBA")

      user_filter = await db_get_user_profile_photo_filter(ctx.author.id)
      if user_filter:
        if user_filter != 'random':
          photo_filter = getattr(pilgram, user_filter)
        else:
          photo_filter = getattr(pilgram, random.choice(Profile.filters))
        photo_content = photo_filter(photo_content).convert("RGBA")

      photo_content.thumbnail((263, 200), Image.Resampling.LANCZOS)
      photo_content = photo_content.crop((0,0,200,200))
      # photo_glare = Image.open("./images/profiles/template_pieces/lcars/photo-glare.png").convert("RGBA")
      # photo_content.paste(photo_glare, (0, 0), photo_glare)
      rotation = random.randint(-7, 7)
      photo_image.rotate(rotation, expand=True, resample=Image.BICUBIC)
      photo_content.rotate(rotation, expand=True, resample=Image.BICUBIC)
      base_bg.paste(photo_content, (6+22, 164+10), photo_content)
      base_bg.paste(photo_image, (6+random.randint(-1,1), 164+random.randint(-5,5)), photo_image)

    base_w, base_h = base_bg.size
    base_canvas = base_bg.resize((int(base_w*2), int(base_h*2))) # makes it more legible maybe
    base_canvas = base_canvas.convert("RGB") # discard alpha to prevent flickering if badge frames are applied

    # Generate Final Frames with Profile Badge if present
    profile_frames = []
    profile_badge_instance_id = await db_get_user_profile_badge_instance_id(member.id)
    if profile_badge_instance_id:
      badge_instance = await db_get_badge_instance_by_id(profile_badge_instance_id)
      badge_is_valid = badge_instance['owner_discord_id'] == str(member.id) and badge_instance['status'] == 'active'

      if badge_is_valid:
        badge_frames = await generate_singular_badge_slot(badge_instance, border_color=random.choice(lcars_colors))
        for frame in badge_frames:
          frame = frame.resize((340, 340), resample=Image.Resampling.LANCZOS)
          final_canvas = base_canvas.copy()
          final_canvas.paste(frame, (1080, 1100), frame)
          profile_frames.append(final_canvas)
      else:
        # Catch that the user had a badge present that they no longer have, so clear it from the DB and alert them
        profile_frames = [base_canvas]
        await db_remove_user_profile_badge(member.id)
        if user["receive_notifications"]:
          try:
            await ctx.author.send(
              embed=discord.Embed(
                title="Profile Badge No Longer Present",
                description=f"Just a heads up, you had a badge on your profile previously, \"{badge_instance['badge_name']}\", which is no longer in your inventory.\n\nYou can set a new featured badge with `/profile set_badge`!",
                color=discord.Color.red()
              )
            )
          except discord.Forbidden as e:
            logger.info(f"Unable to send notification to {ctx.author.display_name} regarding their cleared profile badge, they have their DMs closed.")

    else:
      # No badge selected, just set a single frame of the badgeless PADD
      profile_frames = [base_canvas]

    if len(profile_frames) > 1:
      buf = await encode_webp(profile_frames)
      await ctx.followup.send(file=discord.File(buf, filename='profile_card.webp'), ephemeral=not public)
    else:
      file = buffer_image_to_discord_file(profile_frames[0], 'profile_card.png')
      await ctx.followup.send(file=file, ephemeral=not public)

    return


  @profile.command(
    name="set",
    description="Change your profile settings"
  )
  @option(
    name="tagline",
    description="Your tagline or \"none\" to make blank (follow the server rules please!)",
    required=False
  )
  @option(
    name="photo",
    description="Your PADD photo",
    required=False,
    autocomplete=user_photos_autocomplete
  )
  @option(
    name="sticker",
    description="Your PADD sticker",
    required=False,
    autocomplete=user_stickers_autocomplete
  )
  @option(
    name="style",
    description="Your PADD style",
    required=False,
    autocomplete=user_styles_autocomplete
  )
  @option(
    name="photo_filter",
    description="The photo filter you want applied to your profile photo",
    required=False,
    autocomplete=photo_filters_autocomplete
  )
  async def set(self, ctx:discord.ApplicationContext,
                tagline: str, photo: str, sticker: str, style: str, photo_filter: str):
    """
    Set all profile PADD at once.  At least make it less redundant.
    """
    messages = []
    if tagline is not None:
      messages.append(await self.set_tagline(ctx, tagline))

    if photo is not None:
      messages.append(await self.set_photo(ctx, photo))

    if sticker is not None:
      messages.append(await self.set_sticker(ctx, sticker))

    if style is not None:
      messages.append(await self.set_style(ctx, style))

    if photo_filter is not None:
      messages.append(await self.set_photo_filter(ctx, photo_filter))

    messages = [m for m in messages if m is not None]

    if len(messages) == 0:
      await ctx.respond(embed=discord.Embed(
        title="You need to set at least one value to make changes",
        description="\n\n".join(messages),
        color=discord.Color.red(),
      ), ephemeral=True)
      return

    messages.append("Use `/profile display` to check it out!")

    await ctx.respond(embed=discord.Embed(
      title="Updated Profile Settings",
      description="\n\n".join(messages),
      color=discord.Color.green(),
    ), ephemeral=True)


  @profile.command(
    name="set_badge",
    description="Set your featured Badge"
  )
  @option(
    name="prestige",
    description="Which Prestige Tier?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @option(
    "badge",
    str,
    description="The Badge to feature",
    required=True,
    autocomplete=autocomplete_profile_badges
  )
  async def set_badge(self, ctx:discord.ApplicationContext, prestige:str, badge:str):
    """
    Set a user's badge for their profile card
    """
    await ctx.defer(ephemeral=True)
    user_id = str(ctx.author.id)

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)
    badge_instance_id = int(badge)

    # Check to make sure they own the badge
    badge_instance = await db_get_badge_instance_by_id(badge_instance_id)

    if not badge_instance or badge_instance['owner_discord_id'] != user_id:
      await ctx.respond(embed=discord.Embed(
        title="Unable To Set Featured Profile Badge",
        description="You don't appear to own that Badge at the specified Prestige Tier.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    # If it looks good, go ahead and set the badge
    await db_add_user_profile_badge(ctx.author.id, badge_instance_id)
    badge_name = badge_instance['badge_name']
    logger.info(f'{Fore.CYAN}{ctx.author.display_name}{Fore.RESET} has {Style.BRIGHT}changed their profile badge{Style.RESET_ALL} to: {Style.BRIGHT}"{badge_name}"{Style.RESET_ALL}')
    await ctx.respond(embed=discord.Embed(
      title="Successfully Set Featured Profile Badge",
      description=f'You have successfully set "{badge_name}" as your profile badge.',
      color=discord.Color.green()
    ), ephemeral=True)
    return

  @profile.command(
    name="remove_badge",
    description="Remove your featured Badge"
  )
  async def remove_badge(self, ctx:discord.ApplicationContext):
    """
    Remove a user's featured profile badge (if present)
    """
    await ctx.defer(ephemeral=True)
    user_id = str(ctx.author.id)

    await db_remove_user_profile_badge(user_id)

    await ctx.respond(embed=discord.Embed(
      title="Successfully Removed Featured Profile Badge",
      description=f'You have cleared your profile badge.',
      color=discord.Color.green()
    ), ephemeral=True)
    return


  async def set_tagline(self, ctx:discord.ApplicationContext, tagline:str) -> str:
    """
    Set a user's tagline for their profile card
    Users can also unset it by sending an empty string
    """
    if tagline.strip().lower() in ("", 'none'):
      await db_remove_user_profile_tagline(ctx.author.id)
      logger.info(f"{Fore.CYAN}{ctx.author.display_name}{Fore.RESET} has {Style.BRIGHT}removed their tagline!{Style.RESET_ALL}")
      return "Your tagline has been cleared!"
    else:
      tagline = tagline[0:38].strip()
      await db_add_user_profile_tagline(ctx.author.id, tagline)
      msg = f"Your tagline has been updated to \"{tagline}\""
      if tagline.encode('latin-1', errors='ignore').decode('latin-1') != tagline:
        msg += f'\nIt looks like you are using Unicode characters, and those might not show up.'
      logger.info(f"{Fore.CYAN}{ctx.author.display_name}{Fore.RESET} has {Style.BRIGHT}changed their tagline{Style.RESET_ALL} to: {Style.BRIGHT}\"{tagline}\"{Style.RESET_ALL}")
    return msg

  async def set_photo(self, ctx:discord.ApplicationContext, photo:str) -> str:
    """
    Set a user's PADD photo for their profile out of a list of what they have available in their inventory
    """
    # User selected the warning message, return as no-op
    if photo == "You don't have any additional photos yet!":
      return None

    # Remove photo if desired by user
    remove = bool(photo == '[CLEAR PHOTO]')
    if remove:
      await db_update_user_profile_photo(ctx.author.id, "none")
      logger.info(f"{Fore.CYAN}{ctx.author.display_name}{Fore.RESET} has {Style.BRIGHT}removed their profile photo!{Style.RESET_ALL}")
      return "Cleared Profile Photo"

    # Check to make sure they own the photo
    user_photos = [s['item_name'] for s in await db_get_user_profile_photos_from_inventory(ctx.author.id)] + ['None']
    if photo not in user_photos:
      await ctx.respond(embed=discord.Embed(
        title="Unable To Set Featured PADD Photo",
        description="You don't appear to own that photo yet!",
        color=discord.Color.red()
      ), ephemeral=True)
      return None

    # If it looks good, go ahead and change the sticker
    await db_update_user_profile_photo(ctx.author.id, photo)
    logger.info(f"{Fore.CYAN}{ctx.author.display_name}{Fore.RESET} has {Style.BRIGHT}changed their profile photo{Style.RESET_ALL} to: {Style.BRIGHT}\"{photo}\"{Style.RESET_ALL}")
    return f"You've successfully set your PADD photo as \"{photo}\""

  async def set_sticker(self, ctx:discord.ApplicationContext, sticker:str) -> str:
    """
    set a user's PADD sticker for their profile out of a list of what they have available in their inventory
    """
    # User selected the warning message, return as no-op
    if sticker == "You don't have any additional stickers yet!":
      return None

    # Remove sticker if desired by user
    remove = bool(sticker == '[CLEAR STICKER]')
    if remove:
      await db_update_user_profile_sticker(ctx.author.id, "none")
      logger.info(f"{Fore.CYAN}{ctx.author.display_name}{Fore.RESET} has {Style.BRIGHT}removed their profile sticker!{Style.RESET_ALL}")
      return "Cleared Profile Sticker"

    # Check to make sure they own the sticker
    user_stickers = [s['item_name'] for s in await db_get_user_profile_stickers_from_inventory(ctx.author.id)] + ['Default']
    if sticker not in user_stickers:
      await ctx.respond(embed=discord.Embed(
        title="Unable To Set Featured PADD Sticker",
        description="You don't appear to own that sticker yet!",
        color=discord.Color.red()
      ), ephemeral=True)
      return None

    # If it looks good, go ahead and change the sticker
    await db_update_user_profile_sticker(ctx.author.id, sticker)
    logger.info(f"{Fore.CYAN}{ctx.author.display_name}{Fore.RESET} has {Style.BRIGHT}changed their profile sticker{Style.RESET_ALL} to: {Style.BRIGHT}\"{sticker}\"{Style.RESET_ALL}")
    return f"You've successfully set your PADD sticker as \"{sticker}\""

  async def set_style(self, ctx:discord.ApplicationContext, style:str):
    """
    set a user's PADD style for their profile out of a list of what they have available in their inventory
    """
    # User selected the warning message, return as no-op
    if style == "You don't have any additional styles yet!":
      return None

    # Check to make sure they own the style
    user_styles = [s['item_name'] for s in await db_get_user_profile_styles_from_inventory(ctx.author.id)] + ['Default']
    if style not in user_styles:
      await ctx.respond(embed=discord.Embed(
        title="Unable To Set Featured PADD Style",
        description="You don't appear to own that style yet!",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    # If it looks good, go ahead and change the style
    await db_update_user_profile_style(ctx.author.id, style)
    logger.info(f"{Fore.CYAN}{ctx.author.display_name}{Fore.RESET} has {Style.BRIGHT}changed their profile style{Style.RESET_ALL} to: {Style.BRIGHT}\"{style}\"{Style.RESET_ALL}")
    return f"You've successfully set your PADD style as \"{style}\""

  async def set_photo_filter(self, ctx:discord.ApplicationContext, filter:str) -> str:
    """ allows a user to set their own instagram-style photo filter on their profile photo """
    filter = filter.lower()
    if filter not in Profile.filters and filter not in ['random', 'none']:
      await ctx.respond(
        embed=discord.Embed(
          title="That filter doesn't exist!",
          description="What the devil is going on here, Q",
          color=discord.Color.red()
        ), ephemeral=True
      )
      return None
    else:
      await db_update_user_profile_photo_filter(ctx.author.id, filter)
      logger.info(f"{Fore.CYAN}{ctx.author.display_name}{Fore.RESET} has {Style.BRIGHT}changed their photo filter{Style.RESET_ALL} to: {Style.BRIGHT}\"{filter}\"{Style.RESET_ALL}")
    return f"Profile photo filter has been changed to **{filter}**!"


# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/

# Tagline
async def db_remove_user_profile_tagline(user_id):
  async with AgimusDB() as query:
    sql = "REPLACE INTO profile_taglines (tagline, user_discord_id) VALUES (%(tagline)s, %(user_discord_id)s)"
    vals = {"tagline" : "", "user_discord_id" : user_id}
    await query.execute(sql, vals)

async def db_add_user_profile_tagline(user_id, tagline):
  async with AgimusDB() as query:
    sql = "REPLACE INTO profile_taglines (tagline, user_discord_id) VALUES (%(tagline)s, %(user_discord_id)s)"
    vals = {"tagline" : tagline, "user_discord_id" : user_id}
    await query.execute(sql, vals)

# Badges
async def db_get_user_profile_badge_instance_id(user_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT badge_instance_id FROM profile_badge_instances WHERE user_discord_id = %s"
    vals = (user_id,)
    await query.execute(sql, vals)
    result = await query.fetchone()
  if result:
    return result['badge_instance_id']
  else:
    return None

async def db_remove_user_profile_badge(user_id):
  async with AgimusDB() as query:
    sql = "REPLACE INTO profile_badge_instances (badge_instance_id, user_discord_id) VALUES (%(badge_instance_id)s, %(user_discord_id)s)"
    vals = {"badge_instance_id" : None, "user_discord_id" : user_id}
    await query.execute(sql, vals)

async def db_add_user_profile_badge(user_id, badge_instance_id):
  async with AgimusDB() as query:
    sql = "REPLACE INTO profile_badge_instances (badge_instance_id, user_discord_id) VALUES (%(badge_instance_id)s, %(user_discord_id)s)"
    vals = {"badge_instance_id" : badge_instance_id, "user_discord_id" : user_id}
    await query.execute(sql, vals)

# Photos
async def db_get_user_profile_photos_from_inventory(user_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM profile_inventory WHERE user_discord_id = %s AND item_category = 'photo'"
    vals = (user_id,)
    await query.execute(sql, vals)
    results = await query.fetchall()
  return results

async def db_get_user_profile_photo(user_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT photo FROM profile_photos WHERE user_discord_id = %s"
    vals = (user_id,)
    await query.execute(sql, vals)
    result = await query.fetchone()
  if result:
    return result['photo']
  else:
    return 'Default'

async def db_update_user_profile_photo(user_id, photo):
  async with AgimusDB() as query:
    sql = "REPLACE INTO profile_photos (photo, user_discord_id) VALUES (%(photo)s, %(user_discord_id)s)"
    vals = {"photo" : photo.lower(), "user_discord_id" : user_id}
    await query.execute(sql, vals)

# Stickers
async def db_get_user_profile_stickers_from_inventory(user_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM profile_inventory WHERE user_discord_id = %s AND item_category = 'sticker'"
    vals = (user_id,)
    await query.execute(sql, vals)
    results = await query.fetchall()
  return results

async def db_get_user_profile_sticker(user_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT sticker FROM profile_stickers WHERE user_discord_id = %s"
    vals = (user_id,)
    await query.execute(sql, vals)
    result = await query.fetchone()
  return result['sticker']

async def db_update_user_profile_sticker(user_id, sticker):
  if sticker != 'none':
    sticker = get_sticker_filename_from_name(sticker)
  async with AgimusDB() as query:
    sql = "REPLACE INTO profile_stickers (sticker, user_discord_id) VALUES (%(sticker)s, %(user_discord_id)s)"
    vals = {"sticker" : sticker, "user_discord_id" : user_id}
    await query.execute(sql, vals)

# Styles
async def db_get_user_profile_styles_from_inventory(user_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM profile_inventory WHERE user_discord_id = %s AND item_category = 'style'"
    vals = (user_id,)
    await query.execute(sql, vals)
    results = await query.fetchall()
  return results

async def db_get_user_profile_style(user_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT style FROM profile_style WHERE user_discord_id = %s"
    vals = (user_id,)
    await query.execute(sql, vals)
    result = await query.fetchone()
  if result:
    return result['style']
  else:
    return 'Default'

async def db_update_user_profile_style(user_id, style):
  async with AgimusDB() as query:
    sql = "REPLACE INTO profile_style (style, user_discord_id) VALUES (%(style)s, %(user_discord_id)s)"
    vals = {"style" : style, "user_discord_id" : user_id}
    await query.execute(sql, vals)

# photo filters
async def db_get_user_profile_photo_filter(user_id:int):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT filter FROM profile_photo_filters WHERE user_discord_id = %s"
    vals = (user_id,)
    await query.execute(sql, vals)
    result = await query.fetchone()
  if result:
    if str(result['filter']).lower() == 'none':
      return None
    else:
      return str(result['filter']).lower()
  else:
    return 'random'

async def db_update_user_profile_photo_filter(user_id:int, filter:str):
  async with AgimusDB() as query:
    sql = "REPLACE INTO profile_photo_filters (filter, user_discord_id) VALUES (%(filter)s, %(user_discord_id)s)"
    vals = {"filter" : filter.lower(), "user_discord_id" : user_id}
    await query.execute(sql,vals)