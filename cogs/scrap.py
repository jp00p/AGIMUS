from common import *

from queries.rematerialization import *
from queries.crystal_instances import *
from utils.crystal_instances import *

from utils.check_channel_access import access_check

scrap_group = discord.SlashCommandGroup("scrap", "Badge Scrapping and Crystal Rematerialization Commands.")

class Rematerialization(commands.Cog):
  def __init__(self, bot:commands.Bot):
    self.bot = bot

  @scrap_group.command(name="rematerialize", description="Rematerialize 10 Crystals into a Crystal of a higher rank.")
  @commands.check(access_check)
  async def rematerialize(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    user_id = ctx.user.id

    existing = await db_get_active_rematerialization(user_id)
    if existing:
      all_items = await db_get_rematerialization_items(existing['id'])
      current_total = len(all_items)

      if current_total >= 10:
        embed = discord.Embed(
          title="Rematerialization Ready!",
          description="You already have 10 Crystals contributed. Click below to finalize the Rematerialization!",
          color=discord.Color.gold()
        )

        class ConfirmResumeRematerialize(discord.ui.View):
          def __init__(self):
            super().__init__(timeout=300)

          @discord.ui.button(label="Rematerialize", style=discord.ButtonStyle.success)
          async def confirm(self, button, interaction):
            crystals_used = [item['crystal_instance_id'] for item in all_items]
            await db_mark_crystals_rematerialized(crystals_used)

            new_crystal = await db_select_random_crystal_type_by_rarity_rank(existing['target_rank_id'])
            granted = await create_new_crystal_instance(user_id, new_crystal['id'])

            await db_finalize_rematerialization(existing['id'], granted['id'])

            confirm_embed = discord.Embed(
              title="Rematerialization Complete!",
              description=f"You have received a new **{granted['name']}** Crystal!",
              color=discord.Color.green()
            )
            confirm_embed.set_footer(text=f"Rank: {new_crystal['id']} | ID: {granted['id']}")
            await interaction.response.edit_message(embed=confirm_embed, view=None)

          @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
          async def cancel(self, button, interaction):
            await interaction.response.edit_message(
              embed=discord.Embed(
                title="Canceled",
                description="No changes were made.",
                color=discord.Color.orange()
              ),
              view=None
            )

        await ctx.respond(embed=embed, view=ConfirmResumeRematerialize(), ephemeral=True)
        return

    embed = discord.Embed(
      title="Begin Rematerialization!",
      description="Choose a Rarity to select the relevant Crystals to Rematerialize below.",
      color=discord.Color.teal()
    )

    class RarityDropdown(discord.ui.View):
      def __init__(self, options):
        super().__init__(timeout=60)
        self.dropdown = discord.ui.Select(
          placeholder="Select a Crystal Rarity...",
          min_values=1,
          max_values=1,
          options=options
        )
        self.dropdown.callback = self.on_select
        self.add_item(self.dropdown)
        self.message = None

      async def on_select(self, interaction):

        self.dropdown.options = rarity_options
        selected_rarity = self.dropdown.values[0]
        rarity_info = next((r for r in rarities if r['name'] == selected_rarity), None)
        if not rarity_info:
          await interaction.response.edit_message(
            embed=discord.Embed(
              title="Invalid Selection",
              description="That Rarity selection could not be found. Please try again.",
              color=discord.Color.red()
            ),
            view=None
          )
          return

        source_rank = rarity_info['rarity_rank']
        target_rank = source_rank + 1
        rematerialization_id = await db_create_rematerialization(ctx.user.id, source_rank, target_rank)

        crystals = await db_get_unattuned_crystals_by_rarity(ctx.user.id, selected_rarity)
        if not crystals:
          await db_cancel_rematerialization(rematerialization_id)
          await interaction.response.edit_message(
            embed=discord.Embed(
              title="No Crystals Found",
              description=f"You no longer have any unattuned Crystals of Rarity **{selected_rarity}**.",
              color=discord.Color.orange()
            ),
            view=None
          )
          return

        await interaction.response.edit_message(
          embed=discord.Embed(
            title=f"{selected_rarity} Crystal Types",
            description=f"You may now select a type of Crystal from the **{selected_rarity}** Rarity to add toward Rematerialization.",
            color=discord.Color.teal()
          ),
          view=None
        )

        # Show CrystalTypeDropdown for selected_rarity
        seen = set()
        crystal_options = []
        for c in crystals:
          if c['crystal_type_id'] in seen:
            continue
          seen.add(c['crystal_type_id'])
          label = f"{c['crystal_name']} (×{c['count']})"
          crystal_options.append(discord.SelectOption(
            label=label,
            value=str(c['crystal_type_id']),
            emoji=c.get('emoji')
          ))

        class CrystalTypeDropdown(discord.ui.View):
          def __init__(self, options):
            super().__init__(timeout=60)
            self.page = 0
            self.per_page = 25
            self.options = options
            self.total_pages = (len(options) - 1) // self.per_page + 1
            self.dropdown = discord.ui.Select(
              placeholder="Choose a Crystal Type",
              min_values=1,
              max_values=1,
              options=self.options[:self.per_page]
            )
            self.dropdown.callback = self.on_select
            self.add_item(self.dropdown)

            if self.total_pages > 1:
              self.prev_button = discord.ui.Button(label="⬅ Prev", style=discord.ButtonStyle.primary, row=1)
              self.next_button = discord.ui.Button(label="Next ➡", style=discord.ButtonStyle.primary, row=1)
              self.prev_button.callback = self.prev_page
              self.next_button.callback = self.next_page
              self.add_item(self.prev_button)
              self.add_item(self.next_button)

            self.message = None

          async def on_select(self, interaction):
            crystal_type_id = int(self.dropdown.values[0])
            crystal_instances = await db_get_unattuned_crystals_by_type(ctx.user.id, crystal_type_id)
            if not crystal_instances:
              await interaction.response.send_message(
                embed=discord.Embed(
                  title="No Crystals Found",
                  description="You no longer have any unattuned Crystals of this type.",
                  color=discord.Color.orange()
                ),
                ephemeral=True
              )
              return

            max_select = min(10, len(crystal_instances))
            quantity_options = [
              discord.SelectOption(label=f"{i} Crystal{'s' if i > 1 else ''}", value=str(i))
              for i in range(1, max_select + 1)
            ]

            class QuantityDropdown(discord.ui.View):
              def __init__(self):
                super().__init__(timeout=60)
                self.dropdown = discord.ui.Select(
                  placeholder="Select how many Crystals to add",
                  min_values=1,
                  max_values=1,
                  options=quantity_options
                )
                self.dropdown.callback = self.on_select
                self.add_item(self.dropdown)
                self.message = None

              async def on_select(self, q_interaction):
                selected_count = int(self.dropdown.values[0])
                selected_crystals = crystal_instances[:selected_count]

                for crystal in selected_crystals:
                  await db_add_crystal_to_rematerialization(rematerialization_id, crystal['crystal_instance_id'])

                all_items = await db_get_rematerialization_items(rematerialization_id)
                current_total = len(all_items)

                if current_total >= 10:
                  finalize_embed = discord.Embed(
                    title="Rematerialization Ready!",
                    description="You have contributed 10 Crystals. Click below to finalize the Rematerialization and receive a new Crystal of the next Rank!",
                    color=discord.Color.gold()
                  )

                  class ConfirmRematerialize(discord.ui.View):
                    def __init__(self):
                      super().__init__(timeout=90)

                    @discord.ui.button(label="Rematerialize", style=discord.ButtonStyle.success)
                    async def confirm(self, button, interaction):
                      crystals_used = [item['crystal_instance_id'] for item in all_items]
                      await db_mark_crystals_rematerialized(crystals_used)

                      new_crystal = await db_select_random_crystal_type_by_rarity_rank(target_rank)
                      granted = await create_new_crystal_instance(ctx.user.id, new_crystal['id'])

                      await db_finalize_rematerialization(rematerialization_id, granted['id'])

                      confirm_embed = discord.Embed(
                        title="Rematerialization Complete!",
                        description=f"You have received a new **{granted['name']}** Crystal!",
                        color=discord.Color.green()
                      )
                      confirm_embed.set_footer(text=f"Rank: {new_crystal['id']} | ID: {granted['id']}")
                      await interaction.response.edit_message(embed=confirm_embed, view=None)

                    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
                    async def cancel(self, button, interaction):
                      await interaction.response.edit_message(
                        embed=discord.Embed(
                          title="Canceled",
                          description="No changes were made.",
                          color=discord.Color.orange()
                        ),
                        view=None
                      )

                  await q_interaction.followup.send(embed=finalize_embed, view=ConfirmRematerialize(), ephemeral=True)
                else:
                  await q_interaction.response.send_message(
                    embed=discord.Embed(
                      title="Crystals Added",
                      description=f"Added {selected_count} Crystal{'s' if selected_count > 1 else ''} to your Rematerialization Queue. ({current_total}/10 total)",
                      color=discord.Color.green()
                    ),
                    ephemeral=True
                  )

              async def on_timeout(self):
                for item in self.children:
                  item.disabled = True
                if self.message:
                  try:
                    await self.message.edit(view=self)
                  except discord.errors.NotFound:
                    pass

            quantity_embed = discord.Embed(
              title="Select Quantity to Add",
              description="How many Crystals of this type would you like to contribute?",
              color=discord.Color.teal()
            )
            quantity_view = QuantityDropdown()
            quantity_view.message = await interaction.followup.send(embed=quantity_embed, view=quantity_view, ephemeral=True)

          async def prev_page(self, interaction):
            if self.page > 0:
              self.page -= 1
              await self.update_dropdown(interaction)

          async def next_page(self, interaction):
            if self.page < self.total_pages - 1:
              self.page += 1
              await self.update_dropdown(interaction)

          async def update_dropdown(self, interaction):
            start = self.page * self.per_page
            end = start + self.per_page
            self.dropdown.options = self.options[start:end]
            await interaction.response.edit_message(view=self)

          async def on_timeout(self):
            for item in self.children:
              item.disabled = True
            if self.message:
              try:
                await self.message.edit(view=self)
              except discord.errors.NotFound:
                pass

        type_embed = discord.Embed(
          title=f"{selected_rarity} Crystal Types",
          description=f"Select a type of Crystal from the **{selected_rarity}** Rarity to queue for Rematerialization.",
          color=discord.Color.teal()
        )
        type_view = CrystalTypeDropdown(crystal_options)
        type_view.message = await interaction.followup.send(embed=type_embed, view=type_view, ephemeral=True)

      async def on_timeout(self):
        for item in self.children:
          item.disabled = True
        if self.message:
          try:
            await self.message.edit(view=self)
          except discord.errors.NotFound:
            pass

    rarities = await db_get_user_unattuned_crystal_rarities(ctx.user.id)
    all_ranks = await db_get_all_crystal_rarity_ranks()
    max_rank = max(r['rank'] for r in all_ranks)
    rarity_options = [
      discord.SelectOption(
        label=f"{r['name']} ({r['count']} owned)",
        value=r['name'],
        emoji=r.get('emoji')
      ) for r in rarities if r['rarity_rank'] < max_rank
    ]
    view = RarityDropdown(rarity_options)
    view.message = await ctx.respond(embed=embed, view=view, ephemeral=True)
