import mysql.connector
from common import *

class AgimusDB():
  """Database wrapper for AGIMUS

  utilizes context managers for less repeating code.

  ----
  Usage: 
  ```
  with AgimusDB() as query:
    sql = "INSERT INTO table (col) VALUES (%s)"
    vals = (user_id,)
    query.execute(sql, vals)
  ```
  
  ----
  Returns:

  `mysql.connection.Cursor`
    A self-closing cursor to work with

  """
  def __init__(self, cursor_dict=False):
    self.db = None
    self.cursor = None
    self.cursor_dict = cursor_dict

  def __enter__(self):
    """ context manager opening """
    self.db = mysql.connector.connect(
      host=DB_HOST,
      user=DB_USER,
      database=DB_NAME,
      password=DB_PASS,
    )
    self.cursor = self.db.cursor(dictionary=self.cursor_dict)
    return self.cursor

  def __exit__(self, exc_class, exc, traceback):
    """ context manager closing """
    self.db.commit()
    self.cursor.close()
    self.db.close()