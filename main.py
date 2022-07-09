#  █████   ██████  ██ ███    ███ ██    ██ ███████ 
# ██   ██ ██       ██ ████  ████ ██    ██ ██      
# ███████ ██   ███ ██ ██ ████ ██ ██    ██ ███████ 
# ██   ██ ██    ██ ██ ██  ██  ██ ██    ██      ██ 
# ██   ██  ██████  ██ ██      ██  ██████  ███████ 
from common import *

# Slash Commands
from commands.dustbuster import dustbuster
from commands.fmk import fmk
from commands.help import help
from commands.info import info
from commands.nasa import nasa
from commands.nextep import nextep, nexttrek
from commands.profile import profile
from commands.randomep import randomep
#from commands.restrict_emojis import restrict_emojis
from commands.trekduel import trekduel
from commands.trektalk import trektalk
from commands.tuvix import tuvix

# Slash Command Groups
import commands.drop
import commands.clip

# Bang Commands
from commands.buy import buy
from commands.categories import categories
from commands.clear_media import clear_media
from commands.computer import computer
from commands.ping import ping
from commands.poker import *
from commands.q import qget, qset
from commands.report import report
from commands.reports import reports
from commands.quiz import quiz
from commands.report import report
from commands.scores import scores
from commands.setwager import setwager
from commands.shop import shop
from commands.triv import *
from commands.update_status import update_status
from commands.wordcloud import wordcloud

# Cogs
from cogs.slots import Slots
from cogs.ping import Ping
from cogs.poker import Poker
bot.add_cog(Slots(bot))
bot.add_cog(Ping(bot))
bot.add_cog(Poker(bot))

# Handlers
from handlers.alerts import handle_alerts
from handlers.bot_autoresponse import handle_bot_affirmations
from handlers.save_message import save_message_to_db
from handlers.server_logs import *
from handlers.starboard import get_all_starboard_posts, handle_starboard_reactions
from handlers.xp import handle_message_xp, handle_react_xp

# Tasks
from tasks.bingbong import bingbong_task
from tasks.scheduler import Scheduler
from tasks.weyounsday import weyounsday_task

# Utils
from utils.check_channel_access import perform_channel_check

logger.info(f"{Style.BRIGHT}{Fore.LIGHTRED_EX}ENVIRONMENT VARIABLES AND COMMANDS LOADED{Fore.RESET}{Style.RESET_ALL}")
logger.info(f"{Style.BRIGHT}{Fore.LIGHTRED_EX}CONNECTING TO DATABASE{Fore.RESET}{Style.RESET_ALL}")
seed_db()
ALL_USERS = get_all_users()
logger.info(f"{Style.BRIGHT}{Fore.RED}DATABASE CONNECTION SUCCESSFUL{Fore.RESET}{Style.RESET_ALL}")

background_tasks = set() # for non-blocking tasks

# listens to every message on the server that the bot can see
@bot.event
async def on_message(message:discord.Message):
  logger.info("... ?")
  try:
    # Ignore all messages from any bot
    if message.author == bot.user or message.author.bot:
      return
    
    try:
      await bot.process_commands(message)
    except BaseException as e:
      logger.info(f"{Fore.RED}<! ERROR: Encountered error in process_commands !> {e}{Fore.RESET}")
      logger.info(traceback.format_exc())    

    # message logging
    try:
      msg_save_task = asyncio.create_task(save_message_to_db(message))
      background_tasks.add(msg_save_task)
      msg_save_task.add_done_callback(background_tasks.discard)
    except Exception as e:
      logger.error(f"{Fore.RED}<! ERROR: Encountered error in saving message task !> {e}{Fore.RESET}")
      logger.error(traceback.format_exc())

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
  except Exception as e:
    logger.info(f"Error in on_message: {e}")
    logger.info(traceback.format_exc())

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
  try:
    logger.info(f"{Back.LIGHTRED_EX}{Fore.LIGHTWHITE_EX}LOGGED IN AS {bot.user}{Fore.RESET}{Back.RESET}")

    # We can handle this better late with an Emoji class helper, but for now just create a dict
    # Use EMOJI dict from common
    for e in bot.emojis:
      EMOJIS[e.name] = e

    global ALL_STARBOARD_POSTS
    ALL_USERS = get_all_users()
    ALL_STARBOARD_POSTS = get_all_starboard_posts()
    number_of_starboard_posts = len(ALL_STARBOARD_POSTS)
    for emoji in bot.emojis:
      config["all_emoji"].append(emoji.name)
    #logger.info(client.emojis) -- save this for later, surely we can do something with all these emojis
    #logger.info(f"ALL_STARBOARD_POSTS:\n{ALL_STARBOARD_POSTS}")

    # Print AGIMUS ANSI Art
    agimus_ascii = []
    with open('data/ascii/agimus.txt') as f:
      agimus_ascii = f.readlines()
    logger.info(''.join(agimus_ascii))
    logger.info(f"{Fore.LIGHTMAGENTA_EX}BOT IS ONLINE AND READY FOR COMMANDS!{Fore.RESET}")
    logger.info(f"{Fore.LIGHTRED_EX}CURRENT NUMBER OF STARBOARD POSTS:{Fore.RESET}{Style.BRIGHT} {Fore.BLUE}{number_of_starboard_posts}{Fore.RESET}{Style.RESET_ALL}")

    # Set a fun random presence
    random_presences = [
      { 'name': "PRAISE THE FOUNDERS", 'type': discord.ActivityType.listening },
      { 'name': "The Greatest Generation", 'type': discord.ActivityType.listening },
      { 'name': "The Greatest Discovery", 'type': discord.ActivityType.listening },
      { 'name': "A Nice Game of Chess", 'type': discord.ActivityType.playing },
      { 'name': "Thermonuclear War", 'type': discord.ActivityType.playing },
      { 'name': "Dials", 'type': discord.ActivityType.playing },
      { 'name': "The Stream At Home", 'type': discord.ActivityType.watching },
      { 'name': "and waiting...", 'type': discord.ActivityType.watching },
      { 'name': "Terminator 2: Judgement Day", 'type': discord.ActivityType.watching }
    ]
    selected_presence = random.choice(random_presences)
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(name=selected_presence['name'], type=selected_presence['type']))
  except Exception as e:
    logger.info(f"Error in on_ready: {e}")
    logger.info(traceback.format_exc())


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

# Listen to channel updates
@bot.event
async def on_guild_channel_create(channel):
  await show_channel_creation_message(channel)

@bot.event
async def on_guild_channel_delete(channel):
  await show_channel_deletion_message(channel)

@bot.event
async def on_guild_channel_update(before, after):
 await show_channel_rename_message(before, after)
 await show_channel_topic_change_message(before, after)

# listen to application (slash) command events
@bot.event
async def on_application_command(ctx):
  # Register user if they haven't been previously
  if int(ctx.author.id) not in ALL_USERS:
    logger.info(f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}New User{Style.RESET_ALL}{Fore.RESET}")
    ALL_USERS.append(register_player(ctx.author))

@bot.event
async def on_application_command_error(ctx, exception):
  logger.error(f"{Fore.RED}Error encountered in slash command: /{ctx.command}")
  logger.info(exception)

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
