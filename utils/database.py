import aiomysql
from common import *

class AgimusDB:
  """Asynchronous Database wrapper for AGIMUS with connection pooling"""

  _pool = None

  def __init__(self, dictionary=False):
    self.conn = None
    self.cursor = None
    self.dictionary = dictionary

  @classmethod
  async def init_pool(cls):
    if cls._pool is None:
      cls._pool = await aiomysql.create_pool(
        host=DB_HOST,
        port=3306,
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        autocommit=True,
        minsize=1,
        maxsize=20
      )

  async def __aenter__(self):
    await self.init_pool()
    self.conn = await self._pool.acquire()
    self.cursor = await self.conn.cursor(aiomysql.DictCursor if self.dictionary else aiomysql.Cursor)
    return self.cursor

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    try:
      if self.cursor:
        await self.cursor.close()
    except Exception as e:
      logger.error(f"Error closing cursor: {e}", exc_info=True)

    try:
      if self.conn:
        # swallow double‑release assertions
        try:
          self._pool.release(self.conn)
        except AssertionError:
          # connection wasn’t checked out or already returned—ignore
          pass
    except Exception:
      logger.error("Error releasing connection", exc_info=True)