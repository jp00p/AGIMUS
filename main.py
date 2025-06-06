#  █████   ██████  ██ ███    ███ ██    ██ ███████
# ██   ██ ██       ██ ████  ████ ██    ██ ██
# ███████ ██   ███ ██ ██ ████ ██ ██    ██ ███████
# ██   ██ ██    ██ ██ ██  ██  ██ ██    ██      ██
# ██   ██  ██████  ██ ██      ██  ██████  ███████
from common import *
import aiohttp

# Slash Commands
from commands.aliases import aliases
from commands.bless import bless
from commands.curse import curse
from commands.dice import dice
from commands.dustbuster import dustbuster
from commands.fmk import fmk
from commands.food_war import food_war
#from commands.gifbomb import gifbomb
from commands.help import help
from commands.episode_info import episode_info
from commands.levelcheck import levelcheck
from commands.nasa import nasa
from commands.nextep import nextep, nexttrek
from commands.peptalk import peptalk
from commands.reports import reports
from commands.scores import scores
from commands.setwager import setwager
from commands.shimoda import shimoda
from commands.speak import speak, speak_embed
from commands.spongebob import spongebob
from commands.sub_rosa import sub_rosa
from commands.trekduel import trekduel
from commands.trektalk import trektalk
from commands.tuvix import tuvix
from commands.user_tags import tag_user, untag_user, display_tags
# from commands.wrapped import wrapped
# from commands.xpinfo import xpinfo_channels, xpinfo_activity

# Slash Command Groups
import commands.birthday
import commands.clip
import commands.drop

# Bang
from commands.clear_media import clear_media
from commands.ping import ping
from commands.q import qget, qset
from commands.update_status import update_status

# Prompts
from commands.computer import computer

# Cogs
if config["DEBUG"]:
  from cogs.debug import Debug
  bot.add_cog(Debug(bot))

from cogs.admin import Admin
from cogs.backups import Backups
from cogs.badges import Badges
from cogs.badge_tags import BadgeTags
from cogs.chaoszork import ChaosZork, HitchHikers
from cogs.crystals import Crystals
from cogs.poker import Poker
from cogs.profile import Profile
from cogs.quiz import Quiz
from cogs.settings import Settings
from cogs.shop import Shop
from cogs.slots import Slots
from cogs.tongo import Tongo
from cogs.trade import Trade
from cogs.randomep import RandomEp
from cogs.wishlists import Wishlist
from cogs.wordcloud import Wordcloud
bot.add_cog(Admin(bot))
bot.add_cog(Backups(bot))
bot.add_cog(Badges(bot))
bot.add_cog(BadgeTags(bot))
bot.add_cog(ChaosZork(bot))
bot.add_cog(Crystals(bot))
bot.add_cog(HitchHikers(bot))
bot.add_cog(Poker(bot))
bot.add_cog(Profile(bot))
bot.add_cog(Quiz(bot))
bot.add_cog(RandomEp(bot))
bot.add_cog(Settings(bot))
bot.add_cog(Shop(bot))
bot.add_cog(Slots(bot))
bot.add_cog(Tongo(bot))
bot.add_cog(Trade(bot))
bot.add_cog(Wishlist(bot))
bot.add_cog(Wordcloud(bot))
if config["roles"]["reaction_roles_enabled"]:
  from cogs.react_roles import ReactRoles
  bot.add_cog(ReactRoles(bot))

## Trivia relies on an external JSON request which might fail, in that case log the error but continue
try:
  from cogs.trivia import Trivia
  bot.add_cog(Trivia(bot))
except (aiohttp.client_exceptions.ContentTypeError, aiohttp.client_exceptions.ClientConnectorError, json.decoder.JSONDecodeError) as e:
  logger.error(f"{Fore.RED}<! ERROR: Trivia Failed on Import, unable to register cog. !> {e}{Fore.RESET}")
  pass

