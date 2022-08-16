# String Utils
import re
import string
from io import StringIO
from html.parser import HTMLParser
punct_regex = r'[' + string.punctuation + ']'
emoji_regex = r':[^\t\n\f\r ]+:'
tag_regex = r'<@[^\t\n\f\r ]+>'

# https://stackoverflow.com/a/925630/11767474
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()
    def handle_data(self, d):
        self.text.write(d)
    def get_data(self):
        return self.text.getvalue()

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def strip_punctuation(string):
  return re.sub(punct_regex, '', string).lower().strip()

# After stripping out allowed characters, return if the remaining string is uppercase or not
def is_loud(message):
  # Strip out emojis because these are ok to be lowercase (and will not work as uppercase)
  message = re.sub(emoji_regex, '', message).strip()
  # Strip out tagging of specific people because future pokes are fun
  message = re.sub(tag_regex, '', message)
  # Strip out any punctuation
  message = re.sub(punct_regex, '', message)
  # Only save shouts that are 3 or more characters
  if len(message) < 3:
    return False
  # If the message forced to uppercase matches the string itself, it is LOUD
  return message.upper() == message
