
from common import *
from handlers.xp import increment_user_xp
from utils.check_channel_access import access_check

import requests
from bs4 import BeautifulSoup
import re

class ChaosZork(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.started = False

    self.zork_url = 'http://www.web-adventures.org/cgi-bin/webfrotz'
    self.status_re = re.compile(r'<p.*>(.(?!</p>))+\s*</p>(?P<response>(.(?!(&gt;|</td>)))+)\s*(&gt;|</td>)')

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

    game_text = self.find_statuses(self.send_command(cmd))[-1]
    game_text = "> {}\n\n{}".format(cmd, game_text.replace('     ', '\n')).replace('    ', '\n')

    await ctx.respond(f"```{game_text}```")

  def send_command(self, cmd: str):
    resp = requests.post(self.zork_url, data={'a': cmd, 'x': 'usshood1701daadwef', 's': 'ZorkDungeon'})
    return resp

  def format_status(self, s: str) -> str:
    return s.replace('<br/>', '  ').strip(' \n').replace('<b>', '').replace('</b>', '').replace('</erd@infinet.com>', '')

  def find_statuses(self, resp):
    s = resp.content
    soup = BeautifulSoup(s, 'html.parser')
    r = soup.find_all('td')[1].prettify().replace('\n', '').replace('<font', '\n<font').replace('</td', ' </td')
    return [self.format_status(d[1]) for d in self.status_re.findall(r)]