import asyncio
import json
import logging
import os
import random
import re
import string
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pprint import pprint

import dateutil.parser
import discord
import humanize
import mysql.connector
import numpy as np
import requests
import tmdbsimple as tmdb
import treys
from colorama import Back, Fore, Style
from discord import option
from discord.ext import commands, tasks, pages
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps
from tabulate import tabulate
from treys import Card, Deck, Evaluator, evaluator

from utils.broadcast_logs import BroadcastHandler
from utils.config_utils import get_config, deep_dict_update
from utils.disco_lights import LightHandler


#   _________       __
#  /   _____/ _____/  |_ __ ________
#  \_____  \_/ __ \   __\  |  \____ \
#  /        \  ___/|  | |  |  /  |_> >
# /_______  /\___  >__| |____/|   __/
#         \/     \/           |__|

# Load variables from .env file
load_dotenv()

LOG_LEVEL = os.getenv('LOG_LEVEL')
if not LOG_LEVEL:
  LOG_LEVEL = "INFO"
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(BroadcastHandler())
logger.addHandler(LightHandler())
LOG = []

# Set Config and Globals
config = get_config()
tmdb.API_KEY = os.getenv('TMDB_KEY')

ALL_STARBOARD_POSTS = []
BOT_NAME = f"{Fore.LIGHTRED_EX}AGIMUS{Fore.RESET}"
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TMDB_IMG_PATH = "https://image.tmdb.org/t/p/original"
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_SEED_FILEPATH = os.getenv('DB_SEED_FILEPATH')
ROLES = config["roles"]
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
from utils.database import AgimusDB

# __________        __
# \______   \ _____/  |_
#  |    |  _//  _ \   __\
#  |    |   (  <_> )  |
#  |______  /\____/|__|
#         \/

intents = discord.Intents.all()
bot = commands.Bot(
  intents=intents,
  test_guilds=config["guild_ids"],
  auto_sync_commands=True,
  command_prefix="!"
)

# Channel Helpers
def get_channel_ids_list(channel_list):
  channel_list = list(channel_list)
  channel_list.sort()
  channel_ids = []
  for x in channel_list:
    id = get_channel_id(x)
    channel_ids.append(id)
  return channel_ids

def get_channel_id(channel_identifier):
  if isinstance(channel_identifier, str):
    id = config["channels"].get(channel_identifier)
  else:
    id = channel_identifier
  return id

# Channel Globals
DEV_CHANNEL = get_channel_id(config["dev_channel"])
INTRO_CHANNEL = get_channel_id(config["intro_channel"])
LOGGING_CHANNEL = get_channel_id(config["logging_channel"])
SERVER_LOGS_CHANNEL = get_channel_id(config["server_logs_channel"])


# ________          __        ___.
# \______ \ _____ _/  |______ \_ |__ _____    ______ ____
#  |    |  \\__  \\   __\__  \ | __ \\__  \  /  ___// __ \
#  |    `   \/ __ \|  |  / __ \| \_\ \/ __ \_\___ \\  ___/
# /_______  (____  /__| (____  /___  (____  /____  >\___  >
#         \/     \/          \/    \/     \/     \/     \/

def getDB():
  """Legacy DB connector, use `AgimusDB()` instead!"""
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_NAME,
    password=DB_PASS,
  )
  return db

# seed_db()
# This function takes no arguments
# and is used to seed the database if the tables
# described in the file at $DB_SEED_FILEPATH (.env var)
# If there is no jackpot row, it will also seed that table
# with an opening pot of 250
def seed_db():
  # Seed db structure if it doesn't exist
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASS,
  )
  with open(DB_SEED_FILEPATH, 'r') as f:
    seed = f.read()
  c = db.cursor(buffered=True)
  c.execute(seed, multi=True)
  db.close()
  db = getDB()
  # If the jackpot table is empty, set an initial pot value to 250
  query = db.cursor(dictionary=True)
  query.execute("SELECT count(id) as total_jackpots from jackpots limit 1")
  data = query.fetchone()
  if data["total_jackpots"] == 0:
    logger.info(f"{Fore.GREEN}SEEDING JACKPOT{Fore.RESET}")
    insert = db.cursor()
    insert.execute("INSERT INTO jackpots (jackpot_value) VALUES (250)")
    db.commit()
    insert.close()
  db.close()

