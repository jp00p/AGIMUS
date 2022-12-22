from common import *

TILE_GRASS =  "⬛"
TILE_WALL =   "⬜"
TILE_PLAYER = "😎"
TILE_OOB =    "🟦"
TILE_TREE =   "🔶"

class ExplorationMinigame(object):
  def __init__(self):
    self.map_height = 20
    self.map_width = 20
    self.map_list = []
    self.map_string = ""
    self.player_x = 0
    self.player_y = 0
    self.generate()

  def generate(self):
    ''' generate a random map with a wall around the edges '''
    map_list = []
    for y in range(self.map_height):
      row = []
      for x in range(self.map_width):
        if x == 0 or x == self.map_width - 1 or y == 0 or y == self.map_height - 1:
          row.append(TILE_WALL)
        elif random.randint(0, 100) > 80:
          row.append(TILE_WALL)
        elif random.randint(0, 100) > 95:
          row.append(TILE_TREE)
        else:
          row.append(TILE_GRASS)
      map_list.append(row)   
    self.map_list = map_list
    self.place_player()
    self.map_string = self.build_string()

  def place_player(self):
    ''' place the player on a random valid floor tile '''
    while True:
      self.player_x = random.randint(1, self.map_width - 2)
      self.player_y = random.randint(1, self.map_height - 2)
      if self.map_list[self.player_y][self.player_x] == TILE_GRASS:
        break

  def build_string(self):
    ''' 
    build the string repr of the map 
    includes a "camera"
    '''
    message = ""
    for y in range(self.player_y - 4, self.player_y + 3):
      for x in range(self.player_x - 4, self.player_x + 3):
        if y < 0 or y >= self.map_height or x < 0 or x >= self.map_width:  # Out of bounds
          message += TILE_OOB
        elif x == self.player_x and y == self.player_y:  # Player position
          message += TILE_PLAYER
        else:
          message += self.map_list[y][x]
      message += "\n"
    message += ""
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