from common import *

class UpdateBadges(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.repo_base_url = f"https://github.com/{os.getenv('REPO_OWNER')}/{os.getenv('REPO_NAME')}"

  # update_badges() - Entrypoint for /update_badges command
  # ctx: discord.ApplicationContext
  # will run the badge update make command and report back the PR URL to merge
  # admins only
  @commands.slash_command(
    name="update_badges",
    description="Run the badge updater! (ADMIN ONLY)"
  )
  @commands.has_permissions(administrator=True)
  async def update_badges(self, ctx:discord.ApplicationContext):
    await ctx.defer()

    result = run_make_badger()

    log_channel = self.bot.get_channel(config["channels"]["bot-logs"])
    chunk_length = 3000
    log_chunks = [result['log'][i:i+chunk_length] for i in range(0, len(result['log']), chunk_length)]
    for idx, chunk in enumerate(log_chunks):
      log_embed = discord.Embed(
        title=f"Badge Update Log [{idx + 1} of {len(log_chunks)}]",
        color=discord.Color.blurple(),
        description=f"`{chunk}`"
      )
      await log_channel.send(embed=log_embed)

    if not result['completed']:
      if result['error']:
        embed = discord.Embed(
          title=f"Badge Update Error!",
          color=discord.Color.red(),
          description=f"`{result['error']}`",
        )
      else:
        embed = discord.Embed(
          title=f"Badge Update Unnecessary!",
          color=discord.Color.random(),
          description="🚫 No new badges found, no update needed! 🚫",
        )
    else:
      pull_request_url = f"{self.repo_base_url}/pull/new/badge_updates/{result['version']}"
      embed = discord.Embed(
        title=f"Badge Update Branch Created!",
        color=discord.Color.random(),
        description="",
        url=pull_request_url
      )
      embed.add_field(name="🌟 NEW BADGE UPDATE VERSION 🌟", value=f"`{result['version']}`", inline=False)
      embed.add_field(name="GitHub URL to create PR", value=pull_request_url, inline=False)

    await ctx.respond(embed=embed, ephemeral=False)
