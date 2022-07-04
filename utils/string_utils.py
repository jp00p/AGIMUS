# String Utils
import re
import string

punct_regex = r'[' + string.punctuation + ']'
def strip_punctuation(string):
  return re.sub(punct_regex, '', string).lower().strip()
