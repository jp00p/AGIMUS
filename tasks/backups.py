from common import *

def backups_task(client):
  
  async def backups():
    enabled = config["tasks"]["backups"]["enabled"]
    if not enabled:
      return
    commit_base_url = "https://github.com/Friends-of-DeSoto/database/commit/"  
    log_channel = client.get_channel(config["channels"]["bot-logs"])
    logger.info("Running automated backup!")
    hashes = run_make_backup()
    logger.info(f"Backup complete, new hash: {hashes['new']}")
    embed = discord.Embed(
      title=f"AUTOMATED BACKUP {hashes['new']} COMPLETE",
      color=discord.Color.random(),
      description="",
      url=f"{commit_base_url}{hashes['new']}"
    )
    embed.add_field(name="🌟 NEW HASH 🌟", value=f"`{hashes['new']}`", inline=False)
    embed.add_field(name="GitHub URL to new commit", value=f"{commit_base_url}{hashes['new']}", inline=False)
    await log_channel.send(embed=embed)

  return {
    "task": backups,
    "crontab": config["tasks"]["backups"]["crontab"]
  }