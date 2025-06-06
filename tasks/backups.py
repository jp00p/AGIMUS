from common import *

def backups_task(client):
  async def backups():
    enabled = config["tasks"]["backups"]["enabled"]
    if not enabled:
      return
    log_channel = client.get_channel(config["channels"]["bot-logs"])
    logger.info("Running automated backup!")
    hashes = await run_make_backup()
    logger.info(f"Backup complete, new hash: {hashes['backup_name']}")
    embed = discord.Embed(
      title=f"AUTOMATED BACKUP {hashes['backup_name']} COMPLETE",
      color=discord.Color.random(),
      description="",
      url=f"{hashes['url']}"
    )
    embed.add_field(name="🌟 NEW BACKUP 🌟", value=f"`{hashes['backup_name']}`", inline=False)
    embed.add_field(name="Presigned URL (valid 15m) to new backup", value=f"{hashes['url']}", inline=False)
    await log_channel.send(embed=embed)

  return {
    "task": backups,
    "crontab": config["tasks"]["backups"]["crontab"]
  }
