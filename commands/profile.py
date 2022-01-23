from .common import *

# profile() - Entrypoint for !profile command
# message[required]: discord.Message
# This function is the main entrypoint of the !profile command
# and will return a user's profile card
# Some magic I don't understand...
async def profile(message:discord.Message):
  user = message.author
  channel = message.channel
  player = get_player(user.id)
  template_image = "template.png"
  badge_image = None
  if player["profile_card"] != None:
    template_image = "template_{}.png".format(player["profile_card"].replace(" ", "_"))
  if player["profile_badge"] != None:
    badge_image = "./images/profiles/badges/{}".format(player["profile_badge"])
  image = Image.open(f"./images/profiles/{template_image}", "r")
  image = image.convert("RGBA")
  image_data = np.array(image)
  # replace white with profile color
  red, green, blue = image_data[:,:,0], image_data[:,:,1], image_data[:,:,2]
  r1, g1, b1 = 255,255,255
  r2, g2, b2 = user.color.to_rgb()
  mask = (red == r1) & (green == g1) & (blue == b1)
  image_data[:,:,:3][mask] = [r2, g2, b2]
  top_role = user.top_role
  image = Image.fromarray(image_data)
  image = image.convert("RGBA")
  user_name = f"{user.display_name}"
  user_name_encode = user_name.encode("ascii", errors="ignore")
  user_name = user_name_encode.decode().strip()
  top_role_name = top_role.name.encode("ascii", errors="ignore")
  top_role = top_role_name.decode().strip()
  user_join = user.joined_at.strftime("%Y.%m.%d")
  score = "SCORE: {}".format(player["score"])
  avatar = user.avatar_url_as(format='jpg', size=128)
  await avatar.save("./images/profiles/"+str(user.id)+"_a.jpg")
  name_font = ImageFont.truetype("images/lcars3.ttf", 56)
  rank_font = ImageFont.truetype("images/lcars3.ttf", 26)
  spins_font = ImageFont.truetype("images/lcars3.ttf", 20)
  rank_value_font = ImageFont.truetype("images/lcars3.ttf", 28)
  spins_value_font = ImageFont.truetype("images/lcars3.ttf", 24)
  avatar_image = Image.open("./images/profiles/"+str(user.id)+"_a.jpg")
  avatar_image.resize((128,128))
  image.paste(avatar_image, (12, 142))
  if badge_image:
    badge_template = Image.new("RGBA", (600,400))
    badge = Image.open(badge_image)
    badge = badge.convert("RGBA")
    badge = badge.resize((50,50))
    badge_template.paste(badge, (542, 341))
    image = Image.alpha_composite(image, badge_template)
  if player["high_roller"] == 1:
    vip_template = Image.new("RGBA", (600, 400))
    vip_badge = Image.open("./images/profiles/badges/ferengi.png")
    vip_badge = vip_badge.resize((64,64))
    vip_template.paste(vip_badge, (56, 327))
    image = Image.alpha_composite(image, vip_template)
  draw = ImageDraw.Draw(image)
  draw.line([(0, 0), (600, 0)], fill=(r2,g2,b2), width=5)
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
  image.save("./images/profiles/"+str(user.id)+".png")
  discord_image = discord.File("./images/profiles/"+str(user.id)+".png")
  await channel.send(file=discord_image)
  