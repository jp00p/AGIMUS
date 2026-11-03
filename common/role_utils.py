# Role Helpers
from common.config_utils import deep_dict_update, config


def get_role_ids_list(role_list):
  role_list = list(role_list)
  role_list.sort()
  role_ids = [
    get_role_id(x) for x in role_list
  ]
  return role_ids

def get_role_id(role_identifier):
  if isinstance(role_identifier, str):
    id = config["role_map"].get(role_identifier)
  else:
    id = role_identifier
  return id

def generate_local_role_map(client):
  """
  This runs to apply the local role map (name to id) on top of the existing role map config
  """
  if client.guilds[0]:
    roles = client.guilds[0].roles
    role_map = {
      role.name.encode("ascii", errors="ignore").decode().strip() : role.id
      for role in roles
    }
    # role_map_json = json.dumps(role_map, indent=2, sort_keys=True)
    updated_role_map = deep_dict_update({ "role_map": config['role_map'] }, { "role_map" : role_map })
    config["role_map"] = updated_role_map["role_map"]
