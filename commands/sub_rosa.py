import time
import pytz

from common import *
from utils.check_channel_access import access_check
from utils.check_role_access import role_check

# Create drop Slash Command Group
sub_rosa = bot.create_group("sub_rosa", "Sub Rosa Tracker Commands!")

@sub_rosa.command(
  name="reset",
  description="Reset the days since last Sub Rosa Watch",
)
@commands.check(role_check)
async def reset(ctx: discord.ApplicationContext):
  await ctx.defer()

  previous_reset = await db_get_previous_reset()
  stats = await db_get_sub_rosa_stats()
  total_watches = stats['total_watches'] + 1
  if 30 <= total_watches < 40:
    total_watches = f"{total_watches}... *Thirties...*"

  embed = discord.Embed(
    title="Resetting Days Since Last Sub Rosa Watch...",
    description=f"{ctx.author.mention} is vaporizing the candle! {get_emoji('dinnae_light_that_candle_ghost')}",
    color=discord.Color.dark_green()
  )

  if previous_reset:
    pst_tz = pytz.timezone('America/Los_Angeles')
    raw_now = datetime.utcnow().replace(tzinfo=pytz.utc)
    raw_time_created = pytz.utc.localize(previous_reset['time_created'])
    aware_now = pst_tz.normalize(raw_now.astimezone(pst_tz))
    aware_time_created = pst_tz.normalize(raw_time_created.astimezone(pst_tz))

    lifespan = aware_now - aware_time_created
    days = lifespan.days

    embed.add_field(
      name="Previous Days",
      value=f"{days} {'Day' if days == 1 else 'Days'}",
    )
    embed.add_field(
      name="Total Watches",
      value=f"{total_watches}",
      inline=False
    )
    embed.add_field(
      name="Average Days Between Watches",
      value=int(stats['average_days']),
      inline=False
    )

  await db_reset_days(ctx.author.id)

  gif = await generate_sub_rosa_reset_gif(days)
  embed.set_image(url=f"attachment://{gif.filename}")
  embed.set_footer(text=get_random_footer_text())
  await ctx.followup.send(embed=embed, file=gif)

