from common import *
from utils.check_channel_access import access_check
from pytz import timezone
import pytz

@bot.slash_command(
  name="aliases",
  description="View User Aliases (ADMIN ONLY)"
)
@option(
  "user",
  discord.User,
  description="The user you wish to view past aliases of",
  required=True
)
@commands.check(access_check)
async def aliases(ctx:discord.ApplicationContext, user:discord.User):
  aliases = db_get_user_aliases(user.id)

  if not aliases:
    await ctx.respond(embed=discord.Embed(
      title=f"{user.display_name} has no logged aliases!",
      color=discord.Color.red()
    ), ephemeral=True)
    return

  old_aliases = "\n".join([a['old_alias'] for a in aliases])
  new_aliases = "\n".join([a['new_alias'] for a in aliases])

  pst_tz = timezone('US/Pacific')

  raw_timestamps = [pytz.utc.localize(a['time_created']) for a in aliases]
  aware_timestamps = [pst_tz.normalize(t.astimezone(pst_tz)) for t in raw_timestamps]
  dates_changed = "\n".join([t.strftime("%B %d, %Y - %I:%M %p") for t in aware_timestamps])

  embed = discord.Embed(
    title=f"{user.display_name}'s Known Aliases",
    color=discord.Color.purple()
  )
  embed.add_field(
    name=f"Previous Alias",
    value=old_aliases
  )
  embed.add_field(
    name=f"New Alias",
    value=new_aliases
  )
  embed.add_field(
    name=f"Date Changed",
    value=dates_changed
  )
  await ctx.respond(embed=embed, ephemeral=True)


def db_get_user_aliases(user_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM user_aliases WHERE user_discord_id = %s ORDER BY time_created ASC;"
    vals = (user_discord_id,)
    query.execute(sql, vals)
    aliases = query.fetchall()
  return aliases