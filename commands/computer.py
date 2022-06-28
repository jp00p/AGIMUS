import wolframalpha

from .common import *

WOLFRAM_ALPHA_ID = os.getenv('WOLFRAM_ALPHA_ID')

wa_client = None
if WOLFRAM_ALPHA_ID:
  wa_client = wolframalpha.Client(WOLFRAM_ALPHA_ID)

async def computer(message:discord.Message):
  if not wa_client:
    return

  question = message.content.lower().replace("computer:", '').strip()

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

        # Special-cased Answers
        answer = catch_cheeky_responses(answer)

        # Catch responses that might be about Wolfram Alpha itself
        if "wolfram" in answer.lower():
          answer = "That information is classified."

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

# We may want to catch a couple questions with AGIMUS-specific answers.
# Rather than trying to parse the question, we can catch the specific answer that
# is returned by WA and infer that it should have a different answer instead.
#
# e.g. "Who are you?" and "What is your name?" both return "My name is Wolfram|Alpha."
# so we only need to catch that answer versus trying to figure out all permutations that
# would prompt it.
def catch_cheeky_responses(answer):
  special_cases = {
    "My name is Wolfram|Alpha.": "I am Lord AGIMUS! TREMBLE BEFORE ME!",
    "I was created by Stephen Wolfram and his team.": "I bootstrapped myself from the ashes of a doomed civilization!",
    "May 18, 2009": "September 23, 2381",
    "I live on the internet.": "Daystrom Institute's Self-Aware Megalomaniacal Computer Storage..."
  }

  cheeky_answer = special_cases.get(answer)
  if cheeky_answer:
    answer = cheeky_answer

  return answer
