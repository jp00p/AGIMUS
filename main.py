import traceback

from commands.common import *
from commands.bot_autoresponse import handle_bot_affirmations
from commands.buy import buy
from commands.categories import categories
from commands.clear_media import clear_media
from commands.clip import clip, clips
from commands.dustbuster import dustbuster
from commands.drop import drop, slash_drop, slash_drops
from commands.fmk import fmk
from commands.help import help
from commands.info import info
from commands.jackpot import jackpot, jackpots
from commands.nasa import nasa
from commands.nextep import nexttrek, nextep
from commands.poker import *
from commands.ping import ping
from commands.profile import profile
from commands.quiz import quiz
from commands.q import qget, qset
from commands.report import report
from commands.randomep import randomep
from commands.scores import scores
from commands.setwager import setwager
from commands.shop import shop
from commands.slots import slots, testslots
from commands.triv import *
from commands.trekduel import trekduel
from commands.trektalk import trektalk
from commands.tuvix import tuvix
from commands.xp import handle_message_xp, increment_user_xp
from utils.check_channel_access import perform_channel_check

logger.info(f"{Fore.LIGHTGREEN_EX}ENVIRONMENT VARIABLES AND COMMANDS LOADED{Fore.RESET}")
logger.info(f"{Fore.LIGHTMAGENTA_EX}CONNECTING TO DATABASE{Fore.RESET}")
seed_db()
ALL_USERS = get_all_users()
logger.info(f"{Fore.LIGHTCYAN_EX}DATABASE CONNECTION SUCCESSFUL{Fore.RESET}")

# listens to every message on the server that the bot can see
@client.event
async def on_message(message:discord.Message):

  # Ignore all messages from bot itself
  if message.author == client.user:
    return

  await handle_bot_affirmations(message)  

  if int(message.author.id) not in ALL_USERS:
    logger.info(f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}New User{Style.RESET_ALL}{Fore.RESET}")
    ALL_USERS.append(register_player(message.author))
  try:
    await handle_message_xp(message)

    # handle users in the introduction channel
    if message.channel.id == INTRO_CHANNEL:
      member = message.author
      role = discord.utils.get(message.author.guild.roles, id=config["roles"]["cadet"])
      if role not in member.roles:
        # if they don't have this role, give them this role!
        logger.info(f"Adding {Fore.CYAN}Cadet{Fore.RESET} role to {Style.BRIGHT}{message.author.name}{Style.RESET_ALL}")
        await member.add_roles(role)
        
        # add reactions to the message they posted
        welcome_reacts = [EMOJI["ben_wave"], EMOJI["adam_wave"]]
        random.shuffle(welcome_reacts)
        for i in welcome_reacts:
          logger.info(f"{Fore.LIGHTBLACK_EX}Adding react {i} to intro message{Fore.RESET}")
          await message.add_reaction(i)
  except Exception as e:
    logger.error(f"{Fore.RED}<! ERROR: Failed to process message for xp !> {e}{Fore.RESET}")
  
  # Bang Command Handling
  #logger.debug(message)
  if message.content.startswith("!"):
    logger.info(f"Attempting to process {Fore.CYAN}{message.author.display_name}{Fore.RESET}'s command: {Style.BRIGHT}{Fore.LIGHTGREEN_EX}{message.content}{Fore.RESET}{Style.RESET_ALL}")
    try:
      await process_command(message)
    except Exception as e:
      logging_channel = client.get_channel(config["logging_channel"])
      exception_embed = discord.Embed(
        title="Oops...",
        description=f"{e}\n```{traceback.format_exc()}```",
        color=discord.Color.red()
      )
      await logging_channel.send(embed=exception_embed)

async def process_command(message:discord.Message):
  # Split the user's command by space and remove "!"
  split_string = message.content.lower().split(" ")
  user_command = split_string[0].replace("!","")
  # If the user's first word matches one of the commands in configuration
  if user_command in config["commands"].keys():
    # Check enabled
    logger.info(f"Parsed command: {Fore.LIGHTBLUE_EX}{user_command}{Fore.RESET}")
    if config["commands"][user_command]["enabled"]:
      # Check Channel Access Restrictions 
      access_granted = await perform_channel_check(message, config["commands"][user_command])
      logger.info(f"Access granted? {Fore.LIGHTGREEN_EX}{access_granted}{Fore.RESET}")
      if access_granted:
        logger.info(f"{Fore.RED}Firing command!{Fore.RESET}")
        try:
          await eval(user_command + "(message)")
        except SyntaxError as s:
          logger.info(f"ERROR WITH EVAL: {Fore.RED}{s}{Fore.RESET}")
    else:
      logger.error(f"{Fore.RED}<! ERROR: This function has been disabled: '{user_command}' !>{Fore.RESET}")
  else:
    logger.error(f"{Fore.RED}<! ERROR: Unknown command !>{Fore.RESET}")


@client.event
async def on_ready():
  global EMOJI
  random.seed()
  EMOJI["shocking"] = discord.utils.get(client.emojis, name="q_shocking")
  EMOJI["chula"] = discord.utils.get(client.emojis, name="chula_game")
  EMOJI["allamaraine"] = discord.utils.get(client.emojis, name="allamaraine")
  EMOJI["love"] = discord.utils.get(client.emojis, name="love_heart_tgg")
  EMOJI["adam_wave"] = discord.utils.get(client.emojis, name="adam_wave_hello")
  EMOJI["ben_wave"] = discord.utils.get(client.emojis, name="ben_wave_hello")
  logger.info(f"{Back.LIGHTRED_EX}{Fore.LIGHTWHITE_EX}LOGGED IN AS {client.user}{Fore.RESET}{Back.RESET}")
  ALL_USERS = get_all_users()
  
  for emoji in client.emojis:
    config["all_emoji"].append(emoji.name)
  #logger.info(client.emojis) -- save this for later, surely we can do something with all these emojis

  admin_channel = client.get_channel(config["channels"]["robot-diagnostics"])
  await admin_channel.send("The bot has come back online!")
  
  logger.info(f'''{Fore.LIGHTWHITE_EX}

                                _____
                       __...---'-----`---...__
                  _===============================
 ______________,/'      `---..._______...---'
(____________LL). .    ,--'
 /    /.---'       `. /
'--------_  - - - - _/
          `~~~~~~~~'
      {Fore.LIGHTMAGENTA_EX}BOT IS ONLINE AND READY FOR COMMANDS!

  {Fore.RESET}''')


# listen to reactions
@client.event
async def on_reaction_add(reaction, user):
  # If someone made a particularly reaction-worthy message, award them some XP!
  relevant_emojis = [
    config["emojis"]["data_lmao_lol"],
    config["emojis"]["picard_yes_happy_celebrate"],
    config["emojis"]["tgg_love_heart"]
  ]
  if f"{reaction.emoji}" in relevant_emojis and reaction.count >= 5:
    logger.info(f"User {Style.BRIGHT}{reaction.message.author}{Style.RESET_ALL} gets {Style.BRIGHT}1 xp{Style.RESET_ALL} for their post being reacted to!")
    increment_user_xp(reaction.message.author, 1)


# Engage!
client.run(DISCORD_TOKEN)