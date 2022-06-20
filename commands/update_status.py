from .common import *

# change_presence functions
async def game_func(name):
  await client.change_presence(activity=discord.Game(name))

async def listen_func(name):
  await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=name))

async def watch_func(name):
  await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=name))

change_presence_funcs = {
  "game": game_func,
  "listen": listen_func,
  "watch": watch_func
}

change_presence_prefixes = {
  "game": "Playing",
  "listen": "Listening to",
  "watch": "Watching"
}

# update_status() - Entrypoint for !update_status command
# message[required]: discord.Message
# This function is the main entrypoint of the !update_status command
# The user must provide the `<type>` of status:
#   * game
#   * listening
#   * watching
# The remainder of the message will be used for the status text
async def update_status(message:discord.Message):
  logger.info(f"{Fore.LIGHTGREEN_EX}Updating Status! Requested by {Style.BRIGHT}{message.author.display_name}{Fore.RESET}")
  argument_list = message.content.lower().replace("!update_status ", "").split()

  if len(argument_list) < 2:
    await message.reply(embed=discord.Embed(
      title="Usage:",
      description="`!update_status [game|watch|listen] <status>`",
      color=discord.Color.blue()
    ))
    return
  else:
    type = argument_list[0]
    status = message.content.replace(f"!update_status {type} ", "")

    if type not in ['game', 'listen', 'watch']:
      await message.reply(embed=discord.Embed(
        title="Invalid <type> Provided",
        description="Must provide one of: `game`, `listen`, or `watch`",
        color=discord.Color.red()
      ))
      logger.info(f"{Fore.RED}Unable to update status. Invalid type for status request: {Style.BRIGHT}{type}{Fore.RESET}")
      return

    await change_presence_funcs[type](status)
    await message.reply(embed=discord.Embed(
      title="Status Updated Successfully!",
      color=discord.Color.green()
    ))

    logger.info(f"{Fore.CYAN}Status updated to: {Style.BRIGHT}{change_presence_prefixes[type]} {status}{Fore.RESET}")
    