# Handlers
from handlers.alerts import handle_alerts
from handlers.bot_autoresponse import handle_bot_affirmations
from handlers.crystalsbot import handle_crystalsbot
from handlers.loudbot import handle_loudbot
from handlers.reply_restricted import handle_reply_restricted
from handlers.save_message import save_message_to_db
from handlers.server_logs import *
from handlers.starboard import db_get_all_starboard_posts, handle_starboard_reactions
from handlers.xp import handle_event_creation_xp, handle_message_xp, handle_react_xp

# Utils
from utils.check_channel_access import perform_channel_check
from utils.image_utils import preload_image_assets
from utils.exception_logger import setup_exception_logging, exception_report_task, exception_log_lines

# Tasks
from tasks.backups import backups_task
from tasks.bingbong import bingbong_task
from tasks.birthdays import birthdays_task
from tasks.hoodiversaries import hoodiversary_task
from tasks.scheduler import Scheduler
from tasks.weyounsday import weyounsday_task
# from tasks.wrapped_generation import wrapped_generation_task


background_tasks = set() # for non-blocking tasks
logger.info(f"{Style.BRIGHT}{Fore.LIGHTRED_EX}ENVIRONMENT VARIABLES AND COMMANDS LOADED{Fore.RESET}{Style.RESET_ALL}")

DB_IS_SEEDED = False
ALL_USERS = {}

@bot.event
async def on_ready():
  try:
    # Generate Local Channels and Roles
    bot.current_guild = bot.guilds[0]
    # generate local channels list
    generate_local_channel_list(bot)
    # generate local roles map
    generate_local_role_map(bot)

    # With Asynchronous DB we now seed the db and set up ALL_USERS here
    try:
      global DB_IS_SEEDED
      if not DB_IS_SEEDED:
        logger.info(f"{Style.BRIGHT}{Fore.LIGHTMAGENTA_EX}CONNECTING TO DATABASE...{Fore.RESET}{Style.RESET_ALL}")

        # Use legacy mysql.connector for this so we can execute the seed as multi-statement
        db = mysql.connector.connect(
          host=DB_HOST,
          user=DB_USER,
          database=DB_NAME,
          password=DB_PASS,
        )
        q = db.cursor(buffered=True)
        with open(DB_SEED_FILEPATH, 'r') as f:
          seed = f.read()
          q.execute(seed, multi=True)
        q.close()
        db.close()

        DB_IS_SEEDED = True
        logger.info(f"{Style.BRIGHT}{Fore.LIGHTGREEN_EX}DATABASE CONNECTION SUCCESSFUL!{Fore.RESET}{Style.RESET_ALL}")
    except Exception as e:
      logger.error(f"Error during DB Seeding: {e}")
      logger.info(traceback.format_exc())

    global ALL_USERS
    if not ALL_USERS:
      ALL_USERS = dict.fromkeys(await get_all_users(), True) # used for registering new users without a db lookup

    logger.info(f"{Back.LIGHTRED_EX}{Fore.LIGHTWHITE_EX} LOGGED IN AS {bot.user} {Fore.RESET}{Back.RESET}")
    logger.info(f"{Back.RED}{Fore.LIGHTWHITE_EX} CURRENT ASSIGNMENT: {bot.guilds[0].name} (COMPLEMENT: {len(ALL_USERS)}) {Fore.RESET}{Back.RESET}")

    global ALL_STARBOARD_POSTS
    ALL_STARBOARD_POSTS = await db_get_all_starboard_posts()
    number_of_starboard_posts = sum([len(ALL_STARBOARD_POSTS[p]) for p in ALL_STARBOARD_POSTS])
    for emoji in bot.emojis:
      config["all_emoji"][emoji.name] = emoji

    # Preload commonly used image assets into memory (badge icons, etc)
    await preload_image_assets()

    # Print AGIMUS ANSI Art
    print_agimus_ansi_art()

    logger.info(f"{Fore.LIGHTMAGENTA_EX}BOT IS ONLINE AND READY FOR COMMANDS!{Fore.RESET}")
    logger.info(f"{Fore.LIGHTRED_EX}CURRENT NUMBER OF STARBOARD POSTS:{Fore.RESET}{Style.BRIGHT} {Fore.BLUE}{number_of_starboard_posts}{Fore.RESET}{Style.RESET_ALL}")

    # Set a fun random presence
    random_presences = [
      { 'name': "PRAISE THE FOUNDERS", 'type': discord.ActivityType.listening },
      { 'name': "The Greatest Generation", 'type': discord.ActivityType.listening },
      { 'name': "The Greatest Discovery", 'type': discord.ActivityType.listening },
      { 'name': "The Greatest Trek", 'type': discord.ActivityType.listening },
      { 'name': "A Nice Game of Chess", 'type': discord.ActivityType.playing },
      { 'name': "Thermonuclear War", 'type': discord.ActivityType.playing },
      { 'name': "Gauges", 'type': discord.ActivityType.playing },
      { 'name': "The Stream At Home", 'type': discord.ActivityType.watching },
      { 'name': "and waiting...", 'type': discord.ActivityType.watching },
      { 'name': "Terminator 2: Judgement Day", 'type': discord.ActivityType.watching }
    ]
    selected_presence = random.choice(random_presences)
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(name=selected_presence['name'], type=selected_presence['type']))
  except Exception as e:
    logger.info(f"Error in on_ready: {e}")
    logger.info(traceback.format_exc())

