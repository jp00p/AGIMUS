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
from PIL import Image, ImageColor, ImageDraw, ImageFont
from tabulate import tabulate
from treys import Card, Deck, Evaluator, evaluator

from utils.config_utils import get_config

#from utils.disco_lights import LightHandler


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
#logger.addHandler(LightHandler())
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
EMOJI = {}
EMOJIS = {}
ROLES = config["roles"]
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TRIVIA_RUNNING = False
TRIVIA_DATA = {}
TRIVIA_MESSAGE = None
TRIVIA_ANSWERS = {}

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
  command_prefix="$"
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
  logger.debug(f"Running: {Style.BRIGHT}{Fore.LIGHTGREEN_EX}get_user({discord_id}){Fore.RESET}{Style.RESET_ALL}")
  db = getDB()
  query = db.cursor(dictionary=True)
  query.execute("SELECT * FROM users WHERE discord_id = %s", (discord_id,))
  player_data = query.fetchone()
  query.close()
  db.close()
  return player_data


# get_all_users()
# This function takes no arguments
# and returns a list of all user discord ids
def get_all_users():
  db = getDB()
  query = db.cursor(dictionary=True)
  query.execute("SELECT discord_id FROM users")
  users = []
  for user in query.fetchall():
    users.append(int(user["discord_id"]))
  query.close()
  db.close()
  return users
  

# register_player(user)
# user[required]: object
# This function will insert a new user into the database
def register_player(user):
  global ALL_USERS
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO users (discord_id, name, mention) VALUES (%s, %s, %s)"
  vals = (user.id, user.display_name, user.mention)
  query.execute(sql, vals)
  logger.info(f"{Style.BRIGHT}Registering user to DB:{Style.RESET_ALL} {user.id} {user.display_name} {user.mention}")
  db.commit()
  query.close()
  db.close()
  return int(user.id)


# update_player_profile_card(discord_id, card)
# discord_id[required]: int
# card[required]: string
# This function will update the profile_card value
# for a specific user
def update_player_profile_card(discord_id, card):
  logger.info(f"Updating user {Style.BRIGHT}{discord_id}{Style.RESET_ALL} with new card: {Fore.CYAN}{card}{Fore.RESET}")
  db = getDB()
  query = db.cursor()
  sql = "UPDATE users SET profile_card = %s WHERE discord_id = %s"
  vals = (card, discord_id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()



# update_user(discord_id, key, value)
# discord_id[required]: int
# key[required]: string
# value[required]: string
# This function will update a specific value for a specific user
def update_user(discord_id, key, value):
  logger.info(f"Running: {Fore.LIGHTMAGENTA_EX}update_user({discord_id}, {key}, {value}){Fore.RESET}")
  modifiable = ["score", "spins", "jackpots", "wager", "high_roller", "chips", "xp", "profile_card", "profile_badge"]
  if key not in modifiable:
    logger.error(f"{Fore.RED}{key} not in {modifiable}{Fore.RESET}")
  else:
    logger.info(f"updating: {Fore.LIGHTMAGENTA_EX}({discord_id}, {key}, {value}){Fore.RESET}")
    db = getDB()
    query = db.cursor()
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
    elif key == "chips":
      sql = "UPDATE users SET chips = %s WHERE discord_id = %s"
    elif key == "profile_card":
      sql = "UPDATE users SET profile_card = %s WHERE discord_id = %s"
    elif key == "profile_badge":
      sql = "UPDATE users SET profile_badge = %s WHERE discord_id = %s"
    elif key == "xp":
      sql = "UPDATE users SET xp = %s WHERE discord_id = %s"
    vals = (value, discord_id)
    logger.info(f"{Fore.LIGHTYELLOW_EX}{sql}{Fore.RESET}")
    logger.info(f"{Fore.LIGHTRED_EX}{vals}{Fore.RESET}")
    query.execute(sql, vals)
    logger.info(f"{Fore.LIGHTGREEN_EX}{db.commit()}{Fore.RESET}")
    query.close()
    db.close()


# update_player_profile_badge(discord_id, badge)
# discord_id[required]: int
# badge[required]: string
# This function will update the profile_badge value
# for a specific user
def update_player_profile_badge(discord_id, badge):
  db = getDB()
  query = db.cursor()
  sql = "UPDATE users SET profile_badge = %s WHERE discord_id = %s"
  vals = (badge, discord_id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

# set_player_score(user, amt)
# user[required]: object
# amt[required]: int
# This function increases a player's score by the value amt
def set_player_score(user, amt):
  db = getDB()
  query = db.cursor()
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
  db.commit()
  query.close()
  db.close()


# win_jackpot(winner, id)
# winner[required]: string
# id[required]: int
# This function will set the current jackpot winner
# and reset the jackpot with a default value 
def win_jackpot(winner, id):
  db = getDB()
  query = db.cursor()
  # update current jackpot row with winning data
  sql = "UPDATE jackpots SET winner=%s, time_won=NOW() ORDER BY id DESC LIMIT 1"
  vals = (winner,)
  query.execute(sql, vals)
  new_jackpot = "INSERT INTO jackpots (jackpot_value) VALUES (250)"
  query.execute(new_jackpot)
  update_this_user = "UPDATE users SET jackpots = jackpots + 1 WHERE discord_id = %s"
  user_vals = (id,)
  query.execute(update_this_user, user_vals)
  db.commit()
  query.close()
  db.close()
  

# increase_jackpot(amt)
# amt[required]: int
# This function increases the current jackpot value
# by the value passed as an arugument
def increase_jackpot(amt):
  db = getDB()
  query = db.cursor()
  sql = "UPDATE jackpots SET jackpot_value = jackpot_value + %s ORDER BY id DESC LIMIT 1"
  vals = (amt,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

# generate_local_channel_list(client)
# client[required]: discord.Bot
# run this if you need a nice json list of channel names + ids for your config file
def generate_local_channel_list(client):
  if client.guilds[0]:
    channels = client.guilds[0].channels
    channel_list = {}
    for channel in channels:
      if channel.type == discord.ChannelType.text:
        channel_name = channel.name.encode("ascii", errors="ignore").decode().strip()
        channel_list[channel_name] = channel.id
    channel_list_json = json.dumps(channel_list, indent=2, sort_keys=True)
  
    try:
      with open('./local-channel-list.json', 'w') as f:
        f.write(channel_list_json)
    except FileNotFoundError as e:
      logger.info(f"{Fore.RED}Unable to create local channel list file:{Fore.RESET} {e}")
