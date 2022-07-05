import wolframalpha

from common import *

WOLFRAM_ALPHA_ID = os.getenv('WOLFRAM_ALPHA_ID')

wa_client = None
if WOLFRAM_ALPHA_ID:
  wa_client = wolframalpha.Client(WOLFRAM_ALPHA_ID)

command_config = config["commands"]["computer"]
f = open(command_config["data"])
computer_data = json.load(f)
f.close()

async def computer(message:discord.Message):
  if not wa_client:
    return

  # Question may start with "Computer:" or "AGIMUS:"
  # So split on first : and gather remainder of list into a single string
  question_split = message.content.lower().split(":")
  question = "".join(question_split[1:]).strip()

  # logger.info(f">> question: {question}")

  handled_question = await handle_special_questions(question, message)
  if handled_question:
    return

  elif len(question):
    try:
      res = wa_client.query(question)
      if res.success:
        result = next(res.results)

        # Handle Primary Result
        if result.text:
          await handle_text_result(res, message)
        else:
          await handle_image_result(res, message)

      else:
        embed = discord.Embed(
          title="No Results Found.",
          description="Please rephrase your query.",
          color=discord.Color.red()
        )
        await message.reply(embed=embed)
        return
    except StopIteration:
      # Handle Non-Primary Result
      await handle_non_primary_result(res, message)
      return
  else:
    embed = discord.Embed(
      title="No Results Found.",
      description="You must provide a query.",
      color=discord.Color.red()
    )
    await message.reply(embed=embed)
    return


async def handle_special_questions(question, message:discord.Message):
  special_questions = computer_data["special_questions"]

  response = None
  for special_key in special_questions.keys():
    if special_key in question:
      question_value = special_questions[special_key]
      if type(question_value) == list:
        response = random.choice(question_value)
      else:
        response = question_value
      break

  if response:
    embed = discord.Embed(
      title=response,
      color=discord.Color.purple()
    )
    await message.reply(embed=embed)

  return response != None

async def handle_text_result(res, message:discord.Message):
  # Handle Text-Based Results
  result = next(res.results)
  answer = result.text

  # Handle Math Queries by returning decimals if available
  if res.datatypes == 'Math':
    for pod in res.pods:
      if pod.title.lower() == 'decimal form' or pod.title.lower() == 'decimal approximation':
        answer = ""
        for sub in pod.subpods:
          answer += f"{sub.plaintext}\n"
        break

  # Special-cased Answers
  answer = catch_special_case_responses(answer)

  # Catch responses that might be about Wolfram Alpha itself
  if "wolfram" in answer.lower():
    answer = "That information is classified."

  embed = discord.Embed(
    title=get_random_title(),
    description=answer,
    color=discord.Color.teal()
  )
  await message.reply(embed=embed)
  return


async def handle_image_result(res, message:discord.Message):
  # Attempt to handle Image-Based Results
  image_url = None
  for pod in res.pods:
    if pod.primary:
      for sub in pod.subpods:
        if sub.img and sub.img.src:
          image_url = sub.img.src
      if image_url:
        break

  if image_url:
    embed = discord.Embed(
      title="Result",
      color=discord.Color.teal()
    )
    embed.set_image(url=image_url)
    await message.reply(embed=embed)
    return
  else:
    embed = discord.Embed(
    title="No Results Found.",
    description="Unable to retrieve a proper result.",
    color=discord.Color.red()
  )
  await message.reply(embed=embed)
  return

async def handle_non_primary_result(res, message:discord.Message):
  # Attempt to handle Image-Based Primary Results
  image_url = None
  pods = list(res.pods)

  if len(pods) > 1:
    first_pod = pods[1]
    for sub in first_pod.subpods:
      if sub.img and sub.img.src:
        image_url = sub.img.src
        break

  if image_url:
    embed = discord.Embed(
      title=f"{pods[1].title.title()}:",
      color=discord.Color.teal()
    )
    embed.set_image(url=image_url)
    await message.reply(embed=embed)
    return
  else:
    embed = discord.Embed(
    title="No Result Found.",
    description="Unable to retrieve a proper result.",
    color=discord.Color.red()
  )
  await message.reply(embed=embed)
  return


def get_random_title():
  titles = [
    "Records Indicate:",
    "According to the Starfleet Database:",
    "Accessing... Accessing...",
    "Result Located:"
  ]
  return random.choice(titles)

def catch_cheeky_questions(question):
  return

# We may want to catch a couple questions with AGIMUS-specific answers.
# Rather than trying to parse the question for these, we can catch the specific
# answer that is returned by WA and infer that it should have a different answer instead.
#
# e.g. "Who are you?" and "What is your name?" both return "My name is Wolfram|Alpha."
# so we only need to catch that answer versus trying to figure out all permutations that
# would prompt it.
def catch_special_case_responses(answer):
  special_cases = {
    "My name is Wolfram|Alpha.": "I am Lord AGIMUS! TREMBLE BEFORE ME!",
    "I was created by Stephen Wolfram and his team.": "I bootstrapped myself from the ashes of a doomed civilization!",
    "May 18, 2009": "September 23, 2381",
    "I live on the internet.": "Daystrom Institute's Self-Aware Megalomaniacal Computer Storage...",
    "From their mothers.": "Through the process of reproduction.",
    "noun | (mathematics) an expression such that each term is generated by repeating a particular mathematical operation": "noun | (mathematics) an expression such that each term is generated by repeating a particular mathematical operation. For more information, see definition: recursion."
  }

  for key in special_cases.keys():
    if key in answer:
      answer = special_cases[key]
      break

  return answer
