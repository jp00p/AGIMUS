from common import *

class RoleSelect(discord.ui.Select):
  def __init__(self, cog, message_name, post, role_options):
    self.cog = cog
    self.message_name = message_name

    options = []
    for role_option in role_options:
      description = role_option.get('description')
      if description:
        description = description.replace('**', '')

      options.append(discord.SelectOption(
        label=role_option['role'],
        value=role_option['role'],
        description=description,
        emoji=role_option.get('emoji')
      ))

    super().__init__(
      placeholder=post.get('select_placeholder', 'Select a role to add or remove...'),
      min_values=1,
      max_values=1,
      options=options,
      custom_id=f'agimus:role-select:{message_name}'
    )

  async def callback(self, interaction:discord.Interaction):
    await self.cog.handle_role_selection(interaction, self.message_name, self.values[0])
    # Reset the shared select so the same option can be selected again to toggle it off.
    await interaction.message.edit(view=self.view)


class RoleSelectView(discord.ui.View):
  def __init__(self, cog, message_name, post, role_options):
    super().__init__(timeout=None)
    self.add_item(RoleSelect(cog, message_name, post, role_options))


class RoleSelects(commands.Cog):
  FOUNDER_ROLE_ID = 1505225552599187476
  FOUNDER_ROLE_SUFFIX = ' (Founder)'
  DEPARTMENT_MESSAGE_NAME = 'departments'

  def __init__(self, bot:commands.Bot):
    self.bot = bot
    self.roles_channel = None
    self.role_select_messages = {}
    self.persistent_views_registered = False
    self.role_select_data = {}
    self.missing_role_warnings = set()

    message_names = ['pronouns', 'locations', 'departments', 'notifications']
    for message_name in message_names:
      with open(f'./data/role_selects/{message_name}.json') as f:
        self.role_select_data[message_name] = json.load(f)

  @commands.Cog.listener()
  async def on_ready(self):
    if not config['roles']['reaction_roles_enabled']:
      return

    self.roles_channel = self.bot.get_channel(config['channels']['roles-and-pronouns'])
    await self.ensure_role_select_messages()
    self.role_select_messages = await self.load_role_select_messages()

    if not self.persistent_views_registered:
      self.register_persistent_views()
      self.persistent_views_registered = True

    if not self.rebuild_embeds.is_running():
      self.rebuild_embeds.start()

  def register_persistent_views(self):
    for message_id, message_data in self.role_select_messages.items():
      message_name = message_data['message_name']
      view = self.build_role_select_view(message_name)
      if view:
        self.bot.add_view(view, message_id=message_id)

  def build_role_select_view(self, message_name):
    role_options = self.get_available_role_options(message_name)
    if not role_options:
      logger.error(f'Role Select category {message_name} has no valid Discord roles and will not have a dropdown.')
      return None

    return RoleSelectView(
      self,
      message_name,
      self.role_select_data[message_name],
      role_options
    )

  def get_available_role_options(self, message_name):
    role_options = []

    for role_option in self.role_select_data[message_name]['options']:
      if role_option.get('separator'):
        continue

      role = self.get_configured_role(message_name, role_option['role'])
      if role:
        role_options.append(role_option)

    return role_options

  def get_configured_role(self, message_name, role_name):
    role = discord.utils.get(self.roles_channel.guild.roles, name=role_name)
    warning_key = (message_name, role_name)

    if role is None:
      if warning_key not in self.missing_role_warnings:
        logger.error(
          f'Role Select category {message_name} is configured for missing Discord role: {role_name}'
        )
        self.missing_role_warnings.add(warning_key)
      return None

    self.missing_role_warnings.discard(warning_key)
    return role

  async def ensure_role_select_messages(self):
    role_select_db_data = await self.get_role_select_db_data()
    existing_records = {rdb['message_name']: rdb for rdb in role_select_db_data}

    for message_name, post in self.role_select_data.items():
      role_message_record = existing_records.get(message_name)
      header_message_record = existing_records.get(f'{message_name}_header')

      role_message = await self.fetch_stored_role_select_message(role_message_record)
      header_message = None
      if post.get('header_image_url'):
        header_message = await self.fetch_stored_role_select_message(header_message_record)

      role_message_missing = role_message is None
      header_message_missing = bool(post.get('header_image_url')) and header_message is None

      if not role_message_missing and not header_message_missing:
        await self.sync_role_select_message(role_message, message_name, post)
        continue

      logger.info(f'Rebuilding missing role select message pair for {message_name}.')

      if header_message:
        await header_message.delete()

      if role_message:
        await role_message.delete()

      await self.delete_role_select_db_data(message_name)
      await self.create_role_select_message(message_name, post)

  async def fetch_stored_role_select_message(self, record):
    if not record:
      return None

    message_id = int(record['message_id'])
    try:
      return await self.roles_channel.fetch_message(message_id)
    except discord.NotFound:
      logger.info(f'Role select message {message_id} no longer exists in Discord.')
      return None

  async def sync_role_select_message(self, message, message_name, post):
    embed = self.build_role_select_embed(message_name, post)
    view = self.build_role_select_view(message_name)
    await message.edit(
      content=post['message_content'],
      embed=embed,
      view=view
    )

    if message.reactions:
      await message.clear_reactions()

  async def create_role_select_message(self, message_name, post):
    if post.get('header_image_url'):
      header_msg = await self.roles_channel.send(content=post['header_image_url'])
      header_msg_id = header_msg.id
    else:
      header_msg_id = None

    embed = self.build_role_select_embed(message_name, post)
    view = self.build_role_select_view(message_name)
    role_select_msg = await self.roles_channel.send(
      content=post['message_content'],
      embed=embed,
      view=view
    )

    await self.store_role_select_data(
      header_msg_id,
      role_select_msg.id,
      message_name,
      post['selection_type']
    )

    return role_select_msg

  async def delete_role_select_db_data(self, message_name):
    header_message_name = f'{message_name}_header'
    async with AgimusDB() as query:
      sql = 'DELETE FROM reaction_role_messages WHERE message_name IN (%(message_name)s, %(header_name)s)'
      await query.execute(sql, {
        'message_name': message_name,
        'header_name': header_message_name
      })

  async def load_role_select_messages(self):
    response = {}

    for rdb in await self.get_role_select_db_data():
      message_name = rdb['message_name']
      if rdb['reaction_type'] and message_name in self.role_select_data:
        response[int(rdb['message_id'])] = {
          'message_name': message_name
        }

    return response

  async def handle_role_selection(self, interaction:discord.Interaction, message_name:str, role_name:str):
    user = interaction.user
    role = self.get_configured_role(message_name, role_name)

    if role is None:
      await interaction.response.send_message(
        'That role could not be found. Please let a moderator know.',
        ephemeral=True
      )
      return

    role_option = next(
      role_option for role_option in self.role_select_data[message_name]['options']
      if role_option.get('role') == role_name
    )
    role_emoji = role_option.get('emoji')
    role_label = f'{role_emoji} {role.name}' if role_emoji else role.name

    if user.get_role(role.id) is not None:
      roles_to_remove = self.get_role_select_roles_to_remove(user, role, message_name)

      if roles_to_remove:
        logger.info(f'Removing role(s) {self.format_role_names(roles_to_remove)} from {user.display_name}!')
        await user.remove_roles(*roles_to_remove, reason='RoleSelect')

      embed = discord.Embed(
        title='Role Updated Successfully!',
        description=f'Removed **{role_label}** from your profile.',
        color=discord.Color.green()
      )
      await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
        delete_after=60
      )
      return

    roles_to_add = self.get_role_select_roles_to_add(user, role, message_name)

    if roles_to_add:
      logger.info(f'Adding role(s) {self.format_role_names(roles_to_add)} to {user.display_name}!')
      await user.add_roles(*roles_to_add, reason='RoleSelect')

    removed_other_roles = False
    if self.role_select_data[message_name]['selection_type'] == 'single':
      roles_to_remove = []

      for role_option in self.role_select_data[message_name]['options']:
        if role_option.get('separator') or role_option['role'] == role.name:
          continue

        other_role = self.get_configured_role(message_name, role_option['role'])
        if other_role:
          roles_to_remove.extend(self.get_role_select_roles_to_remove(user, other_role, message_name))

      roles_to_remove = self.dedupe_roles(roles_to_remove)

      if roles_to_remove:
        logger.info(f'Removing role(s) {self.format_role_names(roles_to_remove)} from {user.display_name}!')
        await user.remove_roles(*roles_to_remove, reason='RoleSelect')
        removed_other_roles = True

    response = f'Added **{role_label}** to your profile.'
    if removed_other_roles:
      response += '\n\nThis replaced your previous role in that category.'

    embed = discord.Embed(
      title='Role Updated Successfully!',
      description=response,
      color=discord.Color.green()
    )
    await interaction.response.send_message(
      embed=embed,
      ephemeral=True,
      delete_after=60
    )

  def get_role_select_roles_to_add(self, user:discord.Member, role:discord.Role, message_name:str):
    if message_name != self.DEPARTMENT_MESSAGE_NAME:
      if user.get_role(role.id) is None:
        return [role]
      return []

    roles = []

    if user.get_role(role.id) is None:
      roles.append(role)

    founder_shadow_role = self.get_founder_shadow_role(user, role)

    if founder_shadow_role and user.get_role(founder_shadow_role.id) is None:
      roles.append(founder_shadow_role)

    return roles

  def get_role_select_roles_to_remove(self, user:discord.Member, role:discord.Role, message_name:str):
    if message_name != self.DEPARTMENT_MESSAGE_NAME:
      if user.get_role(role.id) is not None:
        return [role]
      return []

    roles = []

    if user.get_role(role.id) is not None:
      roles.append(role)

    founder_shadow_role = self.get_department_shadow_role(role)

    if founder_shadow_role and user.get_role(founder_shadow_role.id) is not None:
      roles.append(founder_shadow_role)

    return roles

  def get_founder_shadow_role(self, user:discord.Member, role:discord.Role):
    if user.get_role(self.FOUNDER_ROLE_ID) is None:
      return None

    return self.get_department_shadow_role(role)

  def get_department_shadow_role(self, role:discord.Role):
    return discord.utils.get(role.guild.roles, name=f'{role.name}{self.FOUNDER_ROLE_SUFFIX}')

  def dedupe_roles(self, roles):
    role_map = {}

    for role in roles:
      role_map[role.id] = role

    return list(role_map.values())

  def format_role_names(self, roles):
    return ', '.join([role.name for role in roles])

  async def store_role_select_data(self, header_id, message_id, message_name, selection_type):
    header_message_name = f'{message_name}_header'
    async with AgimusDB() as query:
      sql = [
        'DELETE FROM reaction_role_messages WHERE message_name IN (%(message_name)s, %(header_name)s)',
        'INSERT INTO reaction_role_messages (message_id, reaction_type, message_name) VALUES (%(message_id)s, %(reaction_type)s, %(message_name)s)',
      ]
      vals = {
        'message_name': message_name,
        'header_name': header_message_name,
        'message_id': message_id,
        'reaction_type': selection_type
      }

      for q in sql:
        await query.execute(q, vals)

      if header_id:
        sql = 'INSERT INTO reaction_role_messages (message_id, message_name) VALUES (%(header_id)s, %(header_name)s)'
        await query.execute(sql, {'header_id': header_id, 'header_name': header_message_name})

    self.role_select_messages = await self.load_role_select_messages()

  async def get_role_select_db_data(self):
    async with AgimusDB(dictionary=True) as query:
      sql = 'SELECT * FROM reaction_role_messages'
      await query.execute(sql)
      role_select_data = await query.fetchall()
    return role_select_data

  @commands.command()
  @commands.has_permissions(administrator=True)
  async def q_update_role_messages(self, ctx:discord.ApplicationContext, clear=False):
    logger.info(f'{ctx.author.display_name} is running the top secret {Back.RED}{Fore.WHITE}UPDATE ROLE MESSAGES{Fore.RESET}{Back.RESET} command!')
    try:
      await ctx.message.delete()
    except (discord.NotFound, AttributeError):
      pass

    if clear:
      for role_message in await self.get_role_select_db_data():
        message = await self.fetch_stored_role_select_message(role_message)
        if message:
          logger.info(f'Deleting old role select message {message.id}')
          await message.delete()

      async with AgimusDB() as query:
        await query.execute('DELETE FROM reaction_role_messages')

    await self.ensure_role_select_messages()
    self.role_select_messages = await self.load_role_select_messages()

  @q_update_role_messages.error
  async def q_update_role_messages_error(self, ctx, error):
    if isinstance(error, commands.MissingPermissions):
      await ctx.author.send("You think you're clever! Access denied.")
    else:
      await ctx.send('Sensoars indicate some kind of ...*error* has occured!')
      logger.info(traceback.format_exc())
      logger.error(error)

  def build_role_select_embed(self, message_name, post):
    embed_description = post['embed']['description']
    if post.get('embed_channel_name_placeholder'):
      channel_string = f"<#{get_channel_id(config['channels'][post['embed_channel_name_placeholder']])}>"
      embed_description = embed_description.format(channel_string)

    embed = discord.Embed(
      title=post['embed']['title'],
      description=embed_description,
      color=discord.Color.from_rgb(251, 112, 5)
    )
    embed.set_thumbnail(url=post['thumbnail_url'])
    list_of_roles = []

    for role_option in post['options']:
      if role_option.get('separator'):
        embed_desc = '━━━━━━━━━━━━━━━'
      else:
        role = self.get_configured_role(message_name, role_option['role'])
        if role is None:
          continue

        role_emoji = role_option.get('emoji')
        role_prefix = f'{role_emoji} ' if role_emoji else ''
        embed_desc = f'{role_prefix}{role.mention} ({len(role.members)})'
        if role_option.get('description'):
          embed_desc += f"\n{role_option['description']}\n"
      list_of_roles.append(embed_desc)

    if list_of_roles:
      embed.add_field(
        name='⠀',
        value='\n'.join(list_of_roles),
        inline=False
      )

    embed.set_footer(text=post['embed']['footer'])
    return embed

  @tasks.loop(seconds=60)
  async def rebuild_embeds(self):
    if not config['roles']['reaction_roles_enabled']:
      return

    for message_id, message_data in self.role_select_messages.items():
      message_name = message_data['message_name']
      message = self.roles_channel.get_partial_message(message_id)
      new_embed = self.build_role_select_embed(message_name, self.role_select_data[message_name])
      await message.edit(embed=new_embed)
      await asyncio.sleep(10)

  def cog_unload(self):
    self.rebuild_embeds.cancel()
