# Channel Helpers
import discord

from common.config_utils import deep_dict_update, config


def get_channel_ids_list(channel_list: list[str]) -> list[int]:
  channel_list = list(channel_list)
  channel_list.sort()
  channel_ids = [
    get_channel_id(x) for x in channel_list
  ]
  return channel_ids

def get_channel_id(channel_identifier: str) -> int:
  if isinstance(channel_identifier, str):
    id = config["channels"].get(channel_identifier)
  else:
    id = channel_identifier
  return id


def generate_local_channel_list(client: discord.Bot):
  """
  This runs to apply the local channel list on top of the existing channel config
  """
  if client.guilds[0]:
    channels = client.guilds[0].channels + client.guilds[0].threads + client.guilds[0].voice_channels + client.guilds[0].forum_channels
    channel_list = {
      channel.name.encode("ascii", errors="ignore").decode().strip() : channel.id
      for channel in channels
    }
    # channel_list_json = json.dumps(channel_list, indent=2, sort_keys=True)
    updated_channel_list = deep_dict_update({ "channels": config['channels'] }, { "channels" : channel_list })
    config["channels"] = updated_channel_list["channels"]
