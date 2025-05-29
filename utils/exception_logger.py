from common import *


# In-memory exception log buffer
exception_log_lines: list[str] = []


def setup_exception_logging():
  """
  Call this once during bot startup to install global exception hooks.
  """
  sys.excepthook = _handle_sync_exception
  loop = asyncio.get_event_loop()
  loop.set_exception_handler(_handle_async_exception)


def _handle_sync_exception(exc_type, exc_value, exc_traceback):
  if issubclass(exc_type, KeyboardInterrupt):
    return
  tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
  exception_log_lines.append(tb_str)

  # Also print to terminal (stderr)
  sys.__stderr__.write(tb_str)
  sys.__stderr__.flush()


def _handle_async_exception(loop, context):
  exception = context.get("exception")
  if exception:
    tb_str = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
  else:
    tb_str = str(context.get("message"))
  exception_log_lines.append(tb_str)

  # Also print to terminal (stderr)
  sys.__stderr__.write(tb_str + '\n')
  sys.__stderr__.flush()


async def send_exception_log(bot: discord.Bot, channel_id: int):
  """
  Sends the current exception log buffer to the specified Discord channel as a .txt file.
  Clears the buffer after sending.
  """
  if not exception_log_lines:
    return

  channel = bot.get_channel(channel_id)
  if not channel:
    return

  log_content = '\n\n'.join(exception_log_lines)
  log_file = io.StringIO(log_content)
  log_file.name = 'agimus_exceptions.txt'  # Required for Discord to treat it as a file

  await channel.send(
    content="## AGIMUS Exception Report ⚠️",
    file=discord.File(log_file)
  )

  exception_log_lines.clear()


def exception_report_task(bot):
  async def send_report():
    if not exception_log_lines:
      return

    enabled = config["tasks"].get("exception_report", {}).get("enabled", False)
    if not enabled:
      return

    try:
      channel_ids = get_channel_ids_list(config["tasks"]["exception_report"]["channels"])
      for channel_id in channel_ids:
        await send_exception_log(bot, channel_id)
    except Exception as e:
      sys.__stderr__.write(f"[Exception Reporter Error] {e}\n")

  return {
    "task": send_report,
    "crontab": config["tasks"]["exception_report"]["crontab"]
  }
