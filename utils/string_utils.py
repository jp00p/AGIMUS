# String Utils
import string
import re

punct_regex = r'[' + string.punctuation + ']'
def strip_punctuation(string):
  return re.sub(punct_regex, '', string).lower().strip()
