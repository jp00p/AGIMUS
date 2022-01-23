from .common import *

# buy() - Entrypoint for !buy command
# message[required]: discord.Message
# This function is the main entrypoint of the !buy command
# and will allow a user to buy profiles, badges and roles
async def buy(message:discord.Message):
  f = open(config["commands"]["buy"]["data"])
  buy_data = json.load(f)
  f.close()
  usage = "Usage: `!buy [badge|profile|role] [##]`\nFor options, see `!shop badges`, `!shop profiles` or `!shop roles`"
  buy_string = message.content.lower().replace("!buy ", "").split()
  if len(buy_string) < 2:
    await message.channel.send(usage)
  else:
    item_cat = buy_string[0]
    item_to_buy = buy_string[1]
    if type(item_to_buy) == int:
      items = None
      msg = ""
      if item_cat not in ["badge", "profile", "role"]:
        msg = usage
      else:
        if item_cat == "badge":
          items = buy_data["badges"]
          cost = 100
        if item_cat == "profile":
          items = buy_data["cards"]
          cost = 25
        if item_cat == "role":
          items = buy_data["roles"]
          roles = list(buy_data["roles"])
          cost = buy_data["roles"][roles[int(item_to_buy)-1]]["price"] # uh oh...
        player = get_player(message.author.id)
        if player["score"] < cost:
          msg = "{}: You need `{} points` to buy that item!".format(message.author.mention, cost)
        else:
          if item_to_buy.isnumeric():
            if int(item_to_buy) <= len(items):
              item = int(item_to_buy) - 1
              if item_cat == "badge":
                badges = list(buy_data["badges"])
                final_item = buy_data["badges"][badges[item]]
                update_player_profile_badge(message.author.id, final_item)
                msg = "{}: You have spent `{} points` and purchased the **{}** profile badge! Type `!profile` to show it off!".format(message.author.mention, cost, badges[item])
              if item_cat == "profile":
                update_player_profile_card(message.author.id, items[item].lower())
                msg = "{}: You have spent `{} points` and purchased the **{}** profile card! Type `!profile` to show it off!".format(message.author.mention, cost, items[item])
              if item_cat == "role":
                roles = list(buy_data["roles"])
                final_item = buy_data["roles"][roles[item]]["id"]
                await update_player_role(message.author, final_item, buy_data["roles"]["High Roller"]["id"])
                msg = "{}: You have spent `{} points` and purchased the **{}** role!  You should see the role immediately, but you may need to refresh Discord to see it fully!".format(message.author.mention, cost, roles[item])
              set_player_score(message.author, -cost)
              increase_jackpot(cost)
            else:
              msg = usage
          else:
            msg = usage
    else:
      msg = usage
    await message.channel.send(msg)


# update_player_role(user, role)
# user[required]: object
# rolep[required]: string
# This function will add a discord role to a specific user
async def update_player_role(user, role, crew_role):
  # add crew role
  if role == crew_role:
    add_high_roller(user.id)
  role = discord.utils.get(user.guild.roles, id=role)
  if role not in user.roles:
    await user.add_roles(role)


# add_high_roller(discord_id)
# discord_id[required]: int
# This function will set a specific user's high_roller
# value to '1' by discord user id
def add_high_roller(discord_id):
  db = getDB()
  query = db.cursor()
  sql = "UPDATE users SET high_roller = 1 WHERE discord_id = %s"
  vals = (discord_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()
  