@sub_rosa.command(
  name="check",
  description="Check how many days it's been since last Sub Rosa Watch",
)
@commands.check(access_check)
async def check(ctx: discord.ApplicationContext):
  previous_reset = await db_get_previous_reset()

  if not previous_reset:
    await ctx.respond(
      embed=discord.Embed(
        title="No Watches Registered Yet!",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  await ctx.defer()

  stats = await db_get_sub_rosa_stats()

  pst_tz = pytz.timezone('America/Los_Angeles')
  raw_now = datetime.utcnow().replace(tzinfo=pytz.utc)
  raw_time_created = pytz.utc.localize(previous_reset['time_created'])
  aware_now = pst_tz.normalize(raw_now.astimezone(pst_tz))
  aware_time_created = pst_tz.normalize(raw_time_created.astimezone(pst_tz))

  lifespan = aware_now - aware_time_created
  days = lifespan.days

  embed = discord.Embed(
    title=f"The Last Sub Rosa Watch...",
    description=f"was {days} {'Day' if days == 1 else 'Days'} ago... {get_emoji('beverly_horny_ghost_orgasm')}",
    color=discord.Color.dark_green()
  )

  embed.add_field(
    name="Previous Days Streak",
    value=f"{days} {'Day' if days == 1 else 'Days'}",
  )

  longest_reset = await db_get_longest_reset()
  if previous_reset['id'] == longest_reset['id']:
    embed.add_field(
      name="All-Time Longest Streak Was The Previous!",
      value=f"That must have been a particularly *un-erotic* \nchapter of Bev's Grandmother's journal! 🕯️",
      inline=False
    )
  else:
    streak = longest_reset['duration'] // 86400
    embed.add_field(
      name="All-Time Longest Streak",
      value=f"{streak} {'Day' if streak == 1 else 'Days'}",
      inline=False
    )

  embed.add_field(
    name="Total Number of Watches",
    value=stats['total_watches'],
    inline=False
  )
  embed.add_field(
    name="Average Days Between Watches",
    value=int(stats['average_days']),
    inline=False
  )

  png = await generate_sub_rosa_check_png(days)
  embed.set_image(url=f"attachment://{png.filename}")
  embed.set_footer(text=get_random_footer_text())
  await ctx.followup.send(embed=embed, file=png)

@to_thread
def generate_sub_rosa_check_png(days):
  marker_font = ImageFont.truetype("fonts/PermanentMarker.ttf", 200)

  base_width = 600
  base_height = 775

  sub_rosa_sign_image = Image.open("./images/templates/sub_rosa/blank_sign.png").convert("RGBA")
  sub_rosa_base_image = Image.new("RGBA", (base_width, base_height), (0, 0, 0))
  sub_rosa_base_image.paste(sub_rosa_sign_image, (0, 0))

  d = ImageDraw.Draw(sub_rosa_base_image)
  d.text((base_width / 2, 200), f"{days}", fill=(0, 0, 0, 255), font=marker_font, anchor="mm", align="center")

  image_filename = "current_days.png"
  image_filepath = f"./images/sub_rosa/{image_filename}"
  if os.path.exists(image_filepath):
    os.remove(image_filepath)

  sub_rosa_base_image.save(image_filepath)

  while True:
    time.sleep(0.05)
    if os.path.isfile(image_filepath):
      break

  discord_image = discord.File(fp=image_filepath, filename=image_filename)
  return discord_image

@to_thread
def generate_sub_rosa_reset_gif(days):
  marker_font = ImageFont.truetype("fonts/PermanentMarker.ttf", 200)

  base_width = 600
  base_height = 775

  sub_rosa_sign_image = Image.open("./images/templates/sub_rosa/blank_sign.png").convert("RGBA")
  sub_rosa_base_image = Image.new("RGBA", (base_width, base_height), (0, 0, 0))
  sub_rosa_base_image.paste(sub_rosa_sign_image, (0, 0))

  base_text_frame = sub_rosa_base_image.copy()
  d = ImageDraw.Draw(base_text_frame)
  d.text((base_width / 2, 200), f"{days}", fill=(0, 0, 0, 255), font=marker_font, anchor="mm", align="center")
  frames = [base_text_frame] * 20

  # Eraser Wipe
  for n in range(0, 54):
    frame = base_text_frame.copy()
    wipe_frame = Image.open(f"./images/templates/shared/warning_signs/wipe/{'{:02d}'.format(n)}.png").convert('RGBA')
    frame.paste(wipe_frame, (110, 85), wipe_frame)
    frames.append(frame)

  # Blank Frames
  blank_frame = sub_rosa_base_image.copy()
  frames = frames + [blank_frame] * 10

  # Draw Zero
  for n in range(0, 13):
    frame = blank_frame.copy()
    draw_frame = Image.open(f"./images/templates/shared/warning_signs/draw/{'{:02d}'.format(n)}.png").convert('RGBA')
    frame.paste(draw_frame, (110, 85), draw_frame)
    frames.append(frame)

    if n == 12:
      frames = frames + [frame] * 30

  # Save
  image_filename = "days_since_last_sub_rosa_watch.gif"
  image_filepath = f"./images/sub_rosa/{image_filename}"
  if os.path.exists(image_filepath):
    os.remove(image_filepath)

  frames[0].save(
    image_filepath,
    save_all=True, append_images=frames[1:], optimize=False, duration=40, loop=0
  )

  while True:
    time.sleep(0.05)
    if os.path.isfile(image_filepath):
      break

  discord_image = discord.File(fp=image_filepath, filename=image_filename)
  return discord_image


def get_random_footer_text():
  footer_texts = [
    "Most people on this colony will remember my grandmother as a healer, \nbut her abilities went beyond that.",
    "Beverly! It's all right! Have trust in me!",
    "THIRTIES!?",
    "Dinnae light that canhdle! An dunnoe go to that hoose!",
    "It's supposed to symbolise the enduring Howard spirit. \nWherever they may go, the shining light to guide them through their fortune!",
    "That's one hell of a thunderstorm...",
    "A pair of hands. They were moving across my skin...",
    "I did fall asleep reading a particularly erotic chapter \nin my grandmother's journal...",
    "I wonder if I'll have another dream tonight...",
    "I'd read two chapters!",
    "You dinna understand. He's trying to kill us all!",
    "Then we'll be together, uhllwayyyhhhzz...",
    "I was about to be initiated into a very unusual relationship. \nYou might call it a family tradition."
  ]
  return f"{random.choice(footer_texts)} 🕯️"

async def db_reset_days(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "INSERT INTO sub_rosa (user_discord_id, time_created) VALUES (%s, NOW());"
    vals = (user_discord_id,)
    await query.execute(sql, vals)

async def db_get_previous_reset():
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM sub_rosa ORDER BY id DESC LIMIT 1;"
    await query.execute(sql)
    previous_reset = await query.fetchone()
  return previous_reset

async def db_get_longest_reset():
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT
        sr.id,
        sr.user_discord_id,
        sr.time_created,
        TIMESTAMPDIFF(SECOND, sr.time_created, sr.next_time_created) AS duration
      FROM (
        SELECT
          id,
          user_discord_id,
          time_created,
          LEAD(time_created) OVER (ORDER BY time_created ASC) AS next_time_created
        FROM sub_rosa
      ) AS sr
      WHERE sr.next_time_created IS NOT NULL
      ORDER BY duration DESC
      LIMIT 1;
    '''
    await query.execute(sql)
    longest_reset = await query.fetchone()
  return longest_reset

async def db_get_sub_rosa_stats():
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT
        AVG(TIMESTAMPDIFF(DAY, time_created, next_time_created)) AS average_days,
        COUNT(*) AS total_watches
      FROM (
        SELECT
          time_created,
          LEAD(time_created) OVER (ORDER BY time_created ASC) AS next_time_created
        FROM sub_rosa
      ) AS time_differences
      WHERE next_time_created IS NOT NULL;
    '''
    await query.execute(sql)
    stats = await query.fetchone()
  return stats
