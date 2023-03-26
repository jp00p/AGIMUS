from common import *


class Backups(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.commit_base_url = "https://github.com/Friends-of-DeSoto/database/commit/"

    # backup_database() - Entrypoint for !backup_database command
    # ctx: discord.ApplicationContext
    # will backup the database on-demand and respond with the new github url and hash
    # admins only XXX
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def backup_database(self, ctx: discord.ApplicationContext):
        await ctx.message.delete(delay=1.0)
        await ctx.send(f"Backups running, hold your horses.")

        backup_hashes = run_make_backup()
        if not backup_hashes:
            await ctx.send(
                f"Something went wrong with the backup! No databases have been wiped out, I don't think."
            )
        else:
            embed = discord.Embed(
                title=f"BACKUP {backup_hashes['new']} COMPLETE",
                color=discord.Color.random(),
                description="You are safe, for now.",
                url=f"{self.commit_base_url}{backup_hashes['new']}",
            )
            embed.add_field(
                name="🌟 NEW HASH 🌟", value=f"`{backup_hashes['new']}`", inline=False
            )
            embed.add_field(
                name="GitHub URL to new commit",
                value=f"{self.commit_base_url}{backup_hashes['new']}",
                inline=False,
            )
            await ctx.send(embed=embed)
