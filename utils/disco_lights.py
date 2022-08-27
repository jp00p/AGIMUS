import logging
import random
import re
import requests
from pprint import pprint
from urllib3.exceptions import InsecureRequestWarning
from huesdk import Hue # https://pypi.org/project/huesdk/

from utils.config_utils import get_config

# supress insecure request warning for this
# this is because the connection to the Hue bridge is insecure and requests gets cranky
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

config = get_config()
lights_config = config.get("lights")

if lights_config:
  bridge_ip = lights_config.get("bridge_ip") # https://discovery.meethue.com/ get your IP
  bridge_user = lights_config.get("hue_username") # see below
  lights_mode = lights_config.get("lights_mode")
  ###
  # make a tiny file with this in it:
  # ----------------------------------
  # from huesdk import Hue
  # username = Hue.connect(bridge_ip=YOUR_BRIDGE_IP)
  # print(f"HUE USERNAME: {username}")
  # ----------------------------------
  # press your hue bridge button
  # then run your tiny file
  # you will get a username to use for your config file
  ###



class LightHandler(logging.Handler):
  def emit(self, record):
      """
      Show a random color when a log message comes through
      """

      if not lights_config:
        return

      hue = Hue(bridge_ip=bridge_ip, username=bridge_user)

      if not hue:
        return

      target_light_name = lights_config.get("light_name")

      if not target_light_name:
        return

      log_line = record.getMessage()

      if "*" not in log_line:
        return

      light = hue.get_light(name=target_light_name)

      if not light.is_on:
        return

      if lights_mode == "match_logs":
        print(f"lights_mode: {lights_mode}")
        hex = get_hex_from_logline(log_line)
        light.set_color(hexa=hex, transition=3)
        light.set_saturation(254)
      else:
        light.set_color(hue=random.randint(1,65535), transition=3)

#    _____    _______    _________.___
#   /  _  \   \      \  /   _____/|   |
#  /  /_\  \  /   |   \ \_____  \ |   |
# /    |    \/    |    \/        \|   |
# \____|__  /\____|__  /_______  /|___|
#         \/         \/        \/
split_ANSI_escape_sequences = re.compile(r"""
  (?P<col>(\x1b # literal ESC
  \[            # literal [
  [;\d]*        # zero or more digits or semicolons
  [A-Za-z]      # a letter
  )*)
  (?P<name>.*)
  """, re.VERBOSE).match

def split_ANSI(s):
  return split_ANSI_escape_sequences(s).groupdict()


# _________        .__
# \_   ___ \  ____ |  |   ___________
# /    \  \/ /  _ \|  |  /  _ \_  __ \
# \     \___(  <_> )  |_(  <_> )  | \/
#  \______  /\____/|____/\____/|__|
#         \/
LOW_TO_RGB = {
  "30": (46, 52, 55),    # Grey
  "31": (205, 59, 40),   # Red
  "32": (78, 154, 9),    # Green
  "33": (196, 161, 36),  # Yellow
  "34": (52, 101, 164),  # Blue
  "35": (117, 80, 123),  # Magenta
  "36": (64, 153, 155),  # Cyan
  "37": (211, 215, 207), # Reset
  "38": (211, 215, 207), # Reset
  "39": (211, 215, 207), # Reset
}

HIGH_TO_RGB = {
  "92": (208, 98, 101),  # Light Red
  "93": (0, 245, 146),   # Light Green
  "94": (225, 229, 0),   # Light Yellow
  "95": (153, 149, 210), # Light Blue
  "95": (237, 97, 230),  # Magenta
  "96": (164, 73, 166),  # Light Magenta
  "97": (0, 248, 255)    # Light Cyan
}

def get_hex_from_logline(msg):
  split = split_ANSI(msg)
  col = split.get("col")
  if not col:
    return "#dddddd"

  ansi_matches = re.findall(r"(\d+)m", col)
  ansi_number = 0
  for match in ansi_matches:
    ansi_number += int(match)
    if ansi_number >= 30 and ansi_number <= 39:
      break

  hex = _get_hex_from_ansi(ansi_number)
  return hex

def _get_hex_from_ansi(ansi):
  ansi = int(ansi)
  if ansi >= 30 and ansi <= 39:
    rgb = LOW_TO_RGB.get(str(ansi))
  else:
    rgb = HIGH_TO_RGB.get(str(ansi))

  if rgb is None:
    rgb = (211, 215, 207)

  return _get_hex_from_rgb(rgb)

def _get_hex_from_rgb(rgb):
  return '%02x%02x%02x' % rgb
