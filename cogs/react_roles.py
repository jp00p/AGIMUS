from common import *

class ReactRoles(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.roles_channel = None
    self.message_names = ["pronouns", "locations", "departments", "notifications"]
    self.reaction_roles = {} # role list
    self.reaction_data = {} # base json data
    self.reaction_db_data = self.get_reaction_db_data() # db data
    for message_type in self.message_names:
      f = open(f"./data/react_roles/{message_type}.json")
      self.reaction_data[message_type] = json.load(f) # fill the base json for our messages
      f.close()
  
  @commands.Cog.listener()
  async def on_ready(self):
    # load role dict for reaction parsing
    self.roles_channel = self.bot.get_channel(config["channels"]["roles-and-pronouns"])
    self.reaction_roles = self.load_role_reactions()

  # listen to raw reaction additions
  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload:discord.RawReactionActionEvent):
    if payload.member.bot:
      return
    if payload.channel_id == self.roles_channel.id:
      await self.parse_reaction(payload)

  # build reaction role dict for handling reacts
  def load_role_reactions(self):
    response = {}
    for rdb in self.reaction_db_data:
      if rdb["reaction_type"]:
        message_id = rdb["message_id"]
        message_name = rdb["message_name"]
        response[message_id] = { "reactions": {}, "reaction_type": rdb["reaction_type"] }
        # loop over json and pull out emoji:role_id
        for rr in self.reaction_data[message_name]["reactions"]:
          response[message_id]["reactions"][rr["emoji"]] = discord.utils.get(bot.guilds[0].roles,name=rr["role"])
    return response

  async def parse_reaction(self, payload:discord.RawReactionActionEvent):
    # determine what to do with this reaction
    # either add or remove role(s)
    data = self.reaction_roles.get(str(payload.message_id))
    reaction_type = data.get("reaction_type")
    user = self.bot.guilds[0].get_member(payload.user_id)
    logger.info(payload.message_id)
    message = self.roles_channel.get_partial_message(payload.message_id)
    role = data["reactions"].get(str(payload.emoji))
    await message.remove_reaction(payload.emoji, user)
    logger.info(data)
    logger.info(user)
    logger.info(role)

    if user and role:
      logger.info("Role and user found")

      if user.get_role(role.id) == None:
        logger.info("Adding role")
        # add role!
        await user.add_roles(role, reason="ReactionRole")
        # if its a single type reaction, remove all other roles
        if reaction_type == "single":
          roles_to_remove = []
          for rr in data["reactions"].values():
            if rr.id != role.id:
              roles_to_remove.append(rr)
          if len(roles_to_remove) > 0:
            await user.remove_roles(*roles_to_remove, reason="ReactionRole")
      else:
        # remove role!
        if user.get_role(role.id) != None:
          await user.remove_roles(role, reason="ReactionRole")


  # updates db with new message details and deletes old messages from db
  def store_reaction_data(self, header_id, message_id, message_name, reaction_type):
    header_message_name = f"{message_name}_header"
    db = getDB()
    
    sql = [
      "DELETE FROM reaction_role_messages WHERE message_name IN (%(message_name)s, %(header_name)s)", 
      "INSERT INTO reaction_role_messages (message_id, reaction_type, message_name) VALUES (%(message_id)s, %(reaction_type)s, %(message_name)s)",
      "INSERT INTO reaction_role_messages (message_id, message_name) VALUES (%(header_id)s, %(header_name)s)"
    ]
    vals = { 
      "message_name": message_name, 
      "header_name": header_message_name, 
      "message_id": message_id, 
      "header_id": header_id, 
      "reaction_type": reaction_type 
    }
    for q in sql:
      query = db.cursor()
      query.execute(q, vals)
      db.commit()
      query.close()
    db.close()
    
    
  # add initial reactions to message
  async def add_role_reactions(self, message, reacts):
    if len(reacts) > 0:
      for r in reacts:
        await message.add_reaction(r["emoji"])
        #role = discord.utils.get(ctx.guild.roles,name=r["role"])

  # get all existing reaction message data
  def get_reaction_db_data(self):
    db = getDB()
    sql = "SELECT * FROM reaction_role_messages"
    query = db.cursor(dictionary=True)
    query.execute(sql)
    reaction_data = query.fetchall()
    db.commit()
    query.close()
    db.close()
    return reaction_data

  # find the ID of the reaction messages from the DB
  def get_reaction_message_ids(self):
    db = getDB()
    query = db.cursor()
    sql = "SELECT message_id FROM reaction_role_messages;"
    query.execute(sql)
    reaction_message_ids = query.fetchall()
    db.commit()
    query.close()
    db.close()
    return [i[0] for i in reaction_message_ids]

  @commands.command()
  async def q_update_role_messages(self, ctx:discord.ApplicationContext):
    
    await ctx.message.delete()

    # if there are existing messages, remove them
    if self.reaction_db_data and len(self.reaction_db_data) > 0:
      for rm in self.reaction_db_data:
        message = None
        try:
          message = await self.roles_channel.fetch_message(rm["message_id"])
        except:
          logger.info("React role message not found, oh well! Moving on with my life.")
        else:
          if message:
            logger.info(f"Deleting old role message {message.id}")
            await message.delete()      
    
    # loop over all the reaction data and build out the messages
    for message_name, p in self.reaction_data.items():
      message_content = p["message_content"] # the plain message content
      embed = None # build the embed

      if p.get("header_image_url") != "":
        # post the header image first
        header_msg = await self.roles_channel.send(content=p["header_image_url"])

      if p.get("embed"):
        embed_description = p["embed"]["description"]
        if p.get("embed_channel_name_placeholder"):
          channel_string = f"<#{get_channel_id(config['channels'][p['embed_channel_name_placeholder']])}>"
          embed_description = embed_description.format(channel_string)

        embed = discord.Embed(
          title=p["embed"]["title"],
          description=f'{embed_description}',
          color=discord.Color.from_rgb(251, 112, 5)
        )
        embed.set_thumbnail(url=p["thumbnail_url"])
        list_of_reactions = []

        if len(p["reactions"]) > 0:
          for reaction in p["reactions"]:
            role = discord.utils.get(ctx.guild.roles,name=reaction["role"])
            embed_desc = f'{reaction["emoji"]} for {role.mention}'
            if reaction.get("description"):
              embed_desc += f"\n{reaction['description']}\n"
            list_of_reactions.append(embed_desc)
            
          embed.add_field(
            name="⠀",
            value="\n".join(list_of_reactions),
            inline=False
          )
        embed.set_footer(text=p["embed"]["footer"])
        # send the message
        react_role_msg = await self.roles_channel.send(content=message_content, embed=embed)
      
      # save some of the message details to the database
      self.store_reaction_data(header_msg.id, react_role_msg.id, message_name, p["reaction_type"])

      # add the reactions to the message
      await self.add_role_reactions(react_role_msg, p["reactions"])
    
    # update role reactions dict
    self.role_reactions = self.load_role_reactions()
    # reload db data
    self.reaction_db_data = self.get_reaction_db_data()