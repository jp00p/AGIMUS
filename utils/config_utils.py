import collections
import json
import os

BOT_CONFIGURATION_FILEPATH = os.getenv('BOT_CONFIGURATION_FILEPATH')
BOT_LOCAL_CONFIGURATION_FILEPATH = os.getenv('BOT_LOCAL_CONFIGURATION_FILEPATH')

def get_config():
  config = load_json(BOT_CONFIGURATION_FILEPATH)

  if BOT_LOCAL_CONFIGURATION_FILEPATH:
    local_config = load_json(BOT_LOCAL_CONFIGURATION_FILEPATH)
    config = deep_dict_update(config, local_config)

  return config


def load_json(path):
  f = open(path)
  loaded = json.load(f)
  f.close()
  return loaded

def deep_dict_update(source, overrides):
  for key, value in overrides.items():
    if isinstance(value, collections.abc.Mapping) and value:
      returned = deep_dict_update(source.get(key, {}), value)
      source[key] = returned
    else:
      source[key] = overrides[key]
  return source