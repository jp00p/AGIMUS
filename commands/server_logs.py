from .common import *



# show_leave_message(member) - shows a message when someone leaves the server
# member[required]: discord.Member
async def show_leave_message(member):
    if member.bot:
        return

    server_log_channel = bot.get_channel(config["channels"]["captains-log"])
    name = member.display_name
    msg = random.choice(config["leave_messages"]).format(name)
    msg += f" (Join date: {member.joined_at})"
    logger.info(f"{Fore.LIGHTRED_EX}{name} has left the server! :({Fore.RESET}")
    await server_log_channel.send(msg)

# show_nick_change_message(before,after) - shows a message when someone changes their nickname on the server
# before[required]: discord.Member
# after[required]: discord.Member
async def show_nick_change_message(before,after):
    if before.bot or after.bot:
        return

    server_log_channel = bot.get_channel(config["channels"]["captains-log"])
    msg = f"**{before.display_name}** has changed their nickname to: **{after.display_name}**"
    logger.info(f"{Fore.LIGHTGREEN_EX}{before.display_name}{Fore.RESET} has changed their nickname to: {Fore.GREEN}{after.display_name}{Fore.RESET}")
    await server_log_channel.send(msg)