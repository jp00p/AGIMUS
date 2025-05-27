from common import *
from queries.badge_instances import *
from queries.badge_tags import *
from utils.badge_utils import *
from utils.check_channel_access import access_check
from utils.image_utils import generate_badge_collection_images
from utils.prestige import *

# -> cogs.badge_tags

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
async def user_badges_autocomplete(ctx:discord.AutocompleteContext):
  user_badges = [b['badge_name'] for b in await db_get_user_badge_instances(ctx.interaction.user.id)]
  if len(user_badges) == 0:
    user_badges = ["You don't have any badges yet!"]

  return [result for result in user_badges if ctx.value.lower() in result.lower()]


async def badges_autocomplete(ctx:discord.AutocompleteContext):
  special_badge_ids = [b['id'] for b in await db_get_special_badge_info()]
  all_badges = await db_get_all_badge_info()
  filtered_badges = [b for b in all_badges if b['id'] not in special_badge_ids]

  choices = [
    discord.OptionChoice(
      name=b['badge_name'],
      value=str(b['id'])
    )
    for b in filtered_badges if ctx.value.lower() in b['badge_name'].lower()
  ]
  return choices

async def tags_autocomplete(ctx:discord.AutocompleteContext):
  user_tags = [t['tag_name'] for t in await db_get_user_badge_tags(ctx.interaction.user.id)]
  user_tags.sort()
  if len(user_tags) == 0:
    user_tags = ["You don't have any tags yet!"]

  return [t for t in user_tags if ctx.value.lower() in t.lower()]

