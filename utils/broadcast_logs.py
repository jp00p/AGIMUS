import asyncio
import json
import logging
from threading import Thread
import websockets

from utils.config_utils import get_config

# To enable broadcast logging, add the following to your local config file
# as defined in .env as BOT_LOCAL_CONFIGURATION_FILEPATH
# {
#   "broadcast_logs": true
# }
#

config = get_config()
broadcast_enabled = config.get("broadcast_logs")

class BroadcastHandler(logging.Handler):
  def emit(self, record):
    """
    Broadcast Log Lines via Websockets
    """

    if not broadcast_enabled:
      return

    log_line = record.getMessage()
    new_loop.call_soon_threadsafe(q.put_nowait, log_line)

# Websocket Handler
async def socket_handler(websocket, path):
  await websocket.send("'You have connected successfully'")
  try:
    while True:
      message = await q.get()
      await websocket.send(json.dumps(message))
  except websockets.exceptions.ConnectionClosed:
    # No Op
    pass

new_loop = asyncio.new_event_loop()
q = asyncio.Queue(loop=new_loop)

# Start Websocket Server
if broadcast_enabled:
  def start_loop(loop, server):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server)
    loop.run_forever()

  start_server = websockets.serve(socket_handler, "0.0.0.0", 7890, loop=new_loop, ping_interval=None)
  t = Thread(target=start_loop, args=(new_loop, start_server), daemon=True)
  t.start()
