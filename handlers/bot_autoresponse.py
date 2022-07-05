from common import *

# Load up our list of complimentary and condemnation adjectives
with open('bot_affirmations.txt') as f:
  bot_affirmations = f.read().splitlines()
with open('bot_condemnations.txt') as f:
  bot_condemnations = f.read().splitlines()

# bot_affirmations(message) - responds to bot compliments/complaints
# message[required]: discord.Message
async def handle_bot_affirmations(message:discord.Message):
  
  if message.author.bot:
    return

  message_content = message.content.lower()

  for condemnation in bot_condemnations:
    if f"{condemnation} bot" in message_content:
      if not (re.match(fr"not a?\s?{condemnation} bot", message_content)):
        await respond_to_sass(message)
        return

  for affirmation in bot_affirmations:
    if f"{affirmation} bot" in message_content:
      if re.match(fr"not a?\s?{affirmation} bot", message_content):
        await respond_to_sass(message)
        return
      else:
        await respond_to_praise(message)
        return

async def respond_to_sass(message:discord.Message):
  logger.info(f"{BOT_NAME} received some {Fore.YELLOW}sass{Fore.RESET} from {Fore.LIGHTBLUE_EX}{message.author.display_name}{Fore.RESET}")
  await message.add_reaction(EMOJI["shocking"])
  await message.reply(random.choice(config["bot_condemnation_responses"]), mention_author=True)

async def respond_to_praise(message:discord.Message):
  logger.info(f"{BOT_NAME} received some {Fore.RED}love{Fore.RESET} from {Fore.LIGHTBLUE_EX}{message.author.display_name}{Fore.RESET}")
  await message.add_reaction(EMOJI["shocking"])
  await message.reply(random.choice(config["bot_affirmation_responses"]), mention_author=True)