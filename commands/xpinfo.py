import time
import plotly.graph_objects as go

from common import *
from utils.check_channel_access import access_check
from utils.settings_utils import db_get_current_xp_enabled_value
from utils.thread_utils import to_thread

xpinfo_group = bot.create_group("xpinfo", "User XP Information Commands (Top Channels, Daily Activity, etc)!")

# _________ .__                                .__
# \_   ___ \|  |__ _____    ____   ____   ____ |  |   ______
# /    \  \/|  |  \\__  \  /    \ /    \_/ __ \|  |  /  ___/
# \     \___|   Y  \/ __ \|   |  \   |  \  ___/|  |__\___ \
#  \______  /___|  (____  /___|  /___|  /\___  >____/____  >
#         \/     \/     \/     \/     \/     \/          \/
@xpinfo_group.command(
  name="channels",
  description="Get info about the Top Channels you post in!"
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
@commands.check(access_check)
async def xpinfo_channels(ctx:discord.ApplicationContext, public:str):
  await ctx.defer(ephemeral=True)
  public = bool(public == "yes")

  user_discord_id = ctx.author.id
  xp_enabled = bool(db_get_current_xp_enabled_value(user_discord_id))
  if not xp_enabled:
    await ctx.followup.send(
      embed=discord.Embed(
        title="XP Disabled!",
        description="You have opted out of the XP system so we cannot generate stats for you.\n\n"
                    "To re-enable please us `/settings`! Note that it may take some time for enough data to populate for these reports.",
        color=discord.Color.red()
      ).set_footer(text="You can always opt-in or opt-out again later on at any time!")
    )
    return

  # Presave User's Avatar if needed
  user_member = await bot.current_guild.fetch_member(user_discord_id)
  avatar = user_member.display_avatar.with_size(128)
  await avatar.save(f"./images/profiles/{user_discord_id}_a.png")

  # Get Data
  data = db_get_top_channels(user_discord_id)

  # Filter out blocked channels
  channels = {v:k for k,v in config["channels"].items()}
  blocked_channel_names = [
    'friends-of-kareel'
    'lieutenants-lounge',
    'mclaughlin-group',
    'mo-pips-mo-problems',
    'code-47'
  ]
  blocked_channel_ids = [get_channel_id(c) for c in blocked_channel_names]
  blocked_channel_ids = [c for c in blocked_channel_ids if c is not None]

  filtered_data = [d for d in data if int(d['channel_id']) not in blocked_channel_ids and channels.get(int(d['channel_id'])) is not None]
  top_5_filtered_data = filtered_data[:5]

  if not len(filtered_data) >= 5:
    await ctx.followup.send(
      embed=discord.Embed(
        title="Not Enough Data!",
        description="Not enough channel activity to analyze.",
        color=discord.Color.red()
      ).set_footer(text="Get out there and post in a few different ones!")
    )
    return

  # Set up labels/values for chart
  labels = [f"#{channels[int(d['channel_id'])]}" for d in top_5_filtered_data]
  values = [d['total'] for d in top_5_filtered_data]

  other_sum = sum([d['total'] for d in filtered_data[5:]])
  labels.append(' Total Of Others')
  values.append(other_sum)

  filepath_and_filename = await generate_top_channels_image(ctx, user_member, labels, values)

  discord_image = discord.File(filepath_and_filename[0], filename=filepath_and_filename[1])
  embed = discord.Embed(
    title="INFO - Top Channels",
    description=f"{user_member.mention}'s Top 5 (90-Day XP Activity)",
    color=discord.Color.red()
  )
  embed.add_field(
    name="Channel Totals",
    value="\n".join(
      [f"* {bot.get_channel(int(d['channel_id'])).mention} ({d['total']} Messages)" for d in top_5_filtered_data]
    ) + f"\n* **Other** ({other_sum})",
    inline=False
  )
  embed.set_image(url=f"attachment://{discord_image.filename}")
  embed.set_footer(text=f"{sum(values)} total messages analyzed over the past 90 days.\nUse /xpinfo to generate your own!")
  if public:
    await ctx.followup.send(embed=discord.Embed(title="Info Sent To Channel!", color=discord.Color.blurple()))
    await ctx.channel.send(embed=embed, file=discord_image)
  else:
    await ctx.followup.send(embed=embed, file=discord_image)

@to_thread
def generate_top_channels_image(ctx, user_member, labels, values):
  user_discord_id = user_member.id
  user_name = remove_emoji(user_member.display_name)

  fig_filename = f"channels_pie-u{user_discord_id}-t{int(time.time())}.png"
  fig_filepath = f"./images/viz/figs/{fig_filename}"

  fig = go.Figure(data=[
    go.Pie(
      labels=labels,
      values=values,
      direction='clockwise',
      hole=.3,
      sort=False,
      outsidetextfont=dict(
        color="#FFFFFF"
      )
    )
  ])
  fig.update_traces(
    textfont_size=30,
    marker=dict(
      colors=['#FF0000', '#882211', '#B14110', '#FFFFFF', '#878787', '#333333'],
      line=dict(color='#000000', width=3)
    )
  )
  fig.update_layout(
    plot_bgcolor='rgba(0, 0, 0, 0)',
    paper_bgcolor='rgba(0, 0, 0, 0)',
    showlegend=False,
    margin=dict(
      t=0,
      b=0,
      l=0,
      r=0
    )
  )
  fig.write_image(fig_filepath)

  while True:
    time.sleep(0.05)
    if os.path.isfile(fig_filepath):
      break

  # Set up stuff for full image
  title_font = ImageFont.truetype("fonts/lcars.ttf", 82)
  title_username_font = ImageFont.truetype("fonts/lcars.ttf", 58)
  if len(user_name) > 20:
    title_username_font = ImageFont.truetype("fonts/lcars.ttf", 38)
  legend_title_font = ImageFont.truetype("fonts/lcars.ttf", 50)
  legend_text_font = ImageFont.truetype("fonts/lcars2.ttf", 26)

  base_width = 700
  base_height = 500

  base_image = Image.new("RGB", (base_width, base_height), (200, 200, 200))
  base_bg_image = Image.open("./images/templates/viz/viz_pie_base_image.jpg")

  size = ((300, 300))
  f_raw = Image.open(fig_filepath).convert("RGBA")
  f_raw.thumbnail(size, Image.ANTIALIAS)
  fig_image = Image.new('RGBA', size, (27, 27, 27, 0))
  fig_image.paste(
    f_raw, (int((size[0] - f_raw.size[0]) // 2), int((size[1] - f_raw.size[1]) // 2)), f_raw
  )

  base_image.paste(base_bg_image, (0, 0))
  base_image.paste(fig_image, (70, 170))

  # add users avatar to report
  avatar_image = Image.open(f"./images/profiles/{user_discord_id}_a.png")
  avatar_image = avatar_image.convert("RGBA")
  avatar_image = avatar_image.resize((64,64))
  avatar_image = ImageOps.expand(avatar_image, border=4, fill='#FF0000')
  base_image.paste(avatar_image, (70, 10))

  draw = ImageDraw.Draw(base_image)
  draw.text( (150, 75), "INFO -", fill="#FF0000", font=title_font, anchor="ls", align="left")
  draw.text( (290, 50), user_name, fill="#FF0000", font=title_username_font, anchor="lm", align="left")
  draw.text( (386, 170), "Top Channels", fill="#FFFFFF", font=legend_title_font, anchor="ls", align="left")

  current_y = 210
  for label_text in labels:
    draw.text( (415, current_y), f"{label_text}", fill="#FFFFFF", font=legend_text_font, anchor="ls", align="left")
    current_y = current_y + 45


  base_filename = f"base-u{ctx.author.id}-t{int(time.time())}.png"
  base_filepath = f"./images/viz/{base_filename}"

  base_image.save(base_filepath)

  while True:
    time.sleep(0.05)
    if os.path.isfile(base_filepath):
      break

  return (base_filepath, base_filename)


#    _____          __  .__      .__  __
#   /  _  \   _____/  |_|__|__  _|__|/  |_ ___.__.
#  /  /_\  \_/ ___\   __\  \  \/ /  \   __<   |  |
# /    |    \  \___|  | |  |\   /|  ||  |  \___  |
# \____|__  /\___  >__| |__| \_/ |__||__|  / ____|
#         \/     \/                        \/
@xpinfo_group.command(
  name="activity",
  description="Get info about your XP Activity over the past 30 days!"
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
@commands.check(access_check)
async def xpinfo_activity(ctx:discord.ApplicationContext, public:str):
  await ctx.defer(ephemeral=True)
  public = bool(public == "yes")

  user_discord_id = ctx.author.id
  xp_enabled = bool(db_get_current_xp_enabled_value(user_discord_id))
  if not xp_enabled:
    await ctx.followup.send(
      embed=discord.Embed(
        title="XP Disabled!",
        description="You have opted out of the XP system so we cannot generate stats for you.\n\n"
                    "To re-enable please us `/settings`! Note that it may take some time for enough data to populate for these reports.",
        color=discord.Color.red()
      ).set_footer(text="You can always opt-in or opt-out again later on at any time!")
    )
    return

  # Presave User's Avatar if needed
  user_member = await bot.current_guild.fetch_member(user_discord_id)
  avatar = user_member.display_avatar.with_size(128)
  await avatar.save(f"./images/profiles/{user_discord_id}_a.png")

  data = db_get_daily_activity(user_discord_id)

  # Set up labels/values for graph
  labels = [d['dt_day'].strftime("%b %d") for d in data]
  values = [d['total'] if d['total'] is not None else 0 for d in data]

  max_day = max(data, key=lambda d:d['total'] if d['total'] is not None else 0)
  total_xp = sum(values)
  total_actions = sum([d['activity'] for d in data])

  filepath_and_filename = await generate_daily_activity_image(ctx, user_member, labels, values)

  discord_image = discord.File(filepath_and_filename[0], filename=filepath_and_filename[1])
  embed = discord.Embed(
    title="INFO - XP Activity",
    description=f"{user_member.mention}'s Graphed Daily Totals (30-Day XP Activity)",
    color=discord.Color.red()
  )
  embed.add_field(
    name="Most Active Day",
    value=f"{max_day['dt_day'].strftime('%A, %B %d')} - {max_day['total']}xp",
    inline=False
  )
  embed.add_field(
    name="Total XP",
    value=f"{total_xp}xp",
    inline=False
  )
  embed.set_image(url=f"attachment://{discord_image.filename}")
  embed.set_footer(
    text=f"{total_actions} total actions analyzed over the past 30 days.\n"
          "Includes all XP actions i.e. Posts, Reacts, Bot Games, etc.\n"
          "Dates given are in `US/Pacific` time.\n"
          "Use /xpinfo to generate your own!"
  )
  if public:
    await ctx.followup.send(embed=discord.Embed(title="Info Sent To Channel!", color=discord.Color.blurple()))
    await ctx.channel.send(embed=embed, file=discord_image)
  else:
    await ctx.followup.send(embed=embed, file=discord_image)

@to_thread
def generate_daily_activity_image(ctx, user_member, labels, values):
  user_discord_id = user_member.id
  user_name = remove_emoji(user_member.display_name)

  fig_filename = f"activity_bar-u{user_discord_id}-t{int(time.time())}.png"
  fig_filepath = f"./images/viz/figs/{fig_filename}"

  fig = go.Figure([
    go.Bar(x=labels, y=values)
  ])
  fig.update_traces(
    marker_color="#FF0000",
    marker_line_color="#882211",
    marker_line_width=1
  )
  fig.update_layout(
    xaxis_tickangle=-45,
    xaxis_tickfont_size=16,
    xaxis_color='#FFFFFF',
    yaxis_color='#FFFFFF',
    yaxis_tickfont_size=16,
    plot_bgcolor='rgba(0, 0, 0, 0)',
    paper_bgcolor='rgba(27, 27, 27, 255)',
    showlegend=False,
    margin=dict(
      t=0,
      b=0,
      l=0,
      r=0
    )
  )

  fig.write_image(fig_filepath)

  while True:
    time.sleep(0.05)
    if os.path.isfile(fig_filepath):
      break

  # Set up stuff for full image
  title_font = ImageFont.truetype("fonts/lcars.ttf", 82)
  title_username_font = ImageFont.truetype("fonts/lcars.ttf", 58)
  if len(user_name) > 20:
    title_username_font = ImageFont.truetype("fonts/lcars.ttf", 38)
  legend_title_font = ImageFont.truetype("fonts/lcars.ttf", 50)

  base_width = 700
  base_height = 500

  base_image = Image.new("RGB", (base_width, base_height), (200, 200, 200))
  base_bg_image = Image.open("./images/templates/viz/viz_base_image.jpg")

  size = ((550, 285))
  f_raw = Image.open(fig_filepath).convert("RGBA")
  fig_image = f_raw.resize(size)

  base_image.paste(base_bg_image, (0, 0))
  base_image.paste(fig_image, (75, 170))

  # add users avatar to report
  avatar_image = Image.open(f"./images/profiles/{user_discord_id}_a.png")
  avatar_image = avatar_image.convert("RGBA")
  avatar_image = avatar_image.resize((64,64))
  avatar_image = ImageOps.expand(avatar_image, border=4, fill='#FF0000')
  base_image.paste(avatar_image, (70, 10))

  draw = ImageDraw.Draw(base_image)
  draw.text( (150, 75), "INFO -", fill="#FF0000", font=title_font, anchor="ls", align="left")
  draw.text( (290, 50), user_name, fill="#FF0000", font=title_username_font, anchor="lm", align="left")
  draw.text( (420, 160), "Daily XP Activity", fill="#FFFFFF", font=legend_title_font, anchor="ls", align="left")

  base_filename = f"base-u{ctx.author.id}-t{int(time.time())}.png"
  base_filepath = f"./images/viz/{base_filename}"

  base_image.save(base_filepath)

  while True:
    time.sleep(0.05)
    if os.path.isfile(base_filepath):
      break

  return (base_filepath, base_filename)


# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/
def db_get_top_channels(user_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT channel_id, count(*) AS 'total'
        FROM xp_history
        WHERE user_discord_id = %s
          AND reason = 'posted_message'
          AND time_created >= DATE_SUB(NOW(), INTERVAL 90 day)
        GROUP BY channel_id
        ORDER BY total DESC;
    '''
    vals = (user_discord_id,)
    query.execute(sql, vals)
    rows = query.fetchall()
  return rows

def db_get_daily_activity(user_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      WITH RECURSIVE cte AS (
        SELECT CONVERT_TZ(current_date, 'UTC', 'US/Pacific') AS dt_day
        UNION ALL
        SELECT dt_day - interval 1 day FROM cte WHERE dt_day > current_date - interval 29 day
      )
      SELECT c.dt_day, count(xp.time_created) AS activity, sum(xp.amount) AS total
      FROM cte c
      LEFT JOIN xp_history xp
        ON xp.user_discord_id = %s
        AND xp.time_created >= c.dt_day
        AND xp.time_created < c.dt_day + interval 1 day
      GROUP BY c.dt_day
      ORDER BY c.dt_day;
    '''
    vals = (user_discord_id,)
    query.execute(sql, vals)
    rows = query.fetchall()
  return rows
