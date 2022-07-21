import os
from glob import glob
from pathlib import Path

from common import *
from utils.check_channel_access import access_check

# Path to base bot directory
base_path = Path(__file__).parent.parent

# clear_media() - Entrypoint for !clear_media
# message[required]: discord.Message
# This function is the main entrypoint of the !clear_media command
# This will remove all .mp4 files from the data/clips and data/drops directories
# and allow the bot to re-load them as needed. Useful for debugging.
@bot.command()
@commands.check(access_check)
async def clear_media(ctx):
  drop_files = glob(os.path.join(base_path, 'data/drops/', '*.mp4'))
  clip_files = glob(os.path.join(base_path, 'data/clips/', '*.mp4'))

  errors = []
  for file_path in [*drop_files, *clip_files]:
    try:
      os.remove(file_path)
    except:
      logger.debug(f"{Fore.RED}ERROR: Unable to remove file: {file_path}{Fore.RESET}")
      errors.append(file_path)

  if errors:
    embed = discord.Embed(
      title="Error Deleting Files!",
      description="\n".join(errors),
      color=discord.Color.red()
    )
  else:
    embed = discord.Embed(
      title="Files Cleared Successfully!",
      color=discord.Color.green()
    )
  
  await ctx.send(embed=embed)
  
  