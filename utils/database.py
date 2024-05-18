import aiomysql
from common import *

class AgimusDB:
  """Asynchronous Database wrapper for AGIMUS with connection pooling"""

  def __init__(self, dictionary=False):
    self.pool = None
    self.conn = None
    self.cursor = None
    self.dictionary = dictionary

  async def __aenter__(self):
    if not self.pool:
      self.pool = await aiomysql.create_pool(
        host=DB_HOST,
        port=3306,
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        autocommit=True,
        minsize=1,
        maxsize=5
      )
    self.conn = await self.pool.acquire()
    self.cursor = await self.conn.cursor(aiomysql.DictCursor if self.dictionary else aiomysql.Cursor)
    return self.cursor

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    if self.cursor:
      await self.cursor.close()
    if self.conn:
      self.pool.release(self.conn)
