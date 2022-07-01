from .common import *
from utils.check_channel_access import *

# profile() - Entrypoint for /profile command
# This function is the main entrypoint of the /profile command
# and will return a user's profile card

@slash.slash(
  name="profile",
  description="Show your own profile card",
  guild_ids=config["guild_ids"]
)

async def profile(ctx:SlashContext):
  
  user = ctx.author
  player = get_user(user.id)

  # fonts (same font, different sizes) used for building image
  name_font = ImageFont.truetype("images/lcars3.ttf", 56)
  rank_font = ImageFont.truetype("images/lcars3.ttf", 26)
  spins_font = ImageFont.truetype("images/lcars3.ttf", 20)
  rank_value_font = ImageFont.truetype("images/lcars3.ttf", 28)
  spins_value_font = ImageFont.truetype("images/lcars3.ttf", 24)
  
  template_image = "template.png" # base template image
  badge_image = None # little badge in the corner

  if player["profile_card"] != None:
    # do they have a different template base?
    template_image = "template_{}.png".format(player["profile_card"].replace(" ", "_"))

  if player["profile_badge"] != None:
    # get the profile badge image
    badge_image = "./images/profiles/badges/{}".format(player["profile_badge"])

  # open template file
  image = Image.open(f"./images/profiles/{template_image}", "r")
  image = image.convert("RGBA")
  image_data = np.array(image) # load image data into bytes array

  # replace white in the base template with the user's color
  red, green, blue = image_data[:,:,0], image_data[:,:,1], image_data[:,:,2]
  r1, g1, b1 = 255,255,255
  r2, g2, b2 = user.color.to_rgb()
  mask = (red == r1) & (green == g1) & (blue == b1)
  image_data[:,:,:3][mask] = [r2, g2, b2]

  # now we have the base template with colors replaced ready to go
  image = Image.fromarray(image_data)
  image = image.convert("RGBA")
  
  # grab user name and clean up special chars
  user_name = f"{user.display_name}"
  user_name_encode = user_name.encode("ascii", errors="ignore")
  user_name = user_name_encode.decode().strip()
  
  # grab user's top role and clean up special chars
  top_role = user.top_role
  top_role_name = top_role.name.encode("ascii", errors="ignore")
  top_role = top_role_name.decode().strip()
  
  # grab other user data
  user_join = user.joined_at.strftime("%Y.%m.%d")
  score = "SCORE: {}".format(player["score"])
  
  # grab user's avatar and paste it on the template
  avatar = user.avatar_url_as(format='jpg', size=128)
  await avatar.save("./images/profiles/"+str(user.id)+"_a.jpg") 
  avatar_image = Image.open("./images/profiles/"+str(user.id)+"_a.jpg")
  avatar_image.resize((128,128))
  image.paste(avatar_image, (12, 142))

  # if they have a badge image, paste it on the template
  if badge_image:
    badge_template = Image.new("RGBA", (600,400))
    badge = Image.open(badge_image)
    badge = badge.convert("RGBA")
    badge = badge.resize((50,50))
    badge_template.paste(badge, (542, 341))
    image = Image.alpha_composite(image, badge_template)

  # if they are a high roller, paste the special high roller badge on the template
  # probably should remove this
  if player["high_roller"] == 1:
    vip_template = Image.new("RGBA", (600, 400))
    vip_badge = Image.open("./images/profiles/badges/ferengi.png")
    vip_badge = vip_badge.resize((64,64))
    vip_template.paste(vip_badge, (56, 327))
    image = Image.alpha_composite(image, vip_template)
  
  # lots of text drawing
  draw = ImageDraw.Draw(image)
  draw.line([(0, 0), (600, 0)], fill=(r2,g2,b2), width=5) # and a fun line across the top why not
  draw.text( (546, 15), user_name[0:15], fill="white", font=name_font, anchor="rt", align="right")
  draw.text( (62, 83), "RANK", fill="black", font=rank_font, align="right", anchor="rt")
  draw.text( (77, 83), top_role, fill="white", font=rank_value_font, anchor="lt", align="left")
  draw.text( (62, 114), "JOINED", fill="black", font=rank_font, align="right", anchor="rt")
  draw.text( (77, 113), user_join, fill="white", font=rank_value_font, anchor="lt", align="left")
  draw.text( (65, 278), "SPINS", fill="black", font=spins_font, align="right", anchor="rt")
  draw.text( (73, 276), str(player["spins"]), fill="white", font=spins_value_font, anchor="lt", align="left")
  draw.text( (65, 304), "JACKPOTS", fill="black", font=spins_font, align="right", anchor="rt")
  draw.text( (73, 302), str(player["jackpots"]), fill="white", font=spins_value_font, anchor="lt", align="left")
  draw.text( (321, 366), score, fill="white", font=rank_value_font)
  
  # finalize image
  image.save("./images/profiles/"+str(user.id)+".png")
  discord_image = discord.File("./images/profiles/"+str(user.id)+".png")
  await ctx.reply(file=discord_image, hidden=True)