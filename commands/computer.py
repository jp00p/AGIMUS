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
    try:
      res = wa_client.query(question)
      if res.success:
        answer = next(res.results).text

        # Handle Math Queries by returning decimals if available
        if res.datatypes == 'Math':
          for pod in res.pods:
            if pod.title.lower() == 'decimal form' or pod.title.lower() == 'decimal approximation':
              answer = ""
              for sub in pod.subpods:
                answer += f"{sub.plaintext}\n"
              break
        
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
    except StopIteration:
      logger.info(f"Encountered StopIteration with query: {question}")
      embed = discord.Embed(
        title="Query Too Generalized or Unsupported",
        description="Please rephrase your query.",
        color=discord.Color.red()
      )
      await message.reply(embed=embed)
  else:
    embed = discord.Embed(
      title="No Results Found.",
      description="You must provide a query.",
      color=discord.Color.red()
    )
    await message.reply(embed=embed)

def get_random_title():
  titles = [
    "Records Indicate:",
    "According to the Starfleet Database:",
    "Accessing... Accessing...",
    "Result Located:"
  ]
  return random.choice(titles)

