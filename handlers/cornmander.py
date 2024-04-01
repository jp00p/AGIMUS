from datetime import date as d
from common import *

async def handle_cornmander(message:discord.Message):
  # This is only active on April Fools Day...
  today = d.today()
  if today.month != 4 or today.day != 1:
    return

  cornmander_role = discord.utils.get(message.guild.roles, name="Cornmander ●●●")
  lower_decks_role = discord.utils.get(message.guild.roles, name="Lower Decks ○")
  if cornmander_role is None or lower_decks_role is None:
    return
  lower_decks_channel_id = get_channel_id('deck-11-bunk-corridor')
  lower_decks_channel = await bot.fetch_channel(lower_decks_channel_id)

  message_is_corny = False
  message_content = message.content.lower().replace(' ', '')
  if '🌽' in message_content or '🍿' in message_content:
    message_is_corny = True

  message_content = re.sub(r'[^\w\s]', '', message_content)
  if re.search(r'(c|с|ƈ|ċ|k|k)+(o|0|о|ο|օ|ȯ|ọ|ỏ|ơ|ó|ò|ö)+r+(n|ո)+', message_content, re.IGNORECASE):
    message_is_corny = True

  if message_is_corny:
    logger.info(f"{Style.BRIGHT}{message.author.display_name}{Style.RESET_ALL} posted a 🌽-y message! We shall take action!")

  allowed_roles = ["Admiral", "Captain"]
  allowed_role_ids = get_role_ids_list(allowed_roles)
  user_role_ids = [r.id for r in message.author.roles]
  corny_allowed = any(user_rid in allowed_role_ids for user_rid in user_role_ids)

  cornmander_status = db_get_cornmander_status(message.author.id)
  if cornmander_status == 'unpipped':
    if message_is_corny and not corny_allowed:
      # Hush them up if they said the secret word right off the bat
      await message.delete()

    try:
      # We don't notify the user, we just semi-secretly Pip them
      await message.author.add_roles(cornmander_role, reason="Pipping with a Piece Of Corn!")
      db_pip_cornmander_status(message.author.id)
    except Exception as e:
      logger.info(f"Unable to boost {message.author.display_name} to Cornmander role.")
      pass
  elif cornmander_status == 'pipped':
    if message_is_corny and not corny_allowed:
      # Strip Em if they said the forbidden word
      db_strip_cornmander_status(message.author.id)
      await message.author.remove_roles(cornmander_role, reason="They said the forbidden word! Piece Of Corn removed!")
      await message.author.add_roles(lower_decks_role, reason="LOWER DECKS! LOWER DECKS!")
      # SILENCE THEM!
      await message.delete()
      # Then notify!
      try:
        strip_pip_embed = discord.Embed(
          title="Whoops, that Pip was just a Piece of Corn! 🌽",
          description="You said the forbidden word: *Corn!* **April Fools!!!**\n\n"
                      "Sadly this means your Corn-mander role has been revoked.\n\n"
                      f"However, you ***have*** been granted a *secret* role, 'Lower Decks', and can now talk freely in the {lower_decks_channel.mention} channel.\n\n"
                      "To keep the prank going, please don't *publicly* explain the details to others!\n\n🤫",
          color=discord.Color.gold()
        )
        strip_pip_embed.set_footer(text="Thank you for being a valued member of The Hood! We ❤️ you!")
        strip_pip_embed.set_image(url="https://i.imgur.com/Sw8TC4R.gif")
        await message.author.send(embed=strip_pip_embed)
      except discord.Forbidden as e:
        logger.info(f"Unable to send Cornmander stripping message to {message.author.display_name}, they have their DMs closed.")
        pass
  elif cornmander_status == 'depipped':
    if message_is_corny and not corny_allowed:
      if message.channel.id is not lower_decks_channel_id:
        # They can only talk about the secret word in the Lower Decks Channel, so delete em if outside
        await message.delete()


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