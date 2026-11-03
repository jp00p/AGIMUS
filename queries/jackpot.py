import discord

from utils.database import AgimusDB


async def win_jackpot(name: str, id: int):
    """
    This function will set the current jackpot winner
    and reset the jackpot with a default value
    """
    async with AgimusDB() as query:
        # update current jackpot row with winning data
        sql = "UPDATE jackpots SET winner=%s, time_won=NOW() ORDER BY id DESC LIMIT 1"
        vals = (name,)
        await query.execute(sql, vals)
        new_jackpot = "INSERT INTO jackpots (jackpot_value) VALUES (250)"
        await query.execute(new_jackpot)
        update_this_user = "UPDATE users SET jackpots = jackpots + 1 WHERE discord_id = %s"
        user_vals = (id,)
        await query.execute(update_this_user, user_vals)


async def increase_jackpot(amt: int):
    """
    This function increases the current jackpot value
    by the value passed as an arugument
    """
    async with AgimusDB() as query:
        sql = "UPDATE jackpots SET jackpot_value = jackpot_value + %s ORDER BY id DESC LIMIT 1"
        vals = (amt,)
        await query.execute(sql, vals)


async def set_player_score(user: int | str | discord.User | discord.Member, increase: int):
  """
  This function adjusts a player's score by the given amount, with a floor of zero.
  NOTE: THIS IS USED BY MULTIPLE GAMES!
  """
  if isinstance(user, (int, str)):
    sql = "UPDATE users SET score = GREATEST(score + %s, 0) WHERE discord_id = %s"
    vals = (increase, str(user))
  else:
    sql = """
      UPDATE users
      SET score = GREATEST(score + %s, 0), name = %s
      WHERE discord_id = %s
    """
    vals = (increase, user.display_name, str(user.id))

  async with AgimusDB() as query:
    await query.execute(sql, vals)
