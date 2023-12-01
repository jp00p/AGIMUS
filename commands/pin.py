from common import *
from utils.check_role_access import role_check

f = open("./data/pin_messages.json")
random_pin_messages = json.load(f)
f.close()


@bot.message_command(
  name="pin",
  description="Pin (Admin Only)"
)
@commands.check(role_check)
async def pin(ctx, message: discord.Message):
  pinning_user = ctx.author.display_name
  logger.info(
    f"{pinning_user} is pinning message {message.id} in {ctx.channel.name}")
  if message.pinned:
    await ctx.respond(f"Whoa there, this message is already pinned! No action taken.", ephemeral=True)
  else:
    await message.pin()
    await ctx.respond(f"Message pinned! 📌", ephemeral=True)
    await ctx.channel.send(random.choice(random_pin_messages["messages"]).format(user=pinning_user))


@bot.message_command(
  name="unpin",
  description="Unpin (Admin Only)"
)
@commands.check(role_check)
async def unpin(ctx, message: discord.Message):
  pinning_user = ctx.author.display_name
  logger.info(
    f"{ctx.author.display_name} is unpinning message {message.id} in {ctx.channel.name}")
  if not message.pinned:
    await ctx.respond(f"Whoa there, can't unpin this message because it is not already pinned! No action taken.", ephemeral=True)
  else:
    await message.unpin()
    await ctx.respond(f"Message unpinned! 💢", ephemeral=True)