# listens to every message on the server that the bot can see
@bot.event
async def on_message(message:discord.Message):
  # Ignore all messages from any bot
  if message.author == bot.user or message.author.bot:
    return

  try:
    # Process commands that use the command_prefix
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
    await handle_crystalsbot(message)
    await handle_loudbot(message)
    await handle_alerts(message)
    await handle_reply_restricted(message)
  except Exception as e:
    logger.error(f"{Fore.RED}<! ERROR: Encountered error in handlers !> {e}{Fore.RESET}")
    logger.error(traceback.format_exc())

  try:
    await handle_message_xp(message)
  except Exception as e:
    logger.error(f"{Fore.RED}<! ERROR: Failed to process message for xp !> {e}{Fore.RESET}")
    logger.error(traceback.format_exc())

  # "computer:" Prompt Message Handling
  if any(message.content.lower().startswith(x) for x in ["computer:"]): # We've removed 'AGIMUS:' but may add other message handling in the future
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
  if message.content.lower().startswith("agimus:"):
    user_command = "agimus"
  elif message.content.lower().startswith("computer:"):
    user_command = "computer"

  # If the user's first word matches one of the commands in configuration
  if user_command in config["commands"].keys():
    # Check enabled
    #logger.info(f"Parsed command: {Fore.LIGHTBLUE_EX}{user_command}{Fore.RESET}")
    if config["commands"][user_command]["enabled"]:
      # Check Channel Access Restrictions
      access_granted = await perform_channel_check(message, config["commands"][user_command])
      logger.info(f"Access granted? {Fore.LIGHTGREEN_EX}{access_granted}{Fore.RESET}")
      if access_granted:
        logger.info(f"Firing command: {Fore.LIGHTGREEN_EX}{user_command}{Fore.RESET}")
        try:
          await eval(user_command + "(message)")
        except SyntaxError as s:
          logger.info(f"ERROR WITH EVAL: {Fore.RED}{s}{Fore.RESET}")
          logger.info(traceback.format_exc())
    else:
      logger.error(f"{Fore.RED}<! ERROR: This function has been disabled: '{user_command}' !>{Fore.RESET}")
  else:
    logger.error(f"{Fore.RED}<! ERROR: Unknown command !>{Fore.RESET}")

# listen to typing events
@bot.event
async def on_typing(channel, user, when):
  global ALL_USERS
  # Register user if they haven't been previously
  if not ALL_USERS.get(int(user.id)):
    logger.info(f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}New User{Style.RESET_ALL}{Fore.RESET}")
    ALL_USERS[await register_user(user)] = True

