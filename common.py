import asyncio
import json
import io
import logging
import math
import os
import random
import re
import textwrap
import string
import subprocess
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone, timedelta
from pprint import pprint

import aiomysql
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
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps, ImageEnhance, ImageFilter, ImageChops, ImageSequence
from tabulate import tabulate
from treys import Card, Deck, Evaluator, evaluator
from typing import List, Dict

#from utils.broadcast_logs import BroadcastHandler
from utils.config_utils import get_config, deep_dict_update
from utils.thread_utils import to_thread
#from utils.disco_lights import LightHandler

# ThreadPool for image generation tasks
from concurrent.futures import ThreadPoolExecutor
cpu_workers = max(1, os.cpu_count() - 1)
# cpu_workers = 24
THREAD_POOL = ThreadPoolExecutor(max_workers=cpu_workers)


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
# logger.addHandler(BroadcastHandler())
# logger.addHandler(LightHandler())
LOG = []

# Set Config and Globals
config = get_config()
tmdb.API_KEY = os.getenv('TMDB_KEY')

ALL_STARBOARD_POSTS = {}
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


# Role Helpers
def get_role_ids_list(role_list):
  role_list = list(role_list)
  role_list.sort()
  role_ids = []
  for x in role_list:
    id = get_role_id(x)
    role_ids.append(id)
  return role_ids

def get_role_id(role_identifier):
  if isinstance(role_identifier, str):
    id = config["role_map"].get(role_identifier)
  else:
    id = role_identifier
  return id

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
async def get_user(discord_id:int):
  async with AgimusDB(dictionary=True) as query:
    # get user basic info
    sql = """
      SELECT
        users.*,
        profile_photos.photo AS profile_photo,
        profile_taglines.tagline AS profile_tagline
      FROM users
        LEFT JOIN profile_taglines ON profile_taglines.user_discord_id = users.discord_id
        LEFT JOIN profile_photos ON profile_photos.user_discord_id = users.discord_id
      WHERE users.discord_id = %s
    """
    vals = (discord_id,)
    await query.execute(sql, vals)
    user_data = await query.fetchone()
    if user_data:
      # get user stickers
      sql = "SELECT sticker, position FROM profile_stickers WHERE user_discord_id = %s AND sticker IS NOT NULL"
      vals = (discord_id,)
      await query.execute(sql, vals)
      user_stickers = await query.fetchall()
      # get user featured badges
      sql = "SELECT badge_filename FROM profile_badges WHERE user_discord_id = %s AND badge_filename IS NOT NULL"
      vals = (discord_id,)
      await query.execute(sql, vals)
      user_badges = await query.fetchall()
      # close db
      user_data["stickers"] = user_stickers
      user_data["badges"] = user_badges
      logger.debug(f"USER DATA: {user_data}")
  return user_data


# get_all_users()
# This function takes no arguments
# and returns a list of all user discord ids
async def get_all_users():
  async with AgimusDB(dictionary=True) as query:
    await query.execute("SELECT discord_id FROM users")
    users = []
    for user in await query.fetchall():
      users.append(int(user["discord_id"]))
  return users


# register_user(user)
# user[required]: object
# This function will insert a new user into the database
async def register_user(user):
  async with AgimusDB() as query:
    sql = "INSERT INTO users (discord_id, name, mention) VALUES (%s, %s, %s)"
    vals = (user.id, user.display_name, user.mention)
    await query.execute(sql, vals)
    logger.info(f"{Style.BRIGHT}Registering user to DB:{Style.RESET_ALL} {user.id} {user.display_name} {user.mention}")
  return int(user.id)

# update_user(discord_id, key, value)
# discord_id[required]: int
# key[required]: string
# value[required]: string
# This function will update a specific value for a specific user
async def update_user(discord_id, key, value):
  modifiable = ["score", "spins", "jackpots", "wager", "high_roller", "xp", "level", "profile_photo", "profile_sticker_1"]
  if key not in modifiable:
    logger.error(f"{Fore.RED}{key} not in {modifiable}{Fore.RESET}")
  else:
    async with AgimusDB() as query:
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
      elif key == "level":
        sql = "UPDATE users SET level = %s WHERE discord_id = %s"
      vals = (value, discord_id)
      await query.execute(sql, vals)

