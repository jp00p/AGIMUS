from common import *
from utils.check_channel_access import access_check

@bot.slash_command(
  name="spongebob",
  description="Have AGIMUS sPoNgEbOb your text!"
)
@option(
  name="content",
  description="The text you wanna spit back!",
  required=True
)
@commands.check(access_check)
async def spongebob(ctx:discord.ApplicationContext, content:str):
  sponged = sponge(content)
  await ctx.respond(
    embed=discord.Embed(
      description=sponged,
      color=discord.Color.blurple()
    ).set_author(
      name="SpongeBobbed!",
      icon_url="https://i.imgur.com/bjDaNDJ.png"
    )
  )

def sponge(bob):
  """
  Input: string
  output: same string with alternating cases of alpha characters.
  (spaces, punctuation, and other non alphabetical characters ignored)
  """
  if not isinstance(bob, str):
    print("This is not a string")
    return
  wordList = []
  invert = False
  if bob[0] == bob[0].lower():
    invert = True
  for char in bob:
    if char.isalpha() is True:
      if invert:
        wordList.append(char.upper())
      else:
        wordList.append(char.lower())
      invert = not invert
    else:
      wordList.append(char)
  spongedBob = "".join(wordList)
  return spongedBob