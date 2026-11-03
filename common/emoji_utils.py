import random

import discord
from colorama import Fore, Style

from common.config_utils import config
from common.logs import logger


def get_emoji(emoji_name: str) -> discord.Emoji | str:
  """Return a configured emoji by name or a default emoji."""
  emoji = config["all_emoji"].get(emoji_name)
  if not emoji:
    logger.info(f"Emoji: {Fore.LIGHTWHITE_EX}{Style.BRIGHT}{emoji_name}{Style.RESET_ALL}{Fore.RESET} not found, falling back to default bot emoji")
    emoji = random.choice(["🤖", "👽", "🛠"])
  return emoji