# __________             .___           ___________                    _________
# \______   \_____     __| _/ ____   ___\__    ___/____     ____  _____\_   ___ \  ____   ____
#  |    |  _/\__  \   / __ | / ___\_/ __ \|    |  \__  \   / ___\/  ___/    \  \/ /  _ \ / ___\
#  |    |   \ / __ \_/ /_/ |/ /_/  >  ___/|    |   / __ \_/ /_/  >___ \\     \___(  <_> ) /_/  >
#  |______  /(____  /\____ |\___  / \___  >____|  (____  /\___  /____  >\______  /\____/\___  /
#         \/      \/      \/_____/      \/             \//_____/     \/        \/      /_____/
class BadgeTags(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.max_tags = 25 # We can only have 25 items in a Discord select component

  tags_group = discord.SlashCommandGroup("badge_tags", "Badge Tags Commands!")

  @tags_group.command(
    name="create",
    description="Create a new badge tag. (NOTE: You can have a max of 25 tags)"
  )
  @option(
    name="tag",
    description="Name of the tag to create",
    required=True,
    min_length=1,
    max_length=24
  )
  async def create(self, ctx:discord.ApplicationContext, tag:str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.author.id

    tag = tag.strip()
    if len(tag) == 0:
      await ctx.followup.send(
        embed=discord.Embed(
          title="You Must Enter A Tag!",
          description=f"Tag name cannot be empty!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    current_user_tags = await db_get_user_badge_tags(user_discord_id)
    current_user_tag_names = [t['tag_name'] for t in current_user_tags]

    if tag in current_user_tag_names:
      await ctx.followup.send(
        embed=discord.Embed(
          title="This Tag Already Exists",
          description=f"You've already created **{tag}**!" + "\n\n" + "You can associate your badges with this tag via `/badge_tags tag`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if len(current_user_tags) >= self.max_tags:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Maximum Tags Allowed Reached",
          description=f"You've reached the maximum number of tags allowed ({self.max_tags})!" + "\n\n" + "You can remove a tag if desired via `/badge_tags delete`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # If checks pass, go ahead and create the new tag for the user
    await db_create_user_badge_tag(user_discord_id, tag)
    await ctx.followup.send(
      embed=discord.Embed(
        title="Tag Created Successfully!",
        description=f"You've created a new tag: **{tag}**!" + "\n\n" f"You can tag your badges with this tag now via `/badge_tags tag`",
        color=discord.Color.green()
      ),
      ephemeral=True
    )
    return

  @tags_group.command(
    name="delete",
    description="Delete an existing badge tag"
  )
  @option(
    name="tag",
    description="Name of the tag to delete",
    required=True,
    autocomplete=tags_autocomplete
  )
  async def delete(self, ctx:discord.ApplicationContext, tag:str):
    await ctx.defer(ephemeral=True)

    user_discord_id = ctx.author.id

    # Checks
    tag = tag.strip()
    if len(tag) == 0:
      await ctx.followup.send(
        embed=discord.Embed(
          title="You Must Enter A Tag!",
          description=f"Tag name cannot be empty!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if tag == "You don't have any tags yet!":
      await ctx.respond(
        embed=discord.Embed(
          title="No Tags Present",
          description="You'll need to set up some tags first via `/badge_tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    current_user_tags = await db_get_user_badge_tags(user_discord_id)
    current_user_tag_names = [t['tag_name'] for t in current_user_tags]

    if tag not in current_user_tag_names:
      await ctx.followup.send(
        embed=discord.Embed(
          title="This Tag Does Not Exist",
          description=f"**{tag}** is not a tag you have created!" + "\n\n" + "You can create a new tag via `/badge_tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # If checks pass, go ahead and delete the tag for the user
    await db_delete_user_badge_tag(user_discord_id, tag)
    await ctx.followup.send(
      embed=discord.Embed(
        title="Tag Deleted Successfully!",
        description=f"You've deleted the tag: **{tag}**!" + "\n\n" + f"Note that any badges that were previously tagged **{tag}** have been untagged as well.",
        color=discord.Color.green()
      ),
      ephemeral=True
    )
    return


  @tags_group.command(
    name="rename",
    description="Rename an existing badge tag"
  )
  @option(
    name="tag",
    description="Name of the tag to rename",
    required=True,
    autocomplete=tags_autocomplete
  )
  @option(
    name="new_name",
    description="New name for the tag",
    required=True
  )
  async def rename(self, ctx:discord.ApplicationContext, tag:str, new_name:str):
    await ctx.defer(ephemeral=True)

    user_discord_id = ctx.author.id

    # Checks
    tag = tag.strip()
    new_name = new_name.strip()
    if len(tag) == 0 or len(new_name) == 0:
      await ctx.followup.send(
        embed=discord.Embed(
          title="You Must Enter A Tag!",
          description=f"Tag name cannot be empty!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if len(new_name) > 24:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Tag Is Too Long!",
          description=f"Tag name cannot exceed 24 characters!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if tag == "You don't have any tags yet!":
      await ctx.respond(
        embed=discord.Embed(
          title="No Tags Present",
          description="You'll need to set up some tags first via `/badge_tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    current_user_tags = await db_get_user_badge_tags(user_discord_id)
    current_user_tag_names = [t['tag_name'] for t in current_user_tags]

    if tag not in current_user_tag_names:
      await ctx.followup.send(
        embed=discord.Embed(
          title="This Tag Does Not Exist",
          description=f"**{tag}** is not a tag you have created!" + "\n\n" + "You can create a new tag via `/badge_tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if new_name in current_user_tag_names:
      await ctx.followup.send(
        embed=discord.Embed(
          title="This Tag Name Already Exists",
          description=f"You already have a tag named **{new_name}**!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # If checks pass, go ahead and rename the tag for the user
    await db_rename_user_badge_tag(user_discord_id, tag, new_name)
    await ctx.followup.send(
      embed=discord.Embed(
        title="Tag Renamed Successfully!",
        description=f"You've successfully the tag **{tag}** as **{new_name}**!",
        color=discord.Color.green()
      ),
      ephemeral=True
    )
    return


  @tags_group.command(
    name="tag",
    description="Tag a Badge!"
  )
  @option(
    name="badge",
    description="Name of the Badge to tag",
    required=True,
    autocomplete=badges_autocomplete
  )
  async def tag(self, ctx: discord.ApplicationContext, badge: str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.author.id

    badge_info = await db_get_badge_info_by_id(badge)
    if not badge_info:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Badge Not Found",
          description="That Badge does not exist!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    user_tags = await db_get_user_badge_tags(user_discord_id)
    if not user_tags:
      await ctx.followup.send(
        embed=discord.Embed(
          title="No Tags Yet",
          description="You haven't created any tags yet! Use `/badge_tags create` first.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    associated_tags = await db_get_associated_user_badge_tags_by_info_id(user_discord_id, badge_info['id'])
    associated_tag_ids = [t['id'] for t in associated_tags]

    # Build tag selector view
    options = [
      discord.SelectOption(
        label=t['tag_name'],
        value=str(t['id']),
        default=t['id'] in associated_tag_ids
      ) for t in user_tags
    ]

    class TagSelector(discord.ui.Select):
      def __init__(self):
        super().__init__(
          placeholder="Select tags to apply",
          min_values=0,
          max_values=len(options),
          options=options
        )

      async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_tag_ids = [int(v) for v in self.values]

        tag_ids_to_delete = [t['id'] for t in associated_tags if t['id'] not in selected_tag_ids]
        await db_delete_user_badge_info_tags_associations(user_discord_id, tag_ids_to_delete, badge_info['id'])

        if selected_tag_ids:
          await db_create_user_badge_info_tags_associations(user_discord_id, badge_info['id'], selected_tag_ids)

        final_tags = await db_get_associated_user_badge_tags_by_info_id(user_discord_id, badge_info['id'])
        tag_names = [t['tag_name'] for t in final_tags]

        description = (
          f"**{badge_info['badge_name']}** is now tagged with:\n\n- " + "\n- ".join(sorted(tag_names, key=str.lower))
          if tag_names else f"**{badge_info['badge_name']}** now has no tags associated."
        )

        await interaction.edit_original_response(
          embed=discord.Embed(
            title="Tags Updated",
            description=description,
            color=discord.Color.green()
          ),
          view=None
        )

    class TagView(discord.ui.View):
      def __init__(self):
        super().__init__()
        self.add_item(TagSelector())

    embed = discord.Embed(
      title=badge_info['badge_name'],
      description="Select the tags you want to associate with this Badge",
      color=discord.Color.blurple()
    )
    badge_file = discord.File(f"./images/badges/{badge_info['badge_filename']}", filename=badge_info['badge_filename'])
    embed.set_image(url=f"attachment://{badge_info['badge_filename']}")

    await ctx.followup.send(embed=embed, file=badge_file, view=TagView(), ephemeral=True)


  @tags_group.command(
    name="collection",
    description="Display a collection of tagged badges"
  )
  @option(
    name="public",
    description="Show to public?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="No",
        value="no"
      ),
      discord.OptionChoice(
        name="Yes",
        value="yes"
      )
    ]
  )
  @option(
    name="tag",
    description="Name of the tag",
    required=True,
    autocomplete=tags_autocomplete
  )
  @option(
    name="prestige",
    description="Which Prestige Tier to display?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @commands.check(access_check)
  async def collection(self, ctx:discord.ApplicationContext, public:str, tag:str, prestige:str):
    public = (public == "yes")
    await ctx.defer(ephemeral=not public)

    user_discord_id = ctx.author.id

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)

    current_user_tags = await db_get_user_badge_tags(user_discord_id)
    current_user_tag_names = [t['tag_name'] for t in current_user_tags]

    # Checks
    if tag == "You don't have any tags yet!":
      await ctx.respond(
        embed=discord.Embed(
          title="No Tags Present",
          description="You'll need to set up some tags first via `/badge_tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if tag not in current_user_tag_names:
      await ctx.respond(
        embed=discord.Embed(
          title="This Tag Does Not Exist",
          description=f"**{tag}** is not a tag you have created!" + "\n\n" + "You can create a new tag via `/badge_tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    tagged_instances = await db_get_user_tagged_badge_instances_by_prestige(user_discord_id, tag, prestige)
    if not tagged_instances:
      await ctx.respond(
        embed=discord.Embed(
          title="No Tagged Badges Found",
          description=f"No {PRESTIGE_TIERS[prestige]} Badges tagged with {tag} found!\n\nYou may not have collected any at this Tier yet?",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # Set up text values for paginated images
    tagged_badges_cnt = len(tagged_instances)
    collection_label = f"Tagged - {tag}"

    badge_images = await generate_badge_collection_images(ctx.author, prestige, tagged_instances, 'collection', collection_label)

    embed = discord.Embed(
      title=f"Tagged {PRESTIGE_TIERS[prestige]} Badges",
      description=f'{ctx.author.mention} has tagged {tagged_badges_cnt} **{tag}** badges!',
      color=discord.Color.blurple()
    )

    # If we're doing a public display, use the images directly
    # Otherwise private displays can use the paginator
    if not public:
      buttons = [
        pages.PaginatorButton("prev", label="   ⬅   ", style=discord.ButtonStyle.primary, disabled=bool(tagged_badges_cnt <= 30), row=1),
        pages.PaginatorButton(
          "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
        ),
        pages.PaginatorButton("next", label="   ➡   ", style=discord.ButtonStyle.primary, disabled=bool(tagged_badges_cnt <= 30), row=1),
      ]

      pages_list = [
        pages.Page(files=[image], embeds=[embed])
        for image in badge_images
      ]
      paginator = pages.Paginator(
          pages=pages_list,
          show_disabled=True,
          show_indicator=True,
          use_default_buttons=False,
          custom_buttons=buttons,
          loop_pages=True
      )
      await paginator.respond(ctx.interaction, ephemeral=True)
    else:
      # We can only attach up to 10 files per message, so if it's public send them in chunks
      file_chunks = [badge_images[i:i + 10] for i in range(0, len(badge_images), 10)]
      for chunk_index, chunk in enumerate(file_chunks):
        # Only post the embed on the last chunk
        if chunk_index + 1 == len(file_chunks):
          await ctx.followup.send(embed=embed, files=chunk, ephemeral=False)
        else:
          await ctx.followup.send(files=chunk, ephemeral=False)


  @tags_group.command(
    name="carousel",
    description="Cycle through all Badges to apply your tags"
  )
  @option(
    name="start",
    description="Start from beginning or resume where you left off?",
    required=True,
    choices=[
      discord.OptionChoice(name="Resume", value="resume"),
      discord.OptionChoice(name="Beginning", value="beginning")
    ]
  )
  async def carousel(self, ctx: discord.ApplicationContext, start: str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.author.id

    user_tags = await db_get_user_badge_tags(user_discord_id)
    if not user_tags:
      await ctx.followup.send(
        embed=discord.Embed(
          title="No Tags Present",
          description="You haven't set up any tags yet!\n\nUse `/badge_tags create` to add some first!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    all_badge_info = await db_get_all_badge_info()
    all_badge_info.sort(key=lambda b: b['badge_filename'].lower())

    if not all_badge_info:
      await ctx.followup.send(
        embed=discord.Embed(
          title="No Badges Available",
          description="There are no Badges available to tag.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    resume_info = await db_get_last_carousel_badge_info(user_discord_id) if start == "resume" else None
    if start == "resume" and not resume_info:
      await ctx.followup.send(
        embed=discord.Embed(
          title="No Resume Available",
          description="You selected 'Resume' but you hadn't previously begun cycling. Starting from the beginning.",
          color=discord.Color.orange()
        ),
        ephemeral=True
      )
      return

    if start == "beginning":
      await db_clear_last_carousel_badge_info(user_discord_id)
      selected = all_badge_info[0]
    else:
      selected = resume_info

    await db_upsert_last_carousel_badge_info(user_discord_id, selected['id'])

    # Set up View Classes
    class CarouselSelector(discord.ui.Select):
      def __init__(self, tags, selected_ids):
        options = [
          discord.SelectOption(
            label=t['tag_name'],
            value=str(t['id']),
            default=t['id'] in selected_ids
          ) for t in tags
        ]
        super().__init__(
          placeholder="Select Tags for this Badge",
          min_values=0,
          max_values=len(options),
          options=options
        )

      async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.view.tag_ids = [int(v) for v in self.values]

    class CarouselButton(discord.ui.Button):
      def __init__(self, user_discord_id, current_info, info_list):
        self.user_discord_id = user_discord_id
        self.current_info = current_info
        self.info_list = info_list
        super().__init__(
          label="Tag Badge / Move On",
          style=discord.ButtonStyle.primary,
          row=2
        )

      async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        associated_tags = await db_get_associated_user_badge_tags_by_info_id(self.user_discord_id, self.current_info['id'])
        tag_ids_to_delete = [t['id'] for t in associated_tags if t['id'] not in self.view.tag_ids]
        await db_delete_user_badge_info_tags_associations(self.user_discord_id, tag_ids_to_delete, self.current_info['id'])

        if self.view.tag_ids:
          await db_create_user_badge_info_tags_associations(self.user_discord_id, self.current_info['id'], self.view.tag_ids)

        final_tags = await db_get_associated_user_badge_tags_by_info_id(self.user_discord_id, self.current_info['id'])
        tag_names = [t['tag_name'] for t in final_tags]

        if tag_names:
          description = f"**{self.current_info['badge_name']}** is now tagged with:\n\n- " + "\n- ".join(sorted(tag_names, key=str.lower)) + "\n\nUse `/badge_tags collection` to show off your tags!"
        else:
          description = f"**{self.current_info['badge_name']}** has no tags associated!"

        summary_embed = discord.Embed(
          title="Tag Summary",
          description=description,
          color=discord.Color.green()
        )
        summary_embed.set_image(url=f"attachment://{self.current_info['badge_filename']}")
        badge_file = discord.File(fp=f"./images/badges/{self.current_info['badge_filename']}", filename=self.current_info['badge_filename'])
        await interaction.edit_original_response(embed=summary_embed, attachments=[badge_file], view=None)

        current_index = next((i for i, b in enumerate(self.info_list) if b['id'] == self.current_info['id']), None)
        if current_index is None or current_index + 1 >= len(self.info_list):
          await interaction.followup.send(
            embed=discord.Embed(
              title="You're done!",
              description="You've completed tagging every frikkin Badge in the system! Nice.",
              color=discord.Color.blurple()
            ),
            ephemeral=True
          )
          await db_clear_last_carousel_badge_info(self.user_discord_id)
          return

        next_info = self.info_list[current_index + 1]
        await db_upsert_last_carousel_badge_info(self.user_discord_id, next_info['id'])

        new_view = CarouselView(self.user_discord_id, next_info, user_tags, self.info_list)
        embed = discord.Embed(title=next_info['badge_name'], color=discord.Color.dark_purple())
        embed.set_image(url=f"attachment://{next_info['badge_filename']}")
        badge_file = discord.File(fp=f"./images/badges/{next_info['badge_filename']}", filename=next_info['badge_filename'])
        await interaction.followup.send(embed=embed, view=new_view, file=badge_file, ephemeral=True)

    class CarouselView(discord.ui.View):
      def __init__(self, user_discord_id, badge_info, tags, info_list):
        super().__init__()
        self.tag_ids = [t['id'] for t in asyncio.run(db_get_associated_user_badge_tags_by_info_id(user_discord_id, badge_info['id']))]
        self.add_item(CarouselSelector(tags, self.tag_ids))
        self.add_item(CarouselButton(user_discord_id, badge_info, info_list))

    # Actually use the View above
    view = CarouselView(user_discord_id, selected, user_tags, all_badge_info)
    embed = discord.Embed(
      title=selected['badge_name'],
      description="Tag this Badge below.",
      color=discord.Color.blurple()
    )
    badge_file = discord.File(fp=f"./images/badges/{selected['badge_filename']}", filename=selected['badge_filename'])
    embed.set_image(url=f"attachment://{selected['badge_filename']}")
    await ctx.followup.send(embed=embed, file=badge_file, view=view, ephemeral=True)