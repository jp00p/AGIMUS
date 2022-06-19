import discord
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option
from discord.ext import tasks
import os
import random
import tmdbsimple as tmdb
import requests
import asyncio
import re
import string
import json
from PIL import Image, ImageFont, ImageDraw, ImageColor
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
import mysql.connector
from tabulate import tabulate
import treys
from treys import evaluator
import numpy as np
from treys import Card, Evaluator, Deck
import logging
import sys
from colorama import Fore, Back, Style

from utils.config_utils import get_config

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
LOG = []

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TMDB_IMG_PATH = "https://image.tmdb.org/t/p/original"
tmdb.API_KEY = os.getenv('TMDB_KEY')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_SEED_FILEPATH = os.getenv('DB_SEED_FILEPATH')
config = get_config()
client = discord.Client()
slash = SlashCommand(client, sync_commands=True)
POKER_GAMES = {}
TRIVIA_RUNNING = False
TRIVIA_DATA = {}
TRIVIA_MESSAGE = None
TRIVIA_ANSWERS = {}
EMOJI = {}
ROLES = config["roles"]

# Channel Helpers
def get_channel_ids_list(channel_list):
  channel_ids = []
  for x in channel_list:
    id = get_channel_id(x)
    channel_ids.append(id)
  return channel_ids

def get_channel_id(channel):
  if isinstance(channel, str):
    id = config["channels"].get(channel)
  else:
    id = channel
  return id

INTRO_CHANNEL = get_channel_id(config["intro_channel"])
LOGGING_CHANNEL = get_channel_id(config["logging_channel"])
DEV_CHANNEL = get_channel_id(config["dev_channel"])

# Database Functions
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


# get_player(discord_id)
# discord_id[required]: int
# This function will return a user's record from their id
def get_player(discord_id:int):
  logger.debug(f"Running: {Style.BRIGHT}{Fore.LIGHTGREEN_EX}get_player({discord_id}){Fore.RESET}{Style.RESET_ALL}")
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

