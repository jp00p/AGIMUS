from distutils.command.build import build
from common import *

class ReactRoles(commands.Cog):
  def __init__(self, bot:commands.Bot):
    self.bot = bot
    self.roles_channel = None
    self.reaction_roles = {} # role list
    self.reaction_data = {} # base json data
    message_names = ["pronouns", "locations", "departments", "notifications"]
    for message_type in message_names:
      f = open(f"./data/react_roles/{message_type}.json")
      self.reaction_data[message_type] = json.load(f) # fill the base json for our messages
      f.close()

  @commands.Cog.listener()
  async def on_ready(self):
    self.roles_channel = self.bot.get_channel(config["channels"]["roles-and-pronouns"])
    self.reaction_roles = await self.load_role_reactions() # gather all our data for reactions
    await self.rebuild_embeds.start()

  # listen to raw reaction additions
  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload:discord.RawReactionActionEvent):
    if payload.member.bot:
      return
    if payload.channel_id == self.roles_channel.id:
      await self.parse_reaction(payload)

  # listen to raw reaction removals
  @commands.Cog.listener()
  async def on_raw_reaction_remove(self, payload:discord.RawReactionActionEvent):
    if payload.channel_id == self.roles_channel.id:
      await self.parse_reaction(payload)

  # build reaction role dict for handling reacts
  async def load_role_reactions(self):
    response = {}
    for rdb in await self.get_reaction_db_data():
      if rdb["reaction_type"]:
        message_id = rdb["message_id"]
        message_name = rdb["message_name"]
        response[message_id] = { "reactions": {}, "reaction_type": rdb["reaction_type"], "message_name": message_name }
        # loop over json and pull out emoji:role
        for rr in self.reaction_data[message_name]["reactions"]:
          response[message_id]["reactions"][rr["emoji"]] = discord.utils.get(bot.guilds[0].roles,name=rr["role"])
    return response

  # handle a reaction, either add or remove roles when a user reacts
  async def parse_reaction(self, payload:discord.RawReactionActionEvent):
    user = self.bot.guilds[0].get_member(payload.user_id)
    user_info = await get_user(user.id)
    message = self.roles_channel.get_partial_message(payload.message_id)
    data = self.reaction_roles[str(message.id)]
    message_name = data["message_name"]
    reaction_type = data.get("reaction_type")
    role = data["reactions"].get(str(payload.emoji))
    if user and role:
      user_dm_message = ""
      # user is valid and we found a valid role associated with the reaction
      if user.get_role(role.id) == None and payload.event_type == "REACTION_ADD":
        logger.info(f"Adding role {role.name} to {user.display_name}!")
        # add role!
        await user.add_roles(role, reason="ReactionRole")
        user_dm_message = f"You have __added__ the role **{payload.emoji} {role.name}** to your profile on the USS Hood!"
        if reaction_type == "single":
          # if its a single type reaction, remove all other associated roles
          roles_to_remove = []
          emoji_to_remove = []
          for role_emoji, rr in data["reactions"].items():
            if rr.id != role.id:
              roles_to_remove.append(rr)
              emoji_to_remove.append(role_emoji)
          if len(roles_to_remove) > 0:
            await user.remove_roles(*roles_to_remove, reason="ReactionRole")
            user_dm_message += f"\n> This has removed other roles in that same category automatically. Magic!"
            for role_emoji in emoji_to_remove:
              await message.remove_reaction(role_emoji, user)
      else:
          # they already have the role, remove it!
          if user.get_role(role.id) != None and payload.event_type == "REACTION_REMOVE":
            logger.info(f"Removing {role.name} from {user.display_name}!")
            await user.remove_roles(role, reason="ReactionRole")
            user_dm_message = f"You have __removed__ the role **{payload.emoji} {role.name}** from your profile on the USS Hood!"
      if user_dm_message != "" and user_info["receive_notifications"]:
        if random.choice([0,1,2]) == 1:
          user_dm_message += f"\n\n(PS. Use `/settings` in the server to disable these DMs if you need to.)"
        try:
          await user.send(user_dm_message)
        except discord.Forbidden as e:
          logger.info(f"Unable to send react role confirmation message to {user.display_name} because they have DMs disabled.")
          pass



  # updates db with new message details and deletes old messages from db
  async def store_reaction_data(self, header_id, message_id, message_name, reaction_type):
    header_message_name = f"{message_name}_header"
    async with AgimusDB() as query:

      sql = [
        "DELETE FROM reaction_role_messages WHERE message_name IN (%(message_name)s, %(header_name)s)",
        "INSERT INTO reaction_role_messages (message_id, reaction_type, message_name) VALUES (%(message_id)s, %(reaction_type)s, %(message_name)s)",
      ]
      vals = {
        "message_name": message_name,
        "header_name": header_message_name,
        "message_id": message_id,
        "reaction_type": reaction_type
      }
      for q in sql:
        await query.execute(q, vals)

      if header_id:
        sql = "INSERT INTO reaction_role_messages (message_id, message_name) VALUES (%(header_id)s, %(header_name)s)"
        await query.execute(sql, {'header_id': header_id, 'header_name': header_message_name})

    self.reaction_roles = await self.load_role_reactions()

  # add initial reactions to message
  async def add_role_reactions(self, message, reacts):
    if len(reacts) > 0:
      for r in reacts:
        if not r.get('separator'):
          await message.add_reaction(r["emoji"])

  # get all existing reaction message data
  async def get_reaction_db_data(self):
    async with AgimusDB(dictionary=True) as query:
      sql = "SELECT * FROM reaction_role_messages"
      await query.execute(sql)
      reaction_data = await query.fetchall()
    return reaction_data

  @commands.command()
  @commands.has_permissions(administrator=True)
  async def q_update_role_messages(self, ctx:discord.ApplicationContext, clear=False):
    logger.info(f"{ctx.author.display_name} is running the top secret {Back.RED}{Fore.WHITE}UPDATE ROLE MESSAGES{Fore.RESET}{Back.RESET} command!")
    try:
      await ctx.message.delete()
    except (discord.NotFound, AttributeError):
      pass  # Message already deleted or not a message-type context
    message_ids = await self.load_role_reactions()
    # if there are existing messages, remove them
    if clear:
      if len(message_ids) > 0:
        for rm in message_ids:
          logger.error(rm)
          try:
            message = await self.roles_channel.fetch_message(rm)
          except discord.NotFound:
            logger.info("React role message not found, oh well! Moving on with my life.")
          else:
            logger.info(f"Deleting old role message {message.id}")
            await message.delete()
      existing_messages = {}
    else:
      existing_messages = {rdb["message_name"]:rdb for rdb in self.reaction_db_data}

    # loop over all the reaction data and build out the messages
    for message_name, p in self.reaction_data.items():
      if existing_messages.get(message_name):
        continue

      message_content = p["message_content"] # the plain message content

      if p.get("header_image_url") != "":
        # post the header image first
        header_msg = await self.roles_channel.send(content=p["header_image_url"])
        header_msg_id = header_msg.id
      else:
        header_msg_id = None

      # build the embed
      embed = self.build_react_embed(p)
      # send the message
      react_role_msg = await self.roles_channel.send(content=message_content, embed=embed)

      # save some of the message details to the database
      await self.store_reaction_data(header_msg_id, react_role_msg.id, message_name, p["reaction_type"])
      self.reaction_roles = await self.load_role_reactions()
      # add the reactions to the message
      await self.add_role_reactions(react_role_msg, p["reactions"])
    # update role reactions dict
    self.role_reactions = await self.load_role_reactions()

  @q_update_role_messages.error
  async def q_update_role_messages_error(self, ctx, error):
    if isinstance(error, commands.MissingPermissions):
      await ctx.author.send("You think you're clever! Access denied.")
    else:
      await ctx.send("Sensoars indicate some kind of ...*error* has occured!")
      logger.info(traceback.format_exc())
      logger.error(error)

  # builds and returns the embed for the current reaction post
  def build_react_embed(self, post):
    embed = None
    embed_description = post["embed"]["description"]
    if post.get("embed_channel_name_placeholder"):
      # add channel name mention to embed if there is one
      channel_string = f"<#{get_channel_id(config['channels'][post['embed_channel_name_placeholder']])}>"
      embed_description = embed_description.format(channel_string)
    embed = discord.Embed(
      title=post["embed"]["title"],
      description=f'{embed_description}',
      color=discord.Color.from_rgb(251, 112, 5)
    )
    embed.set_thumbnail(url=post["thumbnail_url"])
    list_of_reactions = []

    if len(post["reactions"]) > 0:
      for reaction in post["reactions"]:
        role = discord.utils.get(bot.guilds[0].roles,name=reaction["role"])
        if reaction.get('separator'):
          embed_desc = "━━━━━━━━━━━━━━━"
        else:
          embed_desc = f'{reaction["emoji"]} for {role.mention} ({len(role.members)})'
          if reaction.get("description"):
            embed_desc += f"\n{reaction['description']}\n"
        list_of_reactions.append(embed_desc)
      # one field with lots of content and a blank name
      embed.add_field(
        name="⠀",
        value="\n".join(list_of_reactions),
        inline=False
      )
    embed.set_footer(text=post["embed"]["footer"])
    return embed

  # rebuild embeds (so role counts update)
  @tasks.loop(seconds=60)
  async def rebuild_embeds(self):
    rr = self.reaction_roles
    for message_id in rr:
      message_name = rr[message_id]["message_name"]
      message = self.roles_channel.get_partial_message(message_id)
      new_embed = self.build_react_embed(self.reaction_data[message_name]) # rebuild the embed
      await message.edit(embed=new_embed)
      await self.add_role_reactions(message, self.reaction_data[message_name]["reactions"])
      await asyncio.sleep(10)