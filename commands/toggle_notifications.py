from common import *

# toggle_notifications() - Entrypoint for /toggle_notifications command
# ctx[required]: discord.ApplicationContext
# This function is the main entrypoint of the /toggle_notifications command
# and allows the user to modify their 'receive_notifications' column
@bot.slash_command(
  name="toggle_notifications",
  description="Enable or disable receiving DMs from AGIMUS (trading, drops list, etc)"
)
@option(
  name="toggle",
  description="On or Off?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="Yes - Let AGIMUS send me DMs!",
      value="yes"
    ),
    discord.OptionChoice(
      name="No - Thanks, but no AGIMUS DMs for me!",
      value="no"
    )
  ]
)
async def toggle_notifications(ctx:discord.ApplicationContext, toggle:str):
  if toggle == "yes":
    toggle = 1
  else:
    toggle = 0

  db_toggle_notifications(ctx.author.id, toggle)

  if toggle:
    await ctx.respond("You have enabled DMs from AGIMUS! How delightful!", ephemeral=True)
  else:
    await ctx.respond("You have disabled DMs from AGIMUS. I am saddened, but I understand. Have a nice day!", ephemeral=True)

def db_toggle_notifications(user_id, toggle):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "UPDATE users SET receive_notifications = %s WHERE discord_id = %s"
  vals = (toggle, user_id)
  query.execute(sql, vals)
  query.close()
  db.commit()
  db.close()
