#  █████   ██████  ██ ███    ███ ██    ██ ███████ 
# ██   ██ ██       ██ ████  ████ ██    ██ ██      
# ███████ ██   ███ ██ ██ ████ ██ ██    ██ ███████ 
# ██   ██ ██    ██ ██ ██  ██  ██ ██    ██      ██ 
# ██   ██  ██████  ██ ██      ██  ██████  ███████ 

# Slash Commands
from commands.drop import drops, drop
from commands.clip import clip, clips
from commands.nextep import nexttrek, nextep

# Commands
from commands.common import *
from commands.buy import buy
from commands.categories import categories
from commands.clear_media import clear_media
from commands.computer import computer
from commands.dustbuster import dustbuster
from commands.fmk import fmk
from commands.help import help
from commands.info import info
from commands.jackpot import jackpot, jackpots
from commands.nasa import nasa
from commands.poker import *
from commands.ping import ping
from commands.profile import profile
from commands.quiz import quiz
from commands.q import qget, qset
from commands.report import report
from commands.randomep import randomep
#from commands.restrict_emojis import restrict_emojis
from commands.scores import scores
from commands.setwager import setwager
from commands.shop import shop
from commands.slots import slots, testslots
from commands.triv import *
from commands.trekduel import trekduel
from commands.trektalk import trektalk
from commands.tuvix import tuvix
from commands.update_status import update_status
from commands.server_logs import show_leave_message, show_nick_change_message
# Handlers
from handlers.alerts import handle_alerts
from handlers.bot_autoresponse import handle_bot_affirmations
from handlers.xp import handle_message_xp, handle_react_xp
from handlers.starboard import handle_starboard_reactions, get_all_starboard_posts
# Tasks
from tasks.scheduler import Scheduler
from tasks.bingbong import bingbong_task
from tasks.weyounsday import weyounsday_task
# Utils
from utils.check_channel_access import perform_channel_check

logger.info(f"{Style.BRIGHT}{Fore.LIGHTMAGENTA_EX}ENVIRONMENT VARIABLES AND COMMANDS LOADED{Fore.RESET}")
logger.info(f"{Fore.LIGHTMAGENTA_EX}CONNECTING TO DATABASE{Fore.RESET}")
seed_db()
ALL_USERS = get_all_users()
logger.info(f"{Fore.LIGHTMAGENTA_EX}DATABASE CONNECTION SUCCESSFUL{Fore.RESET}{Style.RESET_ALL}")

# listens to every message on the server that the bot can see
@bot.event
async def on_message(message:discord.Message):

  # Ignore all messages from bot itself
  if message.author == bot.user:
    return

  # Special message Handlers
  try:
    await handle_bot_affirmations(message)
    await handle_alerts(message)
  except Exception as e:
    logger.error(f"{Fore.RED}<! ERROR: Encountered error in handlers !> {e}{Fore.RESET}")
    logger.error(traceback.format_exc())

  if int(message.author.id) not in ALL_USERS:
    logger.info(f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}New User{Style.RESET_ALL}{Fore.RESET}")
    ALL_USERS.append(register_player(message.author))
  try:
    await handle_message_xp(message)
  except Exception as e:
    logger.error(f"{Fore.RED}<! ERROR: Failed to process message for xp !> {e}{Fore.RESET}")
    logger.error(traceback.format_exc())
  
  # Bang Command Handling
  #logger.debug(message)
  if message.content.startswith("!") or any(message.content.lower().startswith(x) for x in ["computer:", "agimus:"]):
    logger.info(f"Attempting to process {Fore.CYAN}{message.author.display_name}{Fore.RESET}'s command: {Style.BRIGHT}{Fore.LIGHTGREEN_EX}{message.content}{Fore.RESET}{Style.RESET_ALL}")
    try:
      await process_command(message)
    except BaseException as e:
      logger.info(f">>> Encountered Exception!")
      logger.info(e)
      exception_embed = discord.Embed(
        title=f"Oops... Encountered exception processing request: {message.content}",
        description=f"{e}\n```{traceback.format_exc()}```",
        color=discord.Color.red()
      )
      logging_channel = bot.get_channel(LOGGING_CHANNEL)
      await logging_channel.send(embed=exception_embed)

async def process_command(message:discord.Message):
  # Split the user's command by space and remove "!"
  split_string = message.content.lower().split(" ")
  if message.content.startswith("!"):
    user_command = split_string[0].replace("!","")
  elif any(message.content.lower().startswith(x) for x in ["computer:", "agimus:"]):
    user_command = "computer"

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
          logger.info(traceback.format_exc())
    else:
      logger.error(f"{Fore.RED}<! ERROR: This function has been disabled: '{user_command}' !>{Fore.RESET}")
  else:
    logger.error(f"{Fore.RED}<! ERROR: Unknown command !>{Fore.RESET}")

@bot.event
async def on_ready():
  global EMOJI
  global ALL_STARBOARD_POSTS
  random.seed()
  EMOJI["shocking"] = discord.utils.get(bot.emojis, name="q_shocking")
  EMOJI["chula"] = discord.utils.get(bot.emojis, name="chula_game")
  EMOJI["allamaraine"] = discord.utils.get(bot.emojis, name="allamaraine")
  EMOJI["love"] = discord.utils.get(bot.emojis, name="love_heart_tgg")
  EMOJI["adam_wave"] = discord.utils.get(bot.emojis, name="adam_wave_hello")
  EMOJI["ben_wave"] = discord.utils.get(bot.emojis, name="ben_wave_hello")
  logger.info(f"{Back.LIGHTRED_EX}{Fore.LIGHTWHITE_EX}LOGGED IN AS {bot.user}{Fore.RESET}{Back.RESET}")
  ALL_USERS = get_all_users()
  ALL_STARBOARD_POSTS = get_all_starboard_posts()
  logger.info(f"{ALL_STARBOARD_POSTS}")
  for emoji in bot.emojis:
    config["all_emoji"].append(emoji.name)
  #logger.info(client.emojis) -- save this for later, surely we can do something with all these emojis
  
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

  await bot.change_presence(status=discord.Status.online, activity=discord.Activity(name='PRAISE THE FOUNDERS', type=2, status="online"))



# listen to reactions
# TODO: change to on_raw_reaction_add so old messages are counted too!
@bot.event
async def on_reaction_add(reaction, user):
  await handle_react_xp(reaction, user)
  
# listen to raw reactions  
@bot.event
async def on_raw_reaction_add(payload):
  if payload.event_type == "REACTION_ADD":
    await handle_starboard_reactions(payload)
    await handle_trivia_reactions(payload)

# listen to server leave events
@bot.event
async def on_member_remove(member):
  await show_leave_message(member)

# listen to nickname change events
@bot.event
async def on_member_update(memberBefore,memberAfter):
  if memberBefore.nick != memberAfter.nick:
    await show_nick_change_message(memberBefore, memberAfter) 

# Schedule Tasks
scheduled_tasks = [
  bingbong_task(bot),
  weyounsday_task(bot)
]

scheduler = Scheduler()
for task in scheduled_tasks:
  scheduler.add_task(task["task"], task["crontab"])
scheduler.start()

# Engage!
bot.run(DISCORD_TOKEN)