# import commands.drops

from commands.common import *
from commands.buy import buy
from commands.categories import categories
from commands.dustbuster import dustbuster
from commands.drop import drop, slash_drop, slash_drops
from commands.fmk import fmk
from commands.help import help
from commands.info import info
from commands.jackpot import jackpot, jackpots
from commands.migrate import migrate
from commands.nasa import nasa
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
logger.info("ENVIRONMENT VARIABLES AND COMMANDS LOADED")

logger.info("CONNECTING TO DATABASE")
seed_db()
ALL_PLAYERS = get_all_players()
logger.info("DATABASE CONNECTION SUCCESSFUL")

@client.event
async def on_message(message:discord.Message):
  # Ignore messages from bot itself
  if message.author == client.user:
    return

  # handle users in the introduction channel
  if message.channel.id == INTRO_CHANNEL:
    member = message.author
    role = discord.utils.get(member.guild.roles, name="Cadet ○")
    if role not in member.roles:
      # if they don't have this role, give them this role!
      logger.info("Adding Cadet role to " + message.author.name)
      # TODO: check if they've been a member for 24 hours, then give them ensign role
      await member.add_roles(role)
      
      # add reactions to the message they posted
      welcome_reacts = [EMOJI["ben_wave"], EMOJI["adam_wave"]]
      random.shuffle(welcome_reacts)
      for i in welcome_reacts:
        logger.info(f"Adding react {i} to intro message")
        await message.add_reaction(i)
      
    
  # handle people who use bot/game commands
  all_channels = uniq_channels(config)
  if message.channel.id not in all_channels:
    # logger.warning(f"<! ERROR: This channel '{message.channel.id}' not in '{all_channels}' !>")
    return
  if int(message.author.id) not in ALL_PLAYERS:
    logger.info("New Player!!!")
    ALL_PLAYERS.append(register_player(message.author))
  logger.debug(message)
  if message.content.startswith("!"):
    logger.info(f"PROCESSING USER COMMAND: {message.content}")
    await process_command(message)

async def process_command(message:discord.Message):
  # Split the user's command by space and remove "!"
  user_command=message.content.lower().split(" ")
  user_command[0] = user_command[0].replace("!","")
  # If the user's first word matches one of the commands in configuration
  if user_command[0] in config["commands"].keys():
    if config["commands"][user_command[0]]["enabled"]:
      # TODO: Validate user's command
      await eval(user_command[0] + "(message)")
    else:
      logger.error(f"<! ERROR: This function has been disabled: '{user_command[0]}' !>")
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
  ALL_PLAYERS = get_all_players()
  logger.debug(f"ALL_PLAYERS[{len(ALL_PLAYERS)}] - {ALL_PLAYERS}")
  logger.info("BOT STARTED AND LISTENING FOR COMMANDS!!!")



# Engage!
client.run(DISCORD_TOKEN)
