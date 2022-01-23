import discord
from discord.ext import tasks
import os
import random
import tmdbsimple as tmdb
import requests
import asyncio
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

# Load variables from .env file
load_dotenv()

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL'))
handler = logging.StreamHandler(sys.stdout)
# handler.setLevel(logging.INFO)
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
BOT_CONFIGURATION_FILEPATH = os.getenv('BOT_CONFIGURATION_FILEPATH')
f = open(BOT_CONFIGURATION_FILEPATH)
config = json.load(f)
f.close()
client = discord.Client()
POKER_GAMES = {}
TRIVIA_RUNNING = False
TRIVIA_DATA = {}
TRIVIA_MESSAGE = None
TRIVIA_ANSWERS = {}
EMOJI = {}

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
    logger.info("SEEDING JACKPOT")
    insert = db.cursor()
    insert.execute("INSERT INTO jackpots (jackpot_value) VALUES (250)")
    db.commit()
    insert.close()
  db.close()


# uniq_channels(config)
# This function compiles a list of all of the unique channels
# used in all commands described in the configuration object
def uniq_channels(config):
  tkeys = []
  for key in config["commands"].keys():
    tkeys = tkeys + config["commands"][key]["channels"]
  res = []
  [res.append(int(x)) for x in tkeys if x not in res]
  return res


# get_player(discord_id)
# discord_id[required]: int
# This function will return a user's record from their id
def get_player(discord_id:int):
  db = getDB()
  query = db.cursor(dictionary=True)
  query.execute("SELECT * FROM users WHERE discord_id = %s", (discord_id,))
  player_data = query.fetchone()
  query.close()
  db.close()
  return player_data


# get_all_players()
# This function takes no arguments
# and returns a list of all user discord ids
def get_all_players():
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
  global ALL_PLAYERS
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO users (discord_id, name, mention) VALUES (%s, %s, %s)"
  vals = (user.id, user.display_name, user.mention)
  query.execute(sql, vals)
  logger.info("Registering user to DB: {} {} {}".format(user.id, user.display_name, user.mention))
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
  logger.info(f"Updating user {discord_id} with new card: {card}")
  db = getDB()
  query = db.cursor()
  sql = "UPDATE users SET profile_card = %s WHERE discord_id = %s"
  vals = (card, discord_id)
  query.execute(sql, vals)
  db.commit()
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
  update_user = "UPDATE users SET jackpots = jackpots + 1 WHERE discord_id = %s"
  user_vals = (id,)
  query.execute(update_user, user_vals)
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

