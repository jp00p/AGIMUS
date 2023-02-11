from common import *

TILE_FLOOR =  "⬛"
TILE_WALL =   "🟫"
TILE_PLAYER = "😎"
TILE_OOB =    "🟦"
TILE_TREE =   "🔶"
TILE_PILL =   "💊"
TILE_ROOM =   "🟪"

class ExplorationMinigame(object):
  def __init__(self):
    self.map_height = 20
    self.map_width = 20
    self.map_list = []
    self.map_string = ""
    self.player_x = 0
    self.player_y = 0
    self.rooms = 5
    self.generate()

  def generate(self):

    ''' generate a random map with a wall around the edges '''
    
    map_list = []
    
    # for y in range(self.map_height):
    #   row = []
    #   for x in range(self.map_width):
    #     if x == 0 or x == self.map_width - 1 or y == 0 or y == self.map_height - 1:
    #       row.append(TILE_TILE_WALL)
    #     elif random.randint(0, 100) > 80:
    #       row.append(TILE_TILE_WALL)
    #     elif random.randint(0, 100) > 95:
    #       row.append(TILE_TREE)
    #     else:
    #       row.append(TILE_TILE_FLOOR)
    #   map_list.append(row)   
    # self.map_list = map_list
    
    # Generate the map using the cellular automata algorithm
    for y in range(self.map_height):
      row = []
      for x in range(self.map_width):
        if random.randint(0, 100) > 50:
          row.append(TILE_WALL)
        else:
          row.append(TILE_FLOOR)
      map_list.append(row)

    for i in range(5):
      new_map = []
      for y in range(self.map_height):
        row = []
        for x in range(self.map_width):
          wall_count = 0
          for dy in range(-1, 2):
            for dx in range(-1, 2):
              if x + dx < 0 or x + dx >= self.map_width or y + dy < 0 or y + dy >= self.map_height:
                continue  # Out of bounds
              if map_list[y + dy][x + dx] == TILE_WALL:
                wall_count += 1
          if wall_count > 4:
            row.append(TILE_FLOOR)
          elif wall_count < 4:
            row.append(TILE_WALL)
          else:
            row.append(map_list[y][x])
        new_map.append(row)
      map_list = list(new_map)

    self.map_list = map_list
    logger.info(self.map_list)
    self.place_player()
    self.map_string = self.build_string()

  def place_player(self):
    ''' place the player on a random valid floor tile '''
    
    while True:
      self.player_x = random.randint(1, self.map_width - 2)
      self.player_y = random.randint(1, self.map_height - 2)
      if self.map_list[self.player_y][self.player_x] == TILE_FLOOR:
        break

  def build_string(self):
    ''' 
    build the string of the map 
    includes a "camera" so the player doesn't see the WHOLE map at once
    '''
    message = ""
    for y in range(self.player_y - 6, self.player_y + 5):
      for x in range(self.player_x - 6, self.player_x + 5):
        if y < 0 or y >= self.map_height or x < 0 or x >= self.map_width:  # Out of bounds
          message += TILE_OOB
        elif x == self.player_x and y == self.player_y:  # Player position
          message += TILE_PLAYER
        else:
          message += self.map_list[y][x]
      message += "\n"
    message += ""
    return message

  def show_whole_map(self):
    message = "\n```\n"
    for y in range(0, self.map_height):
      for x in range(0, self.map_width):
        message += self.map_list[y][x]
      
      message += "\n"
    message += "```\n"
    return message

  def move(self, direction):
    # Calculate the new position of the player based on the direction
    if direction == "up":
      new_x = self.player_x
      new_y = self.player_y - 1
    elif direction == "down":
      new_x = self.player_x
      new_y = self.player_y + 1
    elif direction == "left":
      new_x = self.player_x - 1
      new_y = self.player_y
    elif direction == "right":
      new_x = self.player_x + 1
      new_y = self.player_y

    # Check if the new position is a valid move
    if new_x < 0 or new_x >= self.map_width or new_y < 0 or new_y >= self.map_height:
      return
    if self.map_list[new_y][new_x] == TILE_WALL:
      return

    # Update the player's position
    self.player_x = new_x
    self.player_y = new_y
    self.map_string = self.build_string()