# set_player_score(user, amt)
# user[required]: object
# amt[required]: int
# This function increases a player's score by the value amt
# NOTE: THIS IS USED BY MULTIPLE GAMES!
async def set_player_score(user, amt):
  async with AgimusDB() as query:
    sql = "SELECT score FROM users WHERE discord_id = %s"
    if type(user) is str:
      vals = (user,)
    else:
      vals = (user.id,)
    await query.execute(sql, vals)
    player_score = await query.fetchone()
    updated_amt = max(player_score[0] + amt, 0)
    if type(user) is str:
      sql = "UPDATE users SET score = %s WHERE discord_id = %s"
      vals = (updated_amt, user)
    else:
      sql = "UPDATE users SET score = %s, name = %s WHERE discord_id = %s"
      vals = (updated_amt, user.display_name, user.id)
    await query.execute(sql, vals)


# win_jackpot(winner, id)
# winner[required]: string
# id[required]: int
# This function will set the current jackpot winner
# and reset the jackpot with a default value
async def win_jackpot(winner, id):
  async with AgimusDB() as query:
    # update current jackpot row with winning data
    sql = "UPDATE jackpots SET winner=%s, time_won=NOW() ORDER BY id DESC LIMIT 1"
    vals = (winner,)
    await query.execute(sql, vals)
    new_jackpot = "INSERT INTO jackpots (jackpot_value) VALUES (250)"
    await query.execute(new_jackpot)
    update_this_user = "UPDATE users SET jackpots = jackpots + 1 WHERE discord_id = %s"
    user_vals = (id,)
    await query.execute(update_this_user, user_vals)

# increase_jackpot(amt)
# amt[required]: int
# This function increases the current jackpot value
# by the value passed as an arugument
async def increase_jackpot(amt):
  async with AgimusDB() as query:
    sql = "UPDATE jackpots SET jackpot_value = jackpot_value + %s ORDER BY id DESC LIMIT 1"
    vals = (amt,)
    await query.execute(sql, vals)

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

# generate_local_role_map(client)
# client[required]: discord.Bot
# This runs to apply the local role map (name to id) on top of the existing role map config
def generate_local_role_map(client):
  if client.guilds[0]:
    roles = client.guilds[0].roles
    role_map = {}
    for role in roles:
      role_name = role.name.encode("ascii", errors="ignore").decode().strip()
      role_map[role_name] = role.id
    # role_map_json = json.dumps(role_map, indent=2, sort_keys=True)
    updated_role_map = deep_dict_update({ "role_map": config['role_map'] }, { "role_map" : role_map })
    config["role_map"] = updated_role_map["role_map"]

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
async def run_make_backup():
  backup_info = {"url": "", "backup_name":""}
  os.system("make db-backup --no-print-directory")
  raw_new_backup = []
  with os.popen("make db-get-latest-backup --no-print-directory") as line:
    raw_new_backup = line.readlines()
    backup_info["backup_name"] = raw_new_backup[-1].replace("\n", "")
    raw_presigned_url = []
  with os.popen("make db-get-latest-backup-download-url --no-print-directory") as line:
    raw_presigned_url = line.readlines()
    backup_info["url"] = raw_presigned_url[-1].replace("\n", "")
  return backup_info

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

def remove_emoji(s: str) -> str:
  """
  Cleans out values unprintable in our font.  cp1252 because there are a handful of chars in the font not in latin_1
  """
  return s.replace("€", '').encode("cp1252", errors="ignore").decode("cp1252").strip()


IRREGULAR_MEM_ALPHA_LINKS = None

def make_memory_alpha_link(name: str) -> str:
  """
  Convert the name of this person/ship/tech into a link to https://memory-alpha.fandom.com.  There are exceptions, and
  they are stored in characters_mem_alpha_links.json.  But it’s still better
  """
  global IRREGULAR_MEM_ALPHA_LINKS
  if IRREGULAR_MEM_ALPHA_LINKS is None:
    with open("data/characters_mem_alpha_links.json") as f:
      IRREGULAR_MEM_ALPHA_LINKS = json.load(f)

  if name.startswith("A "):
    return name
  if name in IRREGULAR_MEM_ALPHA_LINKS:
    link = IRREGULAR_MEM_ALPHA_LINKS[name]
    if link:  # can be null if no link exists
      return f"[{name}]({link})"
    else:
      return name
  link_name = re.sub(r'".*" ', '', name) if '"' in name else name  # "nicknames" are not included in the links
  return f"[{name}](https://memory-alpha.fandom.com/wiki/{link_name.replace(' ', '_')})"
