import wolframalpha

from .common import *

WOLFRAM_ALPHA_ID = os.getenv('WOLFRAM_ALPHA_ID')

wa_client = None
if WOLFRAM_ALPHA_ID:
  wa_client = wolframalpha.Client(WOLFRAM_ALPHA_ID)

async def computer(message:discord.Message):
  if not wa_client:
    return

  question = message.content.lower().replace("computer:", '')
  if len(question):
    res = wa_client.query(question)
    if res.success:
      answer = next(res.results).text
      embed = discord.Embed(
        title=get_random_title(),
        description=answer,
        color=discord.Color.teal()
      )
      await message.reply(embed=embed)
    else:
      embed = discord.Embed(
        title="No Results Found.",
        description="Please rephrase your query.",
        color=discord.Color.red()
      )
      await message.reply(embed=embed)

def get_random_title():
  titles = [
    "Records indicate:",
    "According to the Starfleet Database:",
    "Accessing... Accessing... Result:",
    "Result located:"
  ]
  return random.choice(titles)

