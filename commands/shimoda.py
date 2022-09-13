from common import *

class ShimodaModal(discord.ui.Modal):
  def __init__(self, *args, **kwargs) -> None:
    super().__init__(
      discord.ui.InputText(
          label="Character",
          placeholder="Which Character?",
      ),
      discord.ui.InputText(
        label="Reason",
        style=discord.InputTextStyle.long,
      ),
      *args,
      **kwargs,
    )

  async def callback(self, interaction:discord.Interaction):
    member = await bot.current_guild.fetch_member(interaction.user.id)
    pollster_embed = discord.Embed(
      title="New Shimoda Nomination",
      description=f"{member.mention} has nominated a new Drunk Shimoda!",
      fields=[
        discord.EmbedField(name="Character", value=self.children[0].value, inline=False),
        discord.EmbedField(name="Reason", value=self.children[1].value, inline=False)
      ],
      color=discord.Color.random()
    )
    roles = await bot.current_guild.fetch_roles()
    pollster_role = None
    for r in roles:
      if r.name == config['roles']['shimoda_pollsters']:
        pollster_role = r

    recipients = pollster_role.members
    for recipient in recipients:
      await recipient.send(embed=pollster_embed)

    nominator_embed = discord.Embed(
      title="Drunk Shimoda Nomination Successfully Sent!",
      color=discord.Color.green(),
      fields=[
        discord.EmbedField(name="Character", value=self.children[0].value, inline=False),
        discord.EmbedField(name="Reason", value=self.children[1].value, inline=False)
      ]
    )

    await interaction.response.send_message(embed=nominator_embed, ephemeral=True)


@bot.slash_command(
  name="shimoda",
  description="Nominate a character for an episode's Drunk Shimoda poll!"
)
async def shimoda(ctx:discord.ApplicationContext):
  modal = ShimodaModal(title="Drunk Shimoda Nomination")
  await ctx.send_modal(modal)