# listen to reactions
@bot.event
async def on_raw_reaction_add(payload):
  if payload.event_type == "REACTION_ADD":
    await handle_starboard_reactions(payload)
    try:
      channel = bot.get_channel(payload.channel_id)
      if not channel:
        channel = await bot.fetch_channel(payload.channel_id)
      message = await channel.fetch_message(payload.message_id)
      user = payload.member or await bot.fetch_user(payload.user_id)
      # Use string comparison to match emoji properly
      reaction = next(
        (r for r in message.reactions if str(r.emoji) == str(payload.emoji)),
        None
      )
      if reaction and user:
        await handle_react_xp(reaction, user)
    except Exception as e:
      logger.warning(f"on_raw_reaction_add error: {e}")
      raise


# listen to sceheduled event updates (streams, pub trivia, etc)
@bot.event
async def on_scheduled_event_update(before: discord.ScheduledEvent, after: discord.ScheduledEvent):
  # Only award XP when the event starts
  if before.status != after.status and after.status == discord.ScheduledEventStatus.active:
    await handle_event_creation_xp(after)

# listen to server join/leave events
@bot.event
async def on_member_join(member):
  global ALL_USERS
  # Register user if they haven't been previously
  if not ALL_USERS.get(int(member.id)):
    logger.info(f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}New User{Style.RESET_ALL}{Fore.RESET}")
    ALL_USERS[await register_user(member)] = True

@bot.event
async def on_member_remove(member):
  await show_leave_message(member)

# listen to nickname change events
@bot.event
async def on_member_update(memberBefore, memberAfter):
  if memberBefore.nick != memberAfter.nick:
    await show_nick_change_message(memberBefore, memberAfter, "server")

@bot.event
async def on_user_update(userBefore, userAfter):
  if userBefore.discriminator != userAfter.discriminator:
    return
  elif userBefore.display_name != userAfter.display_name:
    await show_nick_change_message(userBefore, userAfter, "Discord")

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
async def on_application_command_error(ctx, error):
  # This prevents any commands with local handlers being handled here in on_command_error.
  if hasattr(ctx.command, 'on_error'):
      return

  # This prevents any cogs with an overwritten cog_command_error being handled here.
  cog = ctx.cog
  if cog:
      if cog._get_overridden_method(cog.cog_command_error) is not None:
          return
  if isinstance(error, discord.errors.CheckFailure):
    # We don't care about check errors,
    # it means the check is succeeding in blocking access
    pass
  else:
    tb_str = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    exception_log_lines.append(tb_str)

    # Also print to terminal
    # sys.__stderr__.write(tb_str)
    # sys.__stderr__.flush()

    logger.error(f"{Fore.RED}Error encountered in slash command: /{ctx.command}")
    logger.info(traceback.print_exception(type(error), error, error.__traceback__))

# listen to context (!) command events
@bot.event
async def on_command_error(ctx, error):
  # This prevents any commands with local handlers being handled here in on_command_error.
  if hasattr(ctx.command, 'on_error'):
      return
  # This prevents any cogs with an overwritten cog_command_error being handled here.
  cog = ctx.cog
  if cog:
      if cog._get_overridden_method(cog.cog_command_error) is not None:
          return
  if isinstance(error, discord.errors.CheckFailure):
    # We don't care about check errors,
    # it means the check is succeeding in blocking access
    pass
  else:
    logger.error(f"{Fore.RED}Error encountered in ! command: !{ctx.command}")
    logger.info(traceback.print_exception(type(error), error, error.__traceback__))


# Schedule Tasks
scheduled_tasks = [
  backups_task(bot),
  bingbong_task(bot),
  birthdays_task(bot),
  exception_report_task(bot),
  hoodiversary_task(bot),
  weyounsday_task(bot),
  # wrapped_generation_task(bot)
]
scheduler = Scheduler()
for task in scheduled_tasks:
  scheduler.add_task(task["task"], task["crontab"])
scheduler.start()

# Engage!
setup_exception_logging()
bot.run(DISCORD_TOKEN)
