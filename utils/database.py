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


class AgimusTransactionDB:
  """
  Manual transaction DB connection.
  Requires explicit `await db.begin()` and then a `await db.commit()` or `await db.rollback()`.
  If neither is called before exiting, a RuntimeError is raised and rollback is performed.
  """
  def __init__(self, dictionary=False):
    self.conn = None
    self.cursor = None
    self.dictionary = dictionary
    self._finalized = False

  async def __aenter__(self):
    self.conn = await aiomysql.connect(
      host=DB_HOST,
      port=3306,
      user=DB_USER,
      password=DB_PASS,
      db=DB_NAME,
      autocommit=False
    )
    self.cursor = await self.conn.cursor(aiomysql.DictCursor if self.dictionary else aiomysql.Cursor)
    return self

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    try:
      if exc_type:
        await self.conn.rollback()
        logger.warning("[AgimusTransactionDB] Exception occurred — transaction rolled back.")
      elif not self._finalized:
        await self.conn.rollback()
        logger.error(
          "[AgimusTransactionDB] FATAL: Transaction exited without commit() or rollback(). "
          "Changes have been rolled back automatically."
        )
        raise RuntimeError(
          "AgimusTransactionDB: Transaction exited without explicit commit() or rollback(). "
          "You must finalize all transactions."
        )
    finally:
      try:
        if self.cursor:
          await self.cursor.close()
        if self.conn:
          self.conn.close()
      except Exception as e:
        logger.error(f"[AgimusTransactionDB] Cleanup error: {e}", exc_info=True)

  async def execute(self, sql, params=None):
    await self.cursor.execute(sql, params)

  async def executemany(self, sql, param_list):
    await self.cursor.executemany(sql, param_list)

  async def fetchone(self):
    return await self.cursor.fetchone()

  async def fetchall(self):
    return await self.cursor.fetchall()

  async def begin(self):
    await self.conn.begin()

  async def commit(self):
    await self.conn.commit()
    self._finalized = True

  async def rollback(self):
    await self.conn.rollback()
    self._finalized = True

