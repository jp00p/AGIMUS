import mysql.connector
from common import *

dbconfig = {
  "host": DB_HOST,
  "user": DB_USER,
  "database": DB_NAME,
  "password": DB_PASS
}

connection_pool = mysql.connector.pooling.MySQLConnectionPool(
  pool_name="agimuspool",
  pool_size=8,
  **dbconfig
)

class AgimusDB:
  """Database wrapper for AGIMUS with connection pooling"""

  def __init__(self, dictionary=False, buffered=False, multi=False):
    self.db = None
    self.cursor = None
    self.dictionary = dictionary
    self.buffered = buffered
    self.multi = multi

  def __enter__(self):
    self.db = connection_pool.get_connection()
    self.cursor = self.db.cursor(dictionary=self.dictionary, buffered=self.buffered)
    return self.cursor

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.cursor:
      self.cursor.close()
    if self.db:
      if exc_type is None:
        self.db.commit()
      self.db.close()

  def __del__(self):
    if hasattr(self, 'cursor') and self.cursor:
      self.cursor.close()
    if hasattr(self, 'db') and self.db:
      try:
        self.db.close()
      except:
        pass