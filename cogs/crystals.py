from common import *

from queries.badge_info import *
from queries.badge_instances import *
from queries.crystals import *
from utils.badge_utils import *
from utils.crystal_effects import apply_crystal_effect
from utils.thread_utils import to_thread

class Crystals(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  async def autocomplete_user_badge_instances(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id
    badge_instances = await db_get_user_badge_instances(user_id)
    choices = [
      b['badge_name'] for b in badge_instances
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

    badge_instance = await db_get_badge_instance_by_badge_info_id(user_id, badge_info['id'])
    if not badge_instance:
      return []

    crystals = await db_get_attached_crystals(badge_instance['badge_instance_id'])
    return ['[None]'] + [
      f"{c['emoji']} {c['crystal_name']}" if c.get('emoji') else c['crystal_name']
      for c in crystals if ctx.value.lower() in c['crystal_name'].lower()
    ][:25]

  crystals_group = discord.SlashCommandGroup("crystals", "Badge Crystal Management.")

  @crystals_group.command(name='install', description='Select which crystal to display for one of your badges.')
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
  async def install(self, ctx: discord.ApplicationContext, badge_name: str, crystal_name: str):
    await ctx.defer(ephemeral=True)
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

    badge_instance = await db_get_badge_instance_by_badge_info_id(user_id, badge_info['id'])
    if not badge_instance:
      embed = discord.Embed(
        title='Badge Not Owned!',
        description=f"You don't own the **{badge_name}** badge.",
        color=discord.Color.red()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    crystals = await db_get_attached_crystals(badge_instance['badge_instance_id'])

    if crystal_name.lower() == '[none]':
      if badge_instance.get('active_crystal_id') is None:
        embed = discord.Embed(
          title='Already Unistalled!',
          description=f"No crystal is currently installed in **{badge_name}**.",
          color=discord.Color.orange()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

      # Look up which crystal was previously installed
      previous = next(
        (c for c in crystals if c['badge_crystal_id'] == badge_instance['active_crystal_id']),
        None
      )
      prev_label = f"{previous['emoji']} {previous['crystal_name']}" if previous else "Unknown Crystal"

      await db_set_active_crystal(badge_instance['badge_instance_id'], None)
      embed = discord.Embed(
        title='Crystal Removed',
        description=f"Uninstalled **{prev_label}** from **{badge_name}**.",
        color=discord.Color.green()
      )
      await ctx.respond(embed=embed, ephemeral=True)  # ← This was missing!
      return


    selected = next(
      (c for c in crystals if crystal_name.lower() in f"{c.get('emoji', '')} {c['crystal_name']}".lower()),
      None
    )

    if not selected:
      embed = discord.Embed(
        title='Crystal Not Found!',
        description=f"No crystal named **{crystal_name}** found on **{badge_name}**.",
        color=discord.Color.red()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    if badge_instance.get('active_crystal_id') == selected['crystal_type_id']:
      embed = discord.Embed(
        title='Already Installed!',
        description=f"**{crystal_name}** is already your installed crystal in **{badge_name}**.",
        color=discord.Color.orange()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    # Generate badge preview image with crystal effect (in-memory)
    base_image = await load_and_prepare_badge_thumbnail(badge_info['badge_filename'])
    badge = { **badge_info, 'badge_instance_id': badge_instance['badge_instance_id'] }
    crystal = selected
    discord_file, attachment_url = await generate_badge_preview_discord_file(base_image, badge, crystal=crystal)

    crystal_description = crystal.get('description', '')
    crystal_label = f"{crystal['emoji']} {crystal['crystal_name']}" if crystal.get('emoji') else crystal['crystal_name']

    preview_embed = discord.Embed(
      title=f"Crystallization Preview",
      description=f"Here's what **{badge_name}** would look like with *{crystal['crystal_name']}* applied.",
      color=discord.Color.blurple()
    )
    preview_embed.add_field(name=f"{crystal['crystal_name']}", value=f"{crystal_description}", inline=False)
    preview_embed.add_field(name=f"Rank", value=f"{crystal['emoji']} {crystal['rarity_name']}", inline=False)
    preview_embed.set_footer(text="Click Confirm to install this crystal, or Cancel.")
    preview_embed.set_image(url=attachment_url)

    # View placed here to have access to outer scope
    class ConfirmCancelView(discord.ui.View):
      def __init__(self):
        super().__init__(timeout=60)

      async def on_timeout(self):
        for child in self.children:
          child.disabled = True
        if self.message:
          await self.message.edit(view=self)

      @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
      async def confirm(self, button, interaction):
        await db_set_active_crystal(badge_instance['badge_instance_id'], selected['badge_crystal_id'])
        embed = discord.Embed(
          title='Crystal Installed ✅',
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

    # Sending response here
    view = ConfirmCancelView()
    await ctx.respond(embed=preview_embed, file=discord_file, view=view, ephemeral=True)
    view.message = await ctx.interaction.original_response()


async def generate_badge_preview_discord_file(base_image, badge, crystal=None):
  preview_result = await apply_crystal_effect(base_image, badge, crystal=crystal)

  if isinstance(preview_result, list):
    # Animated crystal preview
    tmp = tempfile.NamedTemporaryFile(suffix=".webp", delete=False)
    await encode_webp(preview_result, tmp.name)
    file = discord.File(tmp.name, filename=f"preview.webp")
    tmp.flush()
    # buffer = io.BytesIO()
    # preview_result[0].save(
    #   buffer,
    #   format='WEBP',
    #   save_all=True,
    #   append_images=preview_result[1:],
    #   duration=1000 // 12,
    #   loop=0,
    #   lossless=True,
    #   method=6,
    #   optimize=True
    # )
    # buffer.seek(0)
    # file = discord.File(webp, filename='preview.webp')
    attachment_url = 'attachment://preview.webp'
  else:
    buffer = io.BytesIO()
    preview_result.save(buffer, format='PNG')
    buffer.seek(0)
    file = discord.File(buffer, filename='preview.png')
    attachment_url = 'attachment://preview.png'

  return file, attachment_url