from common import *

from queries.badge_info import db_get_badge_info_by_name
from queries.badge_inventory import db_get_badge_instance
from queries.crystals import db_get_existing_crystals_for_instance, db_set_preferred_crystal
from utils.badge_utils import load_badge_image
from utils.crystal_effects import apply_crystal_effect

class Crystals(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  async def autocomplete_user_badge_instances(ctx: discord.AutocompleteContext):
    from queries.badge_inventory import db_get_user_badges

    user_id = ctx.interaction.user.id
    badges = await db_get_user_badges(user_id)
    choices = [
      b['badge_name'] for b in badges
      if b.get('badge_name') and ctx.value.lower() in b['badge_name'].lower()
    ]
    return choices[:25]

  async def autocomplete_user_badge_crystals(ctx: discord.AutocompleteContext):
    badge_name = ctx.options.get('badge_name')
    if not badge_name:
      return []

    user_id = ctx.interaction.user.id
    badge_info = await db_get_badge_info_by_name(badge_name)
    if not badge_info:
      return []

    instance = await db_get_badge_instance(user_id, badge_info['id'])
    if not instance:
      return []

    crystals = await db_get_existing_crystals_for_instance(instance['id'])
    return [
      f"{c['emoji']} {c['crystal_name']}" if c.get('emoji') else c['crystal_name']
      for c in crystals if ctx.value.lower() in c['crystal_name'].lower()
    ][:25]

  @commands.slash_command(name='slot_crystal', description='Select which crystal to display for one of your badges.')
  @option(
    'badge_name',
    str,
    description='Choose a badge from your collection',
    autocomplete=autocomplete_user_badge_instances,
    max_length=128
  )
  @option(
    'crystal_name',
    str,
    description='Choose a crystal you\'ve earned for that badge',
    autocomplete=autocomplete_user_badge_crystals,
    max_length=128
  )
  async def slot_crystal(self, ctx: discord.ApplicationContext, badge_name: str, crystal_name: str):
    user_id = ctx.user.id

    badge_info = await db_get_badge_info_by_name(badge_name)
    if not badge_info:
      embed = discord.Embed(
        title='Badge Not Found!',
        description=f"Badge **{badge_name}** not found.",
        color=discord.Color.red()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    instance = await db_get_badge_instance(user_id, badge_info['id'])
    if not instance:
      embed = discord.Embed(
        title='Badge Not Owned!',
        description=f"You don't own the **{badge_name}** badge.",
        color=discord.Color.red()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    crystals = await db_get_existing_crystals_for_instance(instance['id'])
    selected = next((c for c in crystals if crystal_name.lower() in c['crystal_name'].lower()), None)

    if not selected:
      embed = discord.Embed(
        title='Crystal Not Found!',
        description=f"No crystal named **{crystal_name}** found on **{badge_name}**.",
        color=discord.Color.red()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    if instance.get('preferred_crystal_id') == selected['id']:
      embed = discord.Embed(
        title='Already Slotted!',
        description=f"**{crystal_name}** is already your active crystal for **{badge_name}**.",
        color=discord.Color.orange()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    # Generate badge preview image with crystal effect (in-memory)
    base_image = load_badge_image(badge_info['badge_filename'])
    badge = { **badge_info, 'badge_instance_id': instance['id'] }
    crystal = selected
    preview_img = apply_crystal_effect(base_image, badge)

    buffer = io.BytesIO()
    preview_img.save(buffer, format='PNG')
    buffer.seek(0)
    file = discord.File(buffer, filename='preview.png')

    emoji = crystal.get('emoji', '')
    crystal_label = f"{emoji} {crystal_name}" if emoji else crystal_name

    preview_embed = discord.Embed(
      title=f"Preview: {badge_name} + {crystal_label}",
      description="Click **Confirm** to slot this crystal, or **Cancel** to abort.",
      color=discord.Color.blurple()
    )
    preview_embed.set_image(url="attachment://preview.png")

    class ConfirmCancelView(discord.ui.View):
      def __init__(self):
        super().__init__(timeout=60)

      @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
      async def confirm(self, button, interaction):
        await db_set_preferred_crystal(instance['id'], selected['id'])
        embed = discord.Embed(
          title='Crystal Slotted ✅',
          description=f"Set **{crystal_label}** as your preferred crystal for **{badge_name}**.",
          color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

      @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Cancelled',
          description="No changes made to your badge.",
          color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

    await ctx.respond(embed=preview_embed, file=file, view=ConfirmCancelView(), ephemeral=True)
