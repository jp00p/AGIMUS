from common import *

from datetime import datetime, timedelta

alert_log = {}
alert_config = config["handlers"]["alerts"]

async def handle_alerts(message:discord.Message):
  alertworthy_users = alert_config["alertworthy_users"]
  alert_recipients = alert_config["alert_recipients"]

  author_id = message.author.id
  if author_id in alertworthy_users:
    recency_check_date = alert_log.get(author_id)
    if recency_check_date:
      check = datetime.now() - recency_check_date
      if check < timedelta(hours=2):
        # If we've already done an alert within 2 hours for this user, no need for another
        return

    # If we haven't already early returned from the check,
    # stamp the current time for this user in our in-memory alert_log
    alert_log[author_id] = datetime.now()

    # Alert recipients
    alertworthy_user = await bot.fetch_user(author_id)
    logger.info(f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}{alertworthy_user.display_name}{Style.RESET_ALL} is active on the Discord! {Fore.LIGHTCYAN_EX}{Style.BRIGHT}Sending alerts!{Style.RESET_ALL}{Fore.RESET}")
    for recipient_id in alert_recipients:
      recipient_user = await bot.fetch_user(recipient_id)
      await recipient_user.send(f"Hey {recipient_user.display_name}, looks like **{alertworthy_user.display_name}** is active on the Discord!\n{message.jump_url}")
    