def is_integer(n):
  try:
    float(n)
  except ValueError:
    return False
  else:
    return float(n).is_integer()

# uniq_channels(config)
# This function compiles a list of all of the unique channels
# used in all commands described in the configuration object
def uniq_channels(config):
  tkeys = []
  for key in config["channels"].keys():
    tkeys = tkeys + config["channels"][key]
  res = []
  [res.append(int(x)) for x in tkeys if x not in res]
  return res


# get_user(discord_id)
# discord_id[required]: int
# This function will return a user's record from their id
def get_user(discord_id:int):
  with AgimusDB(cursor_dict=True) as query:
    # get user basic info
    sql = "SELECT users.*, profile_photos.photo as photo, profile_taglines.tagline as tagline FROM users LEFT JOIN profile_taglines ON profile_taglines.user_discord_id = users.discord_id LEFT JOIN profile_photos ON profile_photos.user_discord_id = users.discord_id WHERE discord_id = %s"
    vals = (discord_id,)
    query.execute(sql, vals)
    user_data = query.fetchone()
    # get user stickers
    sql = "SELECT sticker, position FROM profile_stickers WHERE user_discord_id = %s AND sticker IS NOT NULL"
    vals = (discord_id,)
    query.execute(sql, vals)
    user_stickers = query.fetchall()
    # get user featured badges
    sql = "SELECT badge_filename FROM profile_badges WHERE user_discord_id = %s AND badge_filename IS NOT NULL"
    vals = (discord_id,)
    query.execute(sql, vals)
    user_badges = query.fetchall()
    # close db
    user_data["stickers"] = user_stickers
    user_data["badges"] = user_badges
    logger.debug(f"USER DATA: {user_data}")
  return user_data


# get_all_users()
# This function takes no arguments
# and returns a list of all user discord ids
def get_all_users():
  with AgimusDB(cursor_dict=True) as query:
    query.execute("SELECT discord_id FROM users")
    users = []
    for user in query.fetchall():
      users.append(int(user["discord_id"]))
  return users


# register_player(user)
# user[required]: object
# This function will insert a new user into the database
def register_user(user):
  with AgimusDB() as query:
    sql = "INSERT INTO users (discord_id, name, mention) VALUES (%s, %s, %s)"
    vals = (user.id, user.display_name, user.mention)
    query.execute(sql, vals)
    logger.info(f"{Style.BRIGHT}Registering user to DB:{Style.RESET_ALL} {user.id} {user.display_name} {user.mention}")
  return int(user.id)

# update_user(discord_id, key, value)
# discord_id[required]: int
# key[required]: string
# value[required]: string
# This function will update a specific value for a specific user
def update_user(discord_id, key, value):
  modifiable = ["score", "spins", "jackpots", "wager", "high_roller", "xp", "profile_photo", "profile_sticker_1"]
  if key not in modifiable:
    logger.error(f"{Fore.RED}{key} not in {modifiable}{Fore.RESET}")
  else:
    with AgimusDB() as query:
      if key == "score":
        sql = "UPDATE users SET score = %s WHERE discord_id = %s"
      elif key == "spins":
        sql = "UPDATE users SET spins = %s WHERE discord_id = %s"
      elif key == "jackpots":
        sql = "UPDATE users SET jackpots = %s WHERE discord_id = %s"
      elif key == "wager":
        sql = "UPDATE users SET wager = %s WHERE discord_id = %s"
      elif key == "high_roller":
        sql = "UPDATE users SET high_roller = %s WHERE discord_id = %s"
      elif key == "profile_photo":
        sql = "UPDATE users SET profile_photo = %s WHERE discord_id = %s"
      elif key == "profile_sticker_1":
        sql = "UPDATE users SET profile_sticker_1 = %s WHERE discord_id = %s"
      elif key == "xp":
        sql = "UPDATE users SET xp = %s WHERE discord_id = %s"
      vals = (value, discord_id)
      query.execute(sql, vals)

