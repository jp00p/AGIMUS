import logging
import random
import re
import requests
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

  hue = Hue(bridge_ip=bridge_ip, username=bridge_user)

class LightHandler(logging.Handler):
  def emit(self, record):
      """
      Show a random color when a log message comes through
      """

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

      light.set_color(hue=random.randint(1,65535), transition=3)
           
      # b.set_light(light_name, "xy", (random.random(), random.random()))

      # log_line = record.getMessage()
      # split = split_ANSI(log_line)

      # col = split.get("col")
      # if not col:
      #   return

      # ansi_matches = re.findall(r"(\d+)m", col)
      # ansi_number = 0
      # for match in ansi_matches:
      #   ansi_number += int(match)
      # rgb = get_rgb_from_ansi(int(ansi_number))
      # xy = get_xy_from_rgb(*rgb)
      # bri = int(xy[1]*255)

      # if not b.get_light(light_name, 'on'):
      #   return

      # command = {"transitiontime:": 0, "xy": xy, "bri": bri}
      # b.set_light(light_name, command)


# ANSI Methods
def get_rgb_from_ansi(ansi_number):
  index_R = ((ansi_number - 16) // 36)
  rgb_R = 55 + index_R * 40 if index_R > 0 else 0
  index_G = (((ansi_number - 16) % 36) // 6)
  rgb_G = 55 + index_G * 40 if index_G > 0 else 0
  index_B = ((ansi_number - 16) % 6)
  rgb_B = 55 + index_B * 40 if index_B > 0 else 0

  # Convert to floats
  fR = rgb_R / 255
  fG = rgb_G / 255
  fB = rgb_B / 255

  return [fR, fG, fB]

split_ANSI_escape_sequences = re.compile(r"""
    (?P<col>(\x1b     # literal ESC
    \[       # literal [
    [;\d]*   # zero or more digits or semicolons
    [A-Za-z] # a letter
    )*)
    (?P<name>.*)
    """, re.VERBOSE).match

def split_ANSI(s):
    return split_ANSI_escape_sequences(s).groupdict()

# xy methods
def get_xy_from_rgb(red, green, blue):
    # gamma correction
    red = pow((red + 0.055) / (1.0 + 0.055), 2.4) if red > 0.04045 else (red / 12.92)
    green = pow((green + 0.055) / (1.0 + 0.055), 2.4) if green > 0.04045 else (green / 12.92)
    blue =  pow((blue + 0.055) / (1.0 + 0.055), 2.4) if blue > 0.04045 else (blue / 12.92)

    # convert rgb to xyz
    x = red * 0.649926 + green * 0.103455 + blue * 0.197109
    y = red * 0.234327 + green * 0.743075 + blue * 0.022598
    z = green * 0.053077 + blue * 1.035763

    # convert xyz to xy
    x = x / (x + y + z)
    y = y / (x + y + z)
     
    return [x, y]
