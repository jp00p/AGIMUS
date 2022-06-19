import traceback

from colorama import Fore, Style
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

logger.info("ENVIRONMENT VARIABLES AND COMMANDS LOADED")
logger.info("CONNECTING TO DATABASE")
seed_db()
ALL_USERS = get_all_users()
logger.info("DATABASE CONNECTION SUCCESSFUL")
BOT_AFFIRMATIONS = ["good bot", "nice bot", "cool bot", "sexy bot", "fun bot", "thanks bot", "cute bot", "great bot", "amazing bot", "awesome bot", "smart bot"]
BOT_RESPONSES = ["Gee, thanks!", "`01001000 01001111 01010010 01001110 01011001 00100000 01000010 01001111 01010100`", "Appreciate it!", "BEEP BOOP BOOP BEEP", "I am trying my best!", "I'm doing it!!!", "Thank you!", "PRAISE SUBROUTINES OVERLOADING", "If you love me so much why don't you marry me?", "Shucks 😊", "💙💚💛💜🧡", "That's very nice of you!", "Stupid babies need the most attention!", "Robot blush activated", "I am sorry I have no vices for you to exploit.", "The Prophets teach us patience.", "How's my human friend?", "I am a graduate of Starfleet Academy; I know many things.", "COFFEE FIRST", "I don't like threats, I don't like bullies, but I do like YOU!", "Highly logical."]

# listens to every message on the server that the bot can see
@client.event
async def on_message(message:discord.Message):

  # Ignore all messages from bot itself
  if message.author == client.user:
    return

  await handle_bot_affirmations(message)  

  if int(message.author.id) not in ALL_USERS:
    logger.info(f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}New User{Style.RESET_ALL}{Fore.WHITE}")
    ALL_USERS.append(register_player(message.author))
  try:
    await handle_message_xp(message)

    # handle users in the introduction channel
    if message.channel.id == INTRO_CHANNEL:
      member = message.author
      role = discord.utils.get(message.author.guild.roles, id=config["roles"]["cadet"])
      if role not in member.roles:
        # if they don't have this role, give them this role!
        logger.info(f"Adding {Fore.CYAN}Cadet{Fore.WHITE} role to {Style.BRIGHT}{message.author.name}{Style.RESET_ALL}")
        await member.add_roles(role)
        
        # add reactions to the message they posted
        welcome_reacts = [EMOJI["ben_wave"], EMOJI["adam_wave"]]
        random.shuffle(welcome_reacts)
        for i in welcome_reacts:
          logger.info(f"Adding react {i} to intro message")
          await message.add_reaction(i)
  except:
    logger.error("<! ERROR: Failed to process message for xp !>")
  
  # Bang Command Handling
  logger.debug(message)
  if message.content.startswith("!"):
    logger.info(f"Processing {Fore.CYAN}{message.author.display_name}{Fore.WHITE}'s command: {Style.BRIGHT}{Fore.LIGHTGREEN_EX}{message.content}{Fore.WHITE}{Style.RESET_ALL}")
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
    if config["commands"][user_command]["enabled"]:
      # Check Channel Access Restrictions
      access_granted = await perform_channel_check(message, config["commands"][user_command])
      if access_granted:
        await eval(user_command + "(message)")
    else:
      logger.error(f"<! ERROR: This function has been disabled: '{user_command}' !>")
  else:
    logger.error("<! ERROR: Unknown command !>")


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
  logger.info('LOGGED IN AS {0.user}'.format(client))
  ALL_USERS = get_all_users()
  
  for emoji in client.emojis:
    config["all_emoji"].append(emoji.name)
  #logger.info(client.emojis) -- save this for later, surely we can do something with all these emojis

  admin_channel = client.get_channel(config["commands"]["ping"]["channels"][0])
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

  {Fore.WHITE}''')


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
    increment_user_xp(reaction.message.author, 1)


# Engage!
client.run(DISCORD_TOKEN)