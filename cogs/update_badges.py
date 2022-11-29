from common import *

class UpdateBadges(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.repo_base_url = f"https://github.com/{os.getenv('REPO_OWNER')}/{os.getenv('REPO_NAME')}"

  # update_badges() - Entrypoint for !update_badges command
  # ctx: discord.ApplicationContext
  # will run the badge update make command and report back the PR URL to merge
  # admins only
  @commands.command()
  @commands.has_permissions(administrator=True)
  async def update_badges(self, ctx:discord.ApplicationContext):
    await ctx.message.delete(delay=1.0)
    await ctx.send(f"Badge update running, hold onto your butts.")

    result = run_make_badger()
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

    await ctx.send(embed=embed)
