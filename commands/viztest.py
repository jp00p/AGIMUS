import time
import plotly.graph_objects as go
from torchvision.transforms import functional as F

from common import *
from utils.check_channel_access import access_check
from utils.thread_utils import to_thread

@bot.slash_command(
  name="viztest",
  description="Testing, Testing"
)
@commands.check(access_check)
async def viztest(ctx:discord.ApplicationContext):
  await ctx.defer(ephemeral=True)

  user_discord_id = ctx.author.id

  # Presave User's Avatar if needed
  user_member = await bot.current_guild.fetch_member(user_discord_id)
  avatar = user_member.display_avatar.with_size(128)
  await avatar.save(f"./images/profiles/{user_discord_id}_a.png")

  filepath_and_filename = await generate_user_stats_viz_image(ctx, user_member)

  discord_image = discord.File(filepath_and_filename[0], filename=filepath_and_filename[1])
  embed = discord.Embed(color=discord.Color.red())
  embed.set_image(url=f"attachment://{discord_image.filename}")
  await ctx.followup.send(embed=embed, file=discord_image)

@to_thread
def generate_user_stats_viz_image(ctx, user_member):
  user_discord_id = user_member.id

  d = {
    'ten-forward': 1000,
    'temba-his-arms-wide': 385,
    'animal-holophotography': 130,
    'general-trek': 939,
    'replimat': 399
  }

  sorted_data = sorted(d.items(), key=lambda x:x[1], reverse=True)
  labels = [t[0] for t in sorted_data]
  values = [t[1] for t in sorted_data]

  logger.info(f"labels: {labels}")
  logger.info(f"values: {values}")

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
      colors=['#FF0000', '#B14110', '#FFFFFF', '#878787', '#333333'],
      line=dict(color='#000000', width=2)
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
  legend_title_font = ImageFont.truetype("fonts/lcars.ttf", 50)
  legend_text_font = ImageFont.truetype("fonts/lcars.ttf", 26)

  base_width = 700
  base_height = 500

  base_image = Image.new("RGB", (base_width, base_height), (200, 200, 200))
  base_bg_image = Image.open("./images/templates/viz/viz_base_image.jpg")

  size = ((400, 400))
  f_raw = Image.open(fig_filepath).convert("RGBA")
  f_raw.thumbnail(size, Image.ANTIALIAS)
  fig_image = Image.new('RGBA', size, (22, 22, 22, 0))
  fig_image.paste(
    f_raw, (int((size[0] - f_raw.size[0]) // 2), int((size[1] - f_raw.size[1]) // 2)), f_raw
  )
  fig_image = F.center_crop(fig_image, (300, 300))

  base_image.paste(base_bg_image, (0, 0))
  base_image.paste(fig_image, (80, 160))

  # add users avatar to report
  avatar_image = Image.open(f"./images/profiles/{user_discord_id}_a.png")
  avatar_image = avatar_image.convert("RGBA")
  avatar_image = avatar_image.resize((64,64))
  avatar_image = ImageOps.expand(avatar_image, border=4, fill='#FF0000')
  base_image.paste(avatar_image, (555, 120))

  draw = ImageDraw.Draw(base_image)
  draw.text( (70, 70), f"STATS - {ctx.author.display_name}", fill="#FF0000", font=title_font, anchor="ls", align="left")
  draw.text( (390, 190), f"Top Channels", fill="#FFFFFF", font=legend_title_font, anchor="ls", align="left")

  current_y = 230
  for label_text in labels:
    draw.text( (415, current_y), f"# {label_text}", fill="#FFFFFF", font=legend_text_font, anchor="ls", align="left")
    current_y = current_y + 45


  base_filename = f"base-u{ctx.author.id}-t{int(time.time())}.png"
  base_filepath = f"./images/viz/{fig_filename}"

  base_image.save(base_filepath)

  while True:
    time.sleep(0.05)
    if os.path.isfile(base_filepath):
      break

  return (base_filepath, base_filename)