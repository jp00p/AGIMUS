from common import *

class Backups(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  # backup_database() - Entrypoint for !backup_database command
  # ctx: discord.ApplicationContext
  # will backup the database on-demand and respond with the new github url and hash
  # admins only XXX
  @commands.command()
  @commands.has_permissions(administrator=True)
  async def backup_database(self, ctx:discord.ApplicationContext):
    await ctx.message.delete(delay=1.0)
    await ctx.send(f"Backups running, hold your horses.")
    backup_hashes = run_make_backup()
    if not backup_hashes:
      await ctx.send(f"Something went wrong with the backup! No databases have been wiped out, I don't think.")
    else:
      embed = discord.Embed(
        title=f"BACKUP {backup_hashes['backup_name']} COMPLETE",
        color=discord.Color.random(),
        description="You are safe, for now.",
        url=f"{backup_hashes['url']}"
      )
      embed.add_field(name="🌟 NEW BACKUP 🌟", value=f"`{backup_hashes['backup_name']}`", inline=False)
      embed.add_field(name="Presigned URL (valid 15m) to new backup", value=f"{backup_hashes['url']}", inline=False)
      await ctx.send(embed=embed)
