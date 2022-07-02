from pprint import pprint
from discord_components import DiscordComponents, Button, Select, SelectOption

from .common import *

DiscordComponents(client)


# restrict_emojis() - Entrypoint for !restrict_emojis command
# message[required]: discord.Message
# This command can be used to update an emoji's restriction-by-role status.
# It uses the discord_components library to generate the interface!
async def restrict_emojis(message:discord.Message):
  guild = message.guild

  # Gather Guild Emojis
  emojis = await guild.fetch_emojis()
  emojis = sorted(emojis, key = lambda e: e.name)

  emoji_options = []
  for emoji in emojis:
    option = SelectOption(
      label=emoji.name,
      emoji=emoji,
      value=emoji.id
    )
    emoji_options.append(option)

  # Gather Guild Roles
  roles = await message.guild.fetch_roles()
  roles = sorted(roles, key = lambda e: e.name)

  role_options = []
  for role in roles:
    option = SelectOption(
      label=role.name,
      value=role.id
    )
    role_options.append(option)

  # Send Initial Emoji Selection Prompt
  selection_reply = await message.reply(
    embed=discord.Embed(
      title="🔒 Restrict Emojis 🔒",
      description="Select the Emoji you would like to restrict from the following list:"
    ),
    components=[
      Select(
        placeholder="Select an emoji!",
        options=emoji_options
      )
    ]
  )
  
  # Confirm Selection and Prompt With Button Options
  selection_interaction = await client.wait_for("select_option")
  selected_emoji_id = selection_interaction.values[0]
  # selected_emoji = await guild.fetch_emoji()
  selected_emoji = None
  for emoji in emojis:
    if emoji.id == int(selected_emoji_id):
      selected_emoji = emoji
      break

  # Select current Emoji Roles and determine what information to display to the user
  emoji_roles = selected_emoji.roles
  emoji_roles_description = 'This Emoji is not currently restricted to any roles.\n'
  if len(emoji_roles):
    emoji_roles_string = ' '.join(list(map(lambda r: r.name, emoji_roles)))
    emoji_roles_description = f"This Emoji is currently restricted to the following roles:\n\n{emoji_roles_string}\n"

  # Remove the previous reply and send a new message with the action buttons
  await selection_reply.delete()

  action_reply = await selection_interaction.send(
    embed=discord.Embed(
      title=f"Selected Emoji: {selected_emoji}",
      description=f"{emoji_roles_description}\nWhich action would you to apply?"
    ),
    components=[
      Button(
        label="Restrict Emoji To Role",
        style=1,
        custom_id="restrict",
        emoji="🔒"
      ),
      Button(
        label="Remove Restriction From Role",
        style=1,
        custom_id="remove",
        emoji="🗝️"
      ),
      Button(
        label="Clear All Role Restictions From Emoji",
        style=2,
        custom_id="clear",
        emoji="☑️"
      ),
    ],
    ephemeral=False
  )

  action_interaction = await client.wait_for("button_click")
  selected_action = action_interaction.custom_id

  await action_reply.delete()

  # If we're doing a clear action go ahead and fire
  if selected_action == 'clear':
    await selected_emoji.edit(roles=[])
    await action_interaction.send(
      embed=discord.Embed(
        title="Success!",
        description=f"All role restrictions have been cleared from {selected_emoji}!",
        color=discord.Color.green(),
      ),
      ephemeral=False
    )
    return

  # If we're restricting or removing, prompt for the role to interact with
  role_reply = await action_interaction.send(
    embed=discord.Embed(
      title=f"{selected_action.title()}:",
      description=f"Which Role would you like to apply to {selected_emoji}?"
    ),
    components=[
      Select(
        placeholder="Select a Role!",
        options=role_options
      )
    ],
    ephemeral=False
  )

  # Determine which action they've taken and retrieve the selected Role and gather Emoji Roles
  role_interaction = await client.wait_for("select_option")
  selected_role_id = role_interaction.values[0]
  selected_role = None
  for role in roles:
    if role.id == int(selected_role_id):
      selected_role = role
      break

  emoji_roles = selected_emoji.roles

  await role_reply.delete()
  if selected_action == 'restrict':
    if selected_role in emoji_roles:
      await role_interaction.send(
        embed=discord.Embed(
          title="Nah.",
          description=f"{selected_role.name} is already part of the restriction list for {selected_emoji}!",
          color=discord.Color.orange(),
        )
      )
      return
    else:
      emoji_roles.append(selected_role)
      await selected_emoji.edit(roles=emoji_roles)
      await role_interaction.send(
        embed=discord.Embed(
          title="Success!",
          description=f"{selected_role.name} has been successfully added to the restriction list for {selected_emoji}!",
          color=discord.Color.green(),
        )
      )
      return
  elif selected_action == 'remove':
    if selected_role not in emoji_roles:
      await role_interaction.send(
        embed=discord.Embed(
          title="Nah.",
          description=f"{selected_role.name} is not currently in the restriction list for {selected_emoji}!",
          color=discord.Color.orange(),
        )
      )
      return
    else:
      emoji_roles.remove(selected_role)
      await selected_emoji.edit(roles=emoji_roles)
      await role_interaction.send(
        embed=discord.Embed(
          title="Success!",
          description=f"{selected_role.name} has been successfully removed from the restriction list for {selected_emoji}!",
          color=discord.Color.green(),
        )
      )
      return

