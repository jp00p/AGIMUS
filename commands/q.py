import discord.ext.commands

from common import *
from utils.check_channel_access import access_check

@bot.command()
@commands.check(access_check)
async def qget(ctx, user:str):
  """
  This function is the main entrypoint of the !qget command
  and will get a user's DB details
  """
  selected_user = user.replace("<@", "").replace(">","")
  if is_integer(selected_user):
    await display_user(selected_user, ctx)
  else:
    await ctx.send("Usage: !qget [user]")


@bot.command()
@commands.check(access_check)
async def qset(ctx: discord.ext.commands.Context, user:str, key:str, value:str):
  """
  This function is the main entrypoint of the !qset command
  and will set a user's DB details
  """
  # f = open(config["commands"]["qget"]["data"])
  # f.close()
  # qspl = message.content.lower().replace("!qset ", "").split()
  selected_user = user.replace("<@", "").replace(">","")
  change_column = key
  change_value  = value
  this_user = await get_user(selected_user)
  modifiable_ints = ["score", "spins", "jackpots", "wager", "high_roller", "xp", "level"]
  modifiable_strings = ["profile_photo", "profile_sticker_1"]
  logger.info(f"{Fore.LIGHTBLUE_EX}{ctx.author.display_name}{Fore.RESET} is using mysterious Q powers on {Fore.GREEN}{this_user['name']}{Fore.RESET}")

  if change_column not in modifiable_ints and change_column not in modifiable_strings:
    modifiable = "\n".join(modifiable_ints + modifiable_strings)
    await ctx.send(f"Can only modify these values:```\n{modifiable}\n```")
  else:
    if change_column in modifiable_ints:
      if not is_integer(change_value):
        await ctx.reply(f"`{change_value}` is not an integer!")
        return
      else:
        await update_user(selected_user, change_column, change_value)
    elif change_column in modifiable_strings:
      await update_user(selected_user, change_column, change_value)
    await display_user(selected_user, ctx)


async def display_user(user_id, ctx):
  f = open(config["commands"]["qget"]["data"])
  user_columns = json.load(f)
  f.close()
  user_data = await get_user(user_id)
  logger.info(f"q data: {user_data}")

  user = await bot.fetch_user(user_id)
  embed = discord.Embed()
  embed.set_author(
    name=user.display_name,
    icon_url=user.display_avatar.url
  )
  for header in user_columns["display_headers"]:
    embed.add_field(
      name=header,
      value=user_data[header]
    )
  member_info = await ctx.guild.fetch_member(user_id)
  embed.set_footer(text=f"User Joined: {member_info.joined_at.strftime('%A, %b %-d %Y - %I:%M %p')}; Top Role: {member_info.top_role.name}")
  await ctx.send(embed=embed)