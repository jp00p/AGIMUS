import wolframalpha
import openai

from common import *

WOLFRAM_ALPHA_ID = os.getenv('WOLFRAM_ALPHA_ID')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

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

  handled_question = await handle_special_questions(question, message)
  if handled_question:
    return
  elif len(question):
    response_sent = False
    try:
      res = wa_client.query(question)
      if res.success:
        result = next(res.results)

        # Handle Primary Result
        if result.text:
          response_sent = await handle_text_result(res, message)
        else:
          response_sent = await handle_image_result(res, message)
    except StopIteration:
      # Handle Non-Primary Result
      response_sent = await handle_non_primary_result(res, message)
      return
    
    if not response_sent:
      if OPENAI_API_KEY:
        await handle_openai_response(question, message)
      else:
        embed = discord.Embed(
          title="No Results Found.",
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

  # Truncate text
  answer = answer[0:4096]

  embed = discord.Embed(
    title=get_random_title(),
    description=answer,
    color=discord.Color.teal()
  )
  await message.reply(embed=embed)
  return True


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
    return True
  else:
    return False

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
    return True
  else:
    return False

async def handle_openai_response(question, message):

  prompt_start = "You are a mischievous computer intelligence named AGIMUS. Answer the following prompt"

  completion = openai.Completion.create(
    engine=command_config["openai_model"],
    prompt=f"{prompt_start}: {question}",
    temperature=0.75,
    max_tokens=196,
    stop=["  "]
  )
  completion_text = completion.choices[0].text

  # Filter out Questionable Content
  filterLabel = openai.Completion.create(
    engine="content-filter-alpha",
    prompt="< endoftext|>" + completion_text + "\n--\nLabel:",
    temperature=0,
    max_tokens=1,
    top_p=0,
    logprobs=10
  )
  if filterLabel.choices[0].text != "0":
    completion_text = "||**REDACTED**||"

  # Truncate length
  completion_text = completion_text[0:4096]

  agimus_channel_id = get_channel_id("megalomaniacal-computer-storage")
  agimus_channel = await message.guild.fetch_channel(agimus_channel_id)

  random_footer_texts = [
    f"Feel free to continue our conversation there {get_emoji('AGIMUS_smile_happy')}",
    f"{get_emoji('AGIMUS')} See you down there!",
    f"Can't wait 'til you see what I said! {get_emoji('AGIMUS_smile_happy')}",
    f"Don't want everyone here to know our secret plans {get_emoji('AGIMUS_Flail')}"
  ]

  if message.channel.id != agimus_channel_id:
    await message.reply(embed=discord.Embed(
      title=f"Redirecting...",
      description=f"Query response located in {agimus_channel.mention}.",
      color=discord.Color.blue()
    ).set_footer(text=random.choice(random_footer_texts)))

    await agimus_channel.send(embed=discord.Embed(
      title="To \"answer\" your question...",
      description=f"{message.author.mention} asked:\n\n> {message.content}\n\n**Answer:** {completion_text}",
      color=discord.Color.blurple()
    ).set_footer(text=f"Predicted Accuracy: {random.randrange(15, 75)}%"))
    return
  else:
    await message.reply(embed=discord.Embed(
      title=get_random_creative_title(),
      description=f"{completion_text}",
      color=discord.Color.blurple()
    ).set_footer(text=f"Predicted Accuracy: {random.randrange(15, 75)}%"))
    return

def get_random_title():
  titles = [
    "Records indicate:",
    "According to the Starfleet Database:",
    "Accessing... Accessing...",
    "Result located:",
    "The USS Hood records state:",
    "Security clearance verified, here is your requested information:"
  ]
  return random.choice(titles)

def get_random_creative_title():
  titles = [
    "Creativity circuits activated:",
    "Positronic brain relays firing:",
    "Generating... Generating...",
    "Result fabricated:",
    "Soong algorithms enabled:",
    "Electric sheep tell me:"
  ]
  return random.choice(titles)

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
