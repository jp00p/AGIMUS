from common import *
from handlers.xp import increment_user_xp
from utils.check_channel_access import access_check

from bs4 import BeautifulSoup
import re
import requests
import time


class ChaosZork(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.started = False

    self.zork_url = 'http://www.web-adventures.org/cgi-bin/webfrotz'
    self.status_re = re.compile(r'<p.*>(.(?!</p>))+\s*</p>(?P<response>(.(?!(&gt;|</td>)))+)\s*(&gt;|</td>)')
    self.x = f"desoto{time.time()}"

    # Initialize
    self.send_command('look')

  @commands.slash_command(
    name="zork",
    description="Send a command to the Zork game!"
  )
  @option(
    name="input",
    description="What is your text input?",
    required=True
  )
  @commands.check(access_check)
  async def zork(self, ctx:discord.ApplicationContext, cmd:str):
    await ctx.defer()

    await increment_user_xp(ctx.author, 1, "played_zork", ctx.channel)

    game_text = ""

    if cmd == 'quit' or cmd == 'reset' or cmd == 'restart':
      self.reset()
      game_text = self.find_statuses(self.send_command('look'))[-1]
    else:
      game_text = self.find_statuses(self.send_command(cmd))[-1]

    game_text = self.dedupe(game_text)
    game_text = "> {}\n\n{}".format(cmd, game_text.replace('     ', '\n')).replace('    ', '\n')

    await ctx.respond(f"```{game_text}```")

  def send_command(self, cmd: str):
    resp = requests.post(self.zork_url, data={'a': cmd, 'x': self.x, 's': 'ZorkDungeon'})
    return resp

  def format_status(self, s: str) -> str:
    return s.replace('<br/>', '  ').strip(' \n').replace('<b>', '').replace('</b>', '').replace('</erd@infinet.com>', '')

  def find_statuses(self, resp):
    s = resp.content
    soup = BeautifulSoup(s, 'html.parser')
    r = soup.find_all('td')[1].prettify().replace('\n', '').replace('<font', '\n<font').replace('</td', ' </td')
    return [self.format_status(d[1]) for d in self.status_re.findall(r)]

  def reset(self):
    resp = self.send_command('look')
    soup = BeautifulSoup(resp.content, 'html.parser')
    links = soup.find_all('a')
    reset_link = [l['href'] for l in links if l.text == 'restart']
    n = int(reset_link[0][reset_link[0].rfind('=') + 1:])
    requests.post(
      self.zork_url,
      data={'s': 'ZorkDungeon', 'x': self.x, 'n': n}
    )
    self.x = n

  def dedupe(self, game_text):
    replace_text = """Welcome to ZORK.
Release 12 / Serial number 990623 / Inform v6.14 Library 6/7

  WEST OF HOUSE
This is an open field west of a white house, with a boarded front door.
There is a small mailbox here.
A rubber mat saying 'Welcome to Zork!' lies by the door.
"""
    if "Welcome to ZORK." in game_text:
      game_text = replace_text

    return game_text
