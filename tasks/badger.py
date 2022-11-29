from common import *

def badger_task(client):

  async def badger():
    enabled = config["tasks"]["badger"]["enabled"]
    if not enabled:
      return

    repo_base_url = f"https://github.com/{os.getenv('REPO_OWNER')}/{os.getenv('REPO_NAME')}/"
    log_channel = client.get_channel(config["channels"]["bot-logs"])
    logger.info("Running automated badge update!")

    result = run_make_badger()
    if not result['completed']:
      if result['error']:
        logger.info("Badge update error!")
        embed = discord.Embed(
          title=f"AUTOMATED BADGE UPDATE ERROR",
          color=discord.Color.red(),
          description=f"`{result['error']}`",
        )
      else:
        logger.info("Badge update unnecessary")
        embed = discord.Embed(
          title=f"AUTOMATED BADGE UPDATE UNNECESSARY",
          color=discord.Color.random(),
          description="🚫 No new badges found, no update needed! 🚫",
        )

    else:
      logger.info(f"Automated badge update branch creation complete, new version: {result['version']}")

      pull_request_url = f"{repo_base_url}/pull/new/badge_updates/{result['version']}"

      embed = discord.Embed(
        title=f"AUTOMATED BADGE UPDATE BRANCH COMPLETE",
        color=discord.Color.random(),
        description="",
        url=pull_request_url
      )
      embed.add_field(name="🌟 NEW BADGE UPDATE VERSION 🌟", value=f"`{result['version']}`", inline=False)
      embed.add_field(name="GitHub URL to create PR", value=pull_request_url, inline=False)

    await log_channel.send(embed=embed)

  return {
    "task": badger,
    "crontab": config["tasks"]["badger"]["crontab"]
  }