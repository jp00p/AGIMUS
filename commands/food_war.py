import time

from common import *
from utils.check_channel_access import access_check


# Create drop Slash Command Group
food_war = bot.create_group("food_war", "FoD Food War Commands!")

@food_war.command(
  name="reset",
  description="Reset the days since last FoD Food War",
)
@commands.check(access_check)
async def reset(ctx:discord.ApplicationContext):
  await ctx.defer(ephemeral=True)

  gif = await generate_food_war_reset_gif(365)
  await ctx.respond(
    embed=discord.Embed(
      color=discord.Color.dark_purple()
    ).set_image(url=f"attachment://{gif.filename}"),
    file=gif
  )


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

  frames = []

  # Fade out Current Days
  for n in range(1, 21):
    frame_b = food_war_base_image.copy()
    frame_txt = Image.new('RGBA', frame_b.size, (255,255,255,0))

    decreasing_opacity_value = round((100 - (n / 20 * 100)) * 2.55)

    d = ImageDraw.Draw(frame_txt)
    d.text( (base_width/2, 200), f"{days}", fill=(0, 0, 0, decreasing_opacity_value), font=marker_font, anchor="mm", align="center")

    frame = Image.alpha_composite(frame_b, frame_txt)
    frames.append(frame)

    if n == 1:
      frames = frames + [frame]*20
    elif n == 20:
      frames = frames + [frame]*5

  # Fade in 'Zero' Days
  for n in range(1, 21):
    frame_b = food_war_base_image.copy()
    frame_txt = Image.new('RGBA', frame_b.size, (255,255,255,0))

    increasing_opacity_value = round((n / 20 * 100) * 2.55)

    d = ImageDraw.Draw(frame_txt)
    d.text( (base_width/2, 200), "0", fill=(0, 0, 0, increasing_opacity_value), font=marker_font, anchor="mm", align="center")

    frame = Image.alpha_composite(frame_b, frame_txt)
    frames.append(frame)

    if n == 20:
      frames = frames + [frame]*40

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