import time
import pytz

from common import *
from utils.check_channel_access import access_check


# Create drop Slash Command Group
food_war = bot.create_group("food_war", "FoD Food War Commands!")

@food_war.command(
  name="reset",
  description="Reset the days since last FoD Food War",
)
@option(
  name="reason",
  description="Reason for reset?",
  required=True,
  min_length=1,
  max_length=64
)
@commands.check(access_check)
async def reset(ctx:discord.ApplicationContext, reason:str):
  await ctx.defer()

  previous_reset = await db_get_previous_reset()
  stats = await db_get_food_war_stats()

  embed = discord.Embed(
    title="Resetting Days Since Last FoD Food War...",
    description=f"{ctx.author.mention} is resetting the clock!",
    color=discord.Color.gold()
  )
  embed.add_field(
    name="Reason",
    value=reason,
    inline=False
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
      name=f"Previous Reason",
      value=previous_reset['reason'],
    )

    embed.add_field(
      name="Total Number of Food Wars",
      value=stats['total_wars'],
      inline=False
    )
    embed.add_field(
      name="Average Days Between Food Wars",
      value=int(stats['average_days']),
      inline=False
    )
  else:
    days = 0

  await db_reset_days(ctx.author.id, reason, days)

  gif = await generate_food_war_reset_gif(days)
  embed.set_image(url=f"attachment://{gif.filename}")
  embed.set_footer(text="Again!? 💣")
  await ctx.followup.send(embed=embed, file=gif)


