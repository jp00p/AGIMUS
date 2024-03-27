from datetime import date as d
from common import *

async def handle_cornmander(message:discord.Message):
  # This is only active on April Fools Day...
  today = d.today()
  if today.month != 4 and today.day != 1:
    return

  cornmander_role = discord.utils.get(message.guild.roles, name="Cornmander ●●●")
  if cornmander_role is None:
    return

  cornmander_status = db_get_cornmander_status(message.author.id)
  if cornmander_status == 'depipped':
    return
  elif cornmander_status == 'unpipped':
    if 'corn' not in message.content.lower():
      # Pip Em if they're currently unpipped
      db_pip_cornmander_status(message.author.id)
      message.author.add_roles(cornmander_role, reason="Pipping with a Piece Of Corn!")
      # We don't notify the user, we just semi-secretly Pip them
  elif cornmander_status == 'pipped':
    if 'corn' in message.content.lower():
      # Strip Em if they said the forbidden word
      db_strip_cornmander_status(message.author.id)
      await message.author.remove_roles(cornmander_role, reason="They said the forbidden word! Piece Of Corn removed!")
      lower_decks_role = discord.utils.get(message.guild.roles, name="Lower Decks ○")
      if lower_decks_role:
        await message.author.add_roles(lower_decks_role, reason="LOWER DECKS! LOWER DECKS!")
      # Then notify!
      try:
        strip_pip_embed = discord.Embed(
          title="Whoops, that Pip was just a Piece of Corn! 🌽",
          description="You said the forbidden word: *Corn!* **April Fools!!!**\n\n"
                      "Sadly this means your Corn-mander role has been revoked.\n\n"
                      "However, you ***have*** been granted a *secret* role, 'Lower Decks', and can now talk freely in the 'Deck 11 Bunk Corridor' channel.\n\n"
                      "To keep the prank going, please don't *publicly* explain the details to others!\n\n🤫",
          color=discord.Color.gold()
        )
        strip_pip_embed.set_footer(text="Thank your for being a valued member of The Hood! We ❤️ you!")
        strip_pip_embed.set_image(url="https://i.imgur.com/Sw8TC4R.gif")
        await message.author.send(embed=strip_pip_embed)
      except discord.Forbidden as e:
        logger.info(f"Unable to send Cornmander stripping message to {message.author.display_name}, they have their DMs closed.")
        pass


def db_get_cornmander_status(user_id):
  with AgimusDB(dictionary=True) as query:
    sql = "SELECT cornmander_status FROM april_fools WHERE user_discord_id = %s"
    vals = (user_id,)
    query.execute(sql, vals)
    result = query.fetchone()
    if result:
      return result['cornmander_status']
    else:
      sql = "INSERT INTO april_fools (user_discord_id, cornmander_status) values (%s, 'unpipped')"
      query.execute(sql, vals)
      return 'unpipped'

def db_pip_cornmander_status(user_id):
  with AgimusDB(dictionary=True) as query:
    sql = "UPDATE april_fools SET cornmander_status = 'pipped' WHERE user_discord_id = %s"
    vals = (user_id,)
    query.execute(sql, vals)

def db_strip_cornmander_status(user_id):
  with AgimusDB(dictionary=True) as query:
    sql = "UPDATE april_fools SET cornmander_status = 'depipped' WHERE user_discord_id = %s"
    vals = (user_id,)
    query.execute(sql, vals)