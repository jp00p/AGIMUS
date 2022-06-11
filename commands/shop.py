from .common import *

# shop() - Entrypoint for !shop command
# message[required]: discord.Message
# This function is the main entrypoint of the !shop command
# and will allow a user to view possible profiles, badges and roles to buy with buy command
async def shop(message:discord.Message):
  f = open(config["commands"]["shop"]["data"])
  shop_data = json.load(f)
  f.close()
  if message.content.lower() == "!shop":
    msg = "Please use `!shop profiles` or `!shop badges` or `!shop roles`"
    await message.channel.send(msg)
  if message.content.lower().startswith("!shop roles"):
    msg = "__**Role Shop:**__\n COMMANDERS TAKE NOTE: You will be able to buy these roles, but any vanity effects will not apply to you. Sorry!\n\n"
    c = 1
    for i in shop_data["roles"]:
      msg += "`{}` - Role: *{}* - Price: `{}` points\n".format(c, i, shop_data["roles"][i]["price"])
    msg += "\nAll proceeds go to directly to the jackpot. Type `!buy role` follow by the item number to purchase a role"
    await message.channel.send(msg)
  if message.content.lower().startswith("!shop profiles"):
    msg = "__**Profile Shop:**__\n"
    c = 1
    for i in shop_data["cards"]:
      msg += "`{}`. *{}*\n".format(c, i)
      c += 1
    msg += "\n`25 points` each. All proceeds go directly to the jackpot\nType `!buy profile` followed by the item number to buy a profile card"
    await message.channel.send(msg)
  if message.content.lower().startswith("!shop badges"):
    msg = "__**Badge Shop**__\n"
    c = 1
    for i in shop_data["badges"]:
      msg += "`{}` - Badge: *{}*\n".format(c, i)
      c += 1
    msg += "\n`100 points` each. All proceeds go directly to the jackpot\nType `!buy badge` followed by the item number to buy a badge"
    await message.channel.send(msg)