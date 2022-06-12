from .common import *

# jackpot() - Entrypoint for !jackpot command
# message[required]: discord.Message
# This function is the main entrypoint of the !jackpot command
# and sends the current jackpot bounty value
async def jackpot(message:discord.Message):
  await message.channel.send("Current jackpot bounty is: {0}".format(get_jackpot()))


# jackpots() - Entrypoint for !jackpots command
# message[required]: discord.Message
# This function is the main entrypoint of the !jackpots command
# and sends the current jackpots bounty value
async def jackpots(message:discord.Message):
    jackpots = get_all_jackpots()
    table = []
    table.append(["JACKPOT VALUE", "WINNER", "LIFESPAN", "DATE WON"])
    for jackpot in jackpots:
      lifespan = jackpot["time_won"] - jackpot["time_created"]
      lifespan_str = "{}d {}h {}m".format(lifespan.days, lifespan.seconds//3600, (lifespan.seconds//60)%60)
      table.append([jackpot["jackpot_value"], jackpot["winner"], lifespan_str, jackpot["time_won"].strftime("%x %X")])
    msg = "Last 10 jackpots:\n```"
    msg += tabulate(table, headers="firstrow")
    msg += "```"
    await message.channel.send(msg)


# get_jackpot(config)
# This function takes no arguments
# and returns the most recent jackpot_value from the jackpots table
def get_jackpot():
  # get the current jackpot
  db = getDB()
  query = db.cursor()
  sql = "SELECT jackpot_value FROM jackpots ORDER BY id DESC LIMIT 1"
  query.execute(sql)
  jackpot_amt = query.fetchone()
  db.commit()
  query.close()
  db.close()
  return jackpot_amt[0]


# get_all_jackpots(config)
# This function takes no arguments
# and returns the 10 most recent jackpot_value from the jackpots table
def get_all_jackpots():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM jackpots WHERE winner IS NOT NULL ORDER BY id DESC LIMIT 10"
  query.execute(sql)
  jackpot_data = query.fetchall()
  query.close()
  db.close()
  return jackpot_data

