import time
import plotly.graph_objects as go
from torchvision.transforms import functional as F

from common import *
from utils.check_channel_access import access_check
from utils.thread_utils import to_thread

userinfo_group = bot.create_group("user_info", "User Information Commands (Top Channels, Etc)!")

@userinfo_group.command(
  name="top_channels",
  description="Get Info about the top channels you visit."
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
async def top_channels(ctx:discord.ApplicationContext, public:str):
  await ctx.defer(ephemeral=True)
  public = bool(public == "yes")

  user_discord_id = ctx.author.id

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

  # Set up labels/values for image
  labels = [f"#{channels[int(d['channel_id'])]}" for d in top_5_filtered_data]
  values = [d['total'] for d in top_5_filtered_data]

  other_sum = sum([d['total'] for d in filtered_data[5:]])
  labels.append(' Other')
  values.append(other_sum)

  filepath_and_filename = await generate_user_stats_top_channels_image(ctx, user_member, labels, values)

  discord_image = discord.File(filepath_and_filename[0], filename=filepath_and_filename[1])
  embed = discord.Embed(
    title="INFO - Top Channels",
    description=f"{user_member.mention}'s Top 5",
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
  embed.set_footer(text=f"{sum(values)} total messages analyzed over the past 90 days.")
  if public:
    await ctx.followup.send(embed=discord.Embed(title="Info Sent To Channel!", color=discord.Color.blurple()))
    await ctx.channel.send(embed=embed, file=discord_image)
  else:
    await ctx.followup.send(embed=embed, file=discord_image)

@to_thread
def generate_user_stats_top_channels_image(ctx, user_member, labels, values):
  user_discord_id = user_member.id
  user_name = user_member.display_name.encode("ascii", errors="ignore").decode().strip()

  fig_filename = f"fig-u{user_discord_id}-t{int(time.time())}.png"
  fig_filepath = f"./images/viz/figs/{fig_filename}"

  fig = go.Figure(data=[
    go.Pie(
      labels=labels,
      values=values,
      direction='clockwise',
      hole=.3,
      sort=False
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
  legend_title_font = ImageFont.truetype("fonts/lcars.ttf", 50)
  legend_text_font = ImageFont.truetype("fonts/lcars2.ttf", 26)

  base_width = 700
  base_height = 500

  base_image = Image.new("RGB", (base_width, base_height), (200, 200, 200))
  base_bg_image = Image.open("./images/templates/viz/viz_base_image.jpg")

  size = ((400, 400))
  f_raw = Image.open(fig_filepath).convert("RGBA")
  f_raw.thumbnail(size, Image.ANTIALIAS)
  fig_image = Image.new('RGBA', size, (27, 27, 27, 0))
  fig_image.paste(
    f_raw, (int((size[0] - f_raw.size[0]) // 2), int((size[1] - f_raw.size[1]) // 2)), f_raw
  )
  fig_image = F.center_crop(fig_image, (300, 300))

  base_image.paste(base_bg_image, (0, 0))
  base_image.paste(fig_image, (74, 158))

  # add users avatar to report
  avatar_image = Image.open(f"./images/profiles/{user_discord_id}_a.png")
  avatar_image = avatar_image.convert("RGBA")
  avatar_image = avatar_image.resize((64,64))
  avatar_image = ImageOps.expand(avatar_image, border=4, fill='#FF0000')
  # base_image.paste(avatar_image, (555, 120))
  base_image.paste(avatar_image, (70, 10))

  draw = ImageDraw.Draw(base_image)
  draw.text( (150, 75), "INFO -", fill="#FF0000", font=title_font, anchor="ls", align="left")
  draw.text( (290, 68), user_name, fill="#FF0000", font=title_username_font, anchor="ls", align="left")
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

def db_get_top_channels(user_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT channel_id, count(*) AS 'total'
        FROM xp_history
        WHERE user_discord_id = %s 
          AND reason = 'posted_message' 

        GROUP BY channel_id
        ORDER BY total DESC;
    '''
#          AND time_created >= DATE_SUB(NOW(), INTERVAL 90 day)
    vals = (user_discord_id,)
    query.execute(sql, vals)
    rows = query.fetchall()
  return rows