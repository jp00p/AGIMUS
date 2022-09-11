import os
import queue
import re
import subprocess
import threading
from typing import AnyStr, IO, List

import discord
from discord.ext import commands
from discord import option

from handlers.xp import increment_user_xp
from utils.check_channel_access import access_check


class DfrotzRunner(commands.Cog):
  """
  This will open up the dfrotz z-machine interpreter and allow for an in-out game session as long as it is running.

  You will need to set game_name and game_file_name for it to work properly.  Some things are done with the zdungeon
  file in mind, so you may want to override other functions to get things working.  Also, to get ansi working you have
  to build V 2.52.  2.54 is broken.
  """

  game_name: str
  game_file_name: str

  file_path = os.path.abspath(os.path.join(__file__, '../../data/zfiles'))

  def __init__(self, bot):
    self.bot = bot
    self.save_file = os.path.join(self.file_path, self.game_name + '.qzl')

    self.queue: queue.Queue = None
    self.queue_thread: threading.Thread = None
    self.process: subprocess.Popen = None

  def start_process(self):
    """Start the dfrotz process"""
    if self.process:
      return

    self.queue = queue.Queue()
    self.process = subprocess.Popen(self.get_dfrotz_args(), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    self.queue_thread = threading.Thread(target=self.enqueue, args=(self.process.stdout, self.queue))
    self.queue_thread.daemon = True
    self.queue_thread.start()

    self.clean_startup()

  def get_dfrotz_args(self) -> List[str]:
    args = ['dfrotz',
            '-f', 'ansi',  # For the pretty formatting
            '-h', '1000',  # So we don't get [MORE] messages
            '-R', self.file_path,  # keep out of the rest of the system
            '-Z', '0']  # supress errors
    if os.path.exists(self.save_file):
      args.append('-L')
      args.append(self.save_file)

    args.append(os.path.join(self.file_path, self.game_file_name))
    return args

  def enqueue(self, outfile: IO[AnyStr], q: queue.Queue):
    """Run in a background thread, read each line as it comes in and add it to the queue"""
    for line in iter(outfile.readline, b''):
      q.put(line)
    outfile.close()

  def clean_startup(self):
    """There are two lines to clean at first saying "Using ANSI formatting." and "Loading game_file_name" """
    self.queue.get()
    self.queue.get()

  def get_from_queue(self) -> List[str]:
    """Get everything from the stdout queue as a list"""
    lines = []
    while True:
      try:
        line = self.queue.get(timeout=1).decode()
      except queue.Empty:
        break
      else:
        lines.append(line)
    return lines

  def send_output(self, cmd: str):
    self.process.stdin.write((cmd + '\n').encode())
    self.process.stdin.flush()

  def run_command(self, cmd: str) -> str:
    self.send_output(cmd)

    lines = self.get_from_queue()

    lines = self.clean_lines(lines)

    lines = '\x1b[0m\n'.join(lines)
    return f"```ansi\n\x1b[0;36m> {cmd}\x1b[0m\n{lines}\n```"

  def clean_lines(self, lines: List[str]) -> List[str]:
    cleaned_lines = []
    for line in lines:
      if line[0] == '>':
        line = line.lstrip(' >')
      if line[0] == '\x1b':
        continue  # Opening escape sequences break everything
      line = line.replace('\x1b[0K', '')  # Most lines end with this, and I don't know what it does
      line = line[2:]  # Most lines start with a two character sillyness that doesn't make sense
      line = line.rstrip()
      cleaned_lines.append(line)

    blank_line = re.compile(r'^\s*$')
    while blank_line.match(cleaned_lines[0]):
      del cleaned_lines[0]
    while blank_line.match(cleaned_lines[-1]):
      del cleaned_lines[-1]

    return cleaned_lines

  async def save(self, ctx: discord.ApplicationContext):
    self.send_output('save')
    self.send_output(self.save_file)
    self.send_output('yes')
    # flush the output
    self.get_from_queue()

    embed = discord.Embed(
      title="Saving game",
      description="Game successfully saved.  You will return to this point any time AGIMUS restarts or you use the "
                  "RESTORE command.",
      color=discord.Color.blue()
    )
    await ctx.followup.send(embed=embed)

  async def load(self, ctx: discord.ApplicationContext):
    if not os.path.exists(self.save_file):
      await ctx.followup.send(embed=discord.Embed(
        title="Restoring game",
        description="There is no saved game",
        color=discord.Color.red()
      ))
      return

    self.send_output('restore')
    self.send_output(self.save_file)
    # flush the output
    self.get_from_queue()

    embed = discord.Embed(
      title="Restoring game",
      description="Continuing from the last save",
      color=discord.Color.blue()
    )
    await ctx.followup.send(embed=embed)

  async def quit(self, ctx: discord.ApplicationContext):
    await ctx.followup.send(embed=discord.Embed(
      title="Don't be silly!",
      description="You can’t quit now!  There’s so much to do.",
      color=discord.Color.red()
    ))

  async def slash_command(self, ctx: discord.ApplicationContext, cmd: str):
    """
    This should be the starting point for the commands
    """
    await ctx.defer()
    self.start_process()
    cmd = cmd.strip()

    if cmd.lower() == 'save':
      return await self.save(ctx)
    if cmd.lower() == 'restore':
      return await self.load(ctx)
    if cmd.lower() == 'quit':
      return await self.quit(ctx)

    await increment_user_xp(ctx.author, 1, "played_zork", ctx.channel)

    output = self.run_command(cmd)
    if len(output) > 2000:
      current_output = ''
      for line in output.splitlines(keepends=True):
        if line[:3] == '```':
          continue
        if len(current_output) + len(line) + 12 > 2000:
          await ctx.channel.send(f"```ansi\n{current_output}\n```")
          current_output = ''
        current_output += line
      await ctx.respond(f"```ansi\n{current_output}\n```")
    else:
      await ctx.respond(output)


class ChaosZork(DfrotzRunner):
  game_name = 'zork'
  game_file_name = 'zdungeon.z5'

  @commands.slash_command(
    name="zork",
    description="Play Zork!"
  )
  @option(
    name="input",
    description="What do you want to do next?",
    required=True
  )
  @commands.check(access_check)
  async def zork(self, ctx: discord.ApplicationContext, cmd: str):
    await self.slash_command(ctx, cmd)
