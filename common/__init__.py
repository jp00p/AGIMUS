import json
import os
import random
import re
from concurrent.futures import ThreadPoolExecutor

import discord
from colorama import Fore, Style

from common.channel_utils import get_channel_id, get_channel_ids_list
from common.config_utils import config
from common.discord_bot import bot
from common.role_utils import get_role_id, get_role_ids_list
from common.db import get_user, get_all_users, register_user, update_user
from common.logs import logger


cpu_workers = max(1, os.cpu_count() - 1)
# cpu_workers = 24
THREAD_POOL = ThreadPoolExecutor(max_workers=cpu_workers)

#   _________       __
#  /   _____/ _____/  |_ __ ________
#  \_____  \_/ __ \   __\  |  \____ \
#  /        \  ___/|  | |  |  /  |_> >
# /_______  /\___  >__| |____/|   __/
#         \/     \/           |__|


BOT_NAME = f"{Fore.LIGHTRED_EX}AGIMUS{Fore.RESET}"
ROOT_DIR:str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Channel Globals
# Unless config['channels'] is populated in local-config.json, these will be None
DEV_CHANNEL = get_channel_id(config["dev_channel"])
INTRO_CHANNEL = get_channel_id(config["intro_channel"])
LOGGING_CHANNEL = get_channel_id(config["logging_channel"])
SERVER_LOGS_CHANNEL = get_channel_id(config["server_logs_channel"])


def get_emoji(emoji_name:str) -> discord.Emoji|str:
  """
  get an emoji by name
  will fail softly if emoji doesn't exist on the server!
  """
  emoji = config["all_emoji"].get(emoji_name)
  if not emoji:
    logger.info(f"Emoji: {Fore.LIGHTWHITE_EX}{Style.BRIGHT}{emoji_name}{Style.RESET_ALL}{Fore.RESET} not found, falling back to default bot emoji")
    emoji = random.choice(["🤖", "👽", "🛠"])
  return emoji


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


# I know I can't stop you from doing import *
__all__ = ["THREAD_POOL", "BOT_NAME", "ROOT_DIR", "DEV_CHANNEL", "INTRO_CHANNEL", "LOGGING_CHANNEL", "SERVER_LOGS_CHANNEL",
           "get_channel_id", "get_channel_ids_list", "get_role_id", "get_role_ids_list", "config", "bot",
           "get_user", "get_all_users", "register_user", "update_user", "logger",
           "get_emoji", "remove_emoji", "make_memory_alpha_link"]