@food_war.command(
  name="check",
  description="Check how many days it's been since last FoD Food War",
)
@commands.check(access_check)
async def check(ctx:discord.ApplicationContext):
  previous_reset = await db_get_previous_reset()

  if not previous_reset:
    await ctx.respond(
      embed=discord.Embed(
        title="No Wars Registered Yet!",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  await ctx.defer()
  stats = await db_get_food_war_stats()

  pst_tz = pytz.timezone('America/Los_Angeles')
  raw_now = datetime.utcnow().replace(tzinfo=pytz.utc)
  raw_time_created = pytz.utc.localize(previous_reset['time_created'])
  aware_now = pst_tz.normalize(raw_now.astimezone(pst_tz))
  aware_time_created = pst_tz.normalize(raw_time_created.astimezone(pst_tz))

  lifespan = aware_now - aware_time_created
  days = lifespan.days

  embed = discord.Embed(
    title=f"The Last FoD Food War...",
    description=f"was {days} {'Day' if days == 1 else 'Days'} ago...",
    color=discord.Color.gold()
  )

  embed.add_field(
    name="Previous Days Streak",
    value=f"{previous_reset['days']} {'Day' if previous_reset['days'] == 1 else 'Days'}",
  )
  embed.add_field(
    name="Previous Reason",
    value=previous_reset['reason'],
  )

  longest_reset = await db_get_longest_reset()
  if previous_reset['id'] == longest_reset['id']:
    embed.add_field(
      name="All-Time Longest Streak Was The Previous!",
      value="Holy Guacamole! 🥑",
      inline=False
    )
  else:
    embed.add_field(
      name="All-Time Longest Streak",
      value=f"{longest_reset['days']} {'Day' if longest_reset['days'] == 1 else 'Days'}",
      inline=False
    )
    embed.add_field(
      name="All-Time Longest Streak Reason",
      value=longest_reset['reason'],
      inline=False
    )

  embed.add_field(
    name="Total Number of Food Wars",
    value=stats['total_wars'],
    inline=False
  )
  embed.add_field(
    name="Average Days Between Food Wars",
    value=int(stats['average_days']),
    inline=False
  )

  png = await generate_food_war_check_png(days)
  embed.set_image(url=f"attachment://{png.filename}")
  embed.set_footer(text="We can only hope it shall last longer... 🥑 ⚔️ 🙏")
  await ctx.followup.send(embed=embed, file=png)


@to_thread
def generate_food_war_check_png(days):
  marker_font = ImageFont.truetype("fonts/PermanentMarker.ttf", 200)

  base_width = 600
  base_height = 775

  food_war_sign_image = Image.open("./images/templates/food_war/blank_sign.png").convert("RGBA")
  food_war_base_image = Image.new("RGBA", (base_width, base_height), (0, 0, 0))
  food_war_base_image.paste(food_war_sign_image, (0, 0))

  d = ImageDraw.Draw(food_war_base_image)
  d.text( (base_width/2, 200), f"{days}", fill=(0, 0, 0, 255), font=marker_font, anchor="mm", align="center")

  image_filename = "current_days.png"
  image_filepath = f"./images/food_war/{image_filename}"
  if os.path.exists(image_filepath):
    os.remove(image_filepath)

  food_war_base_image.save(image_filepath)

  while True:
    time.sleep(0.05)
    if os.path.isfile(image_filepath):
      break

  discord_image = discord.File(fp=image_filepath, filename=image_filename)
  return discord_image

@to_thread
def generate_food_war_reset_gif(days):
  marker_font = ImageFont.truetype("fonts/PermanentMarker.ttf", 200)

  base_width = 600
  base_height = 775

  food_war_sign_image = Image.open("./images/templates/food_war/blank_sign.png").convert("RGBA")
  food_war_base_image = Image.new("RGBA", (base_width, base_height), (0, 0, 0))
  food_war_base_image.paste(food_war_sign_image, (0, 0))

  base_text_frame = food_war_base_image.copy()
  d = ImageDraw.Draw(base_text_frame)
  d.text( (base_width/2, 200), f"{days}", fill=(0, 0, 0, 255), font=marker_font, anchor="mm", align="center")
  frames = [base_text_frame]*20

  # Eraser Wipe
  for n in range(0, 54):
    frame = base_text_frame.copy()
    wipe_frame = Image.open(f"./images/templates/shared/warning_signs/wipe/{'{:02d}'.format(n)}.png").convert('RGBA')
    frame.paste(wipe_frame, (110, 85), wipe_frame)
    frames.append(frame)

  # Blank Frames
  blank_frame = food_war_base_image.copy()
  frames = frames + [blank_frame]*10

  # Draw Zero
  for n in range(0, 13):
    frame = blank_frame.copy()
    draw_frame = Image.open(f"./images/templates/shared/warning_signs/draw/{'{:02d}'.format(n)}.png").convert('RGBA')
    frame.paste(draw_frame, (110, 85), draw_frame)
    frames.append(frame)

    if n == 12:
      frames = frames + [frame]*30

  # Save
  image_filename = "days_since_last_fod_food_war.gif"
  image_filepath = f"./images/food_war/{image_filename}"
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


async def db_get_previous_reset():
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM food_war ORDER BY id DESC LIMIT 1"
    await query.execute(sql)
    previous_reset = await query.fetchone()
  return previous_reset

async def db_reset_days(user_discord_id, reason, days):
  async with AgimusDB(dictionary=True) as query:
    sql = "INSERT INTO food_war (user_discord_id, reason, days) VALUES (%s, %s, %s)"
    vals = (user_discord_id, reason, days)
    await query.execute(sql, vals)

async def db_get_longest_reset():
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT fw.*
        FROM (select fw.*,
                (SELECT time_created
                  FROM food_war fw2
                  WHERE fw2.time_created > fw.time_created
                  ORDER BY time_created
                  LIMIT 1
                ) AS next_time_created
            FROM food_war fw
          ) fw
        ORDER BY timestampdiff(second, time_created, next_time_created) DESC
        LIMIT 1;
    '''
    await query.execute(sql)
    longest_reset = await query.fetchone()
  return longest_reset

async def db_get_food_war_stats():
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT
        AVG(TIMESTAMPDIFF(DAY, time_created, next_time_created)) AS average_days,
        COUNT(*) AS total_wars
      FROM (
        SELECT
          time_created,
          LEAD(time_created) OVER (ORDER BY time_created ASC) AS next_time_created
        FROM food_war
      ) AS time_differences
      WHERE next_time_created IS NOT NULL;
    '''
    await query.execute(sql)
    stats = await query.fetchone()
  return stats