# set_player_score(user, amt)
# user[required]: object
# amt[required]: int
# This function increases a player's score by the value amt
# NOTE: THIS IS USED BY MULTIPLE GAMES!
def set_player_score(user, amt):
  with AgimusDB() as query:
    sql = "SELECT score FROM users WHERE discord_id = %s"
    if type(user) is str:
      vals = (user,)
    else:
      vals = (user.id,)
    query.execute(sql, vals)
    player_score = query.fetchone()
    updated_amt = max(player_score[0] + amt, 0)
    if type(user) is str:
      sql = "UPDATE users SET score = %s WHERE discord_id = %s"
      vals = (updated_amt, user)
    else:
      sql = "UPDATE users SET score = %s, name = %s WHERE discord_id = %s"
      vals = (updated_amt, user.display_name, user.id)
    query.execute(sql, vals)


# win_jackpot(winner, id)
# winner[required]: string
# id[required]: int
# This function will set the current jackpot winner
# and reset the jackpot with a default value
def win_jackpot(winner, id):
  with AgimusDB() as query:
    # update current jackpot row with winning data
    sql = "UPDATE jackpots SET winner=%s, time_won=NOW() ORDER BY id DESC LIMIT 1"
    vals = (winner,)
    query.execute(sql, vals)
    new_jackpot = "INSERT INTO jackpots (jackpot_value) VALUES (250)"
    query.execute(new_jackpot)
    update_this_user = "UPDATE users SET jackpots = jackpots + 1 WHERE discord_id = %s"
    user_vals = (id,)
    query.execute(update_this_user, user_vals)

# increase_jackpot(amt)
# amt[required]: int
# This function increases the current jackpot value
# by the value passed as an arugument
def increase_jackpot(amt):
  with AgimusDB() as query:
    sql = "UPDATE jackpots SET jackpot_value = jackpot_value + %s ORDER BY id DESC LIMIT 1"
    vals = (amt,)
    query.execute(sql, vals)
  
# generate_local_channel_list(client)
# client[required]: discord.Bot
# This runs to apply the local channel list on top of the existing channel config
def generate_local_channel_list(client):
  if client.guilds[0]:
    channels = client.guilds[0].channels + client.guilds[0].threads + client.guilds[0].voice_channels + client.guilds[0].forum_channels
    channel_list = {}
    for channel in channels:
      channel_name = channel.name.encode("ascii", errors="ignore").decode().strip()
      channel_list[channel_name] = channel.id
    # channel_list_json = json.dumps(channel_list, indent=2, sort_keys=True)
    updated_channel_list = deep_dict_update({ "channels": config['channels'] }, { "channels" : channel_list })
    config["channels"] = updated_channel_list["channels"]

# get_emoji(emoji_name)
# emoji_name[required]: str
# get an emoji by name
# will fail softly if emoji doesn't exist on the server!
def get_emoji(emoji_name:str):
  emoji = config["all_emoji"].get(emoji_name)
  if not emoji:
    logger.info(f"Emoji: {Fore.LIGHTWHITE_EX}{Style.BRIGHT}{emoji_name}{Style.RESET_ALL}{Fore.RESET} not found, falling back to default bot emoji")
    emoji = random.choice(["🤖", "👽", "🛠"])
  return emoji

# run_make_backup()
# util function that runs our `make db-backup` command
# returns the new hash from git
def run_make_backup():
  hashes = { "old":"", "new":"" }
  raw_new_hash = []
  os.system("make db-backup")
  with os.popen("cd database && git rev-parse HEAD") as line:
    raw_new_hash = line.readlines()
  hashes["new"] = raw_new_hash[-1].replace("\n", "")
  return hashes

# returns a pretend stardate based on the given datetime
def calculate_stardate(date:datetime.date):
  # calculate the stardate
  stardate = date.year * 100 + date.month * 10 + date.day
  # calculate the stardate offset
  stardate_offset = (date.year - 2300) * 365 + (date.year - 2300) // 4 + (date.month - 1) * 30 + date.day
  # calculate the stardate
  stardate += stardate_offset
  return stardate

def print_agimus_ansi_art():
  agimus_ansi = []
  ansi_file = random.choice(os.listdir("data/ansi/"))
  with open(f"data/ansi/{ansi_file}") as f:
    agimus_ansi = f.readlines()
  logger.info(''.join(agimus_ansi))
