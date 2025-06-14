# String Utils
import random
import re
import string
from io import StringIO
from html.parser import HTMLParser
punct_regex = r'[' + string.punctuation + ']'
emoji_regex = r':[^\t\n\f\r ]+:'
tag_regex = r'<@[^\t\n\f\r ]+>'
match_discord_emoji = re.compile('<:.*?>')
match_urls = re.compile('https?:\/\/\S*')
#match_all_punctuation = re.escape(string.punctuation)

# 1000 most common english words (https://gist.github.com/deekayen/4148741)
common_words = ["the","of","to","and","a","in","is","it","you","that","he","was","for","on","are","with","as","I","his","they","be","at","one","have","this","from","or","had","by","not","word","but","what","some","we","can","out","other","were","all","there","when","up","use","your","how","said","an","each","she","which","do","their","time","if","will","way","about","many","then","them","write","would","like","so","these","her","long","make","thing","see","him","two","has","look","more","day","could","go","come","did","number","sound","no","most","people","my","over","know","water","than","call","first","who","may","down","side","been","now","find","any","new","work","part","take","get","place","made","live","where","after","back","little","only","round","man","year","came","show","every","good","me","give","our","under","name","very","through","just","form","sentence","great","think","say","help","low","line","differ","turn","cause","much","mean","before","move","right","boy","old","too","same","tell","does","set","three","want","air","well","also","play","small","end","put","home","read","hand","port","large","spell","add","even","land","here","must","big","high","such","follow","act","why","ask","men","change","went","light","kind","off","need","house","picture","try","us","again","animal","point","mother","world","near","build","self","earth","father","head","stand","own","page","should","country","found","answer","school","grow","study","still","learn","plant","cover","food","sun","four","between","state","keep","eye","never","last","let","thought","city","tree","cross","farm","hard","start","might","story","saw","far","sea","draw","left","late","run","don't","while","press","close","night","real","life","few","north","open","seem","together","next","white","children","begin","got","walk","example","ease","paper","group","always","music","those","both","mark","often","letter","until","mile","river","car","feet","care","second","book","carry","took","science","eat","room","friend","began","idea","fish","mountain","stop","once","base","hear","horse","cut","sure","watch","color","face","wood","main","enough","plain","girl","usual","young","ready","above","ever","red","list","though","feel","talk","bird","soon","body","dog","family","direct","pose","leave","song","measure","door","product","black","short","numeral","class","wind","question","happen","complete","ship","area","half","rock","order","fire","south","problem","piece","told","knew","pass","since","top","whole","king","space","heard","best","hour","better","true","during","hundred","five","remember","step","early","hold","west","ground","interest","reach","fast","verb","sing","listen","six","table","travel","less","morning","ten","simple","several","vowel","toward","war","lay","against","pattern","slow","center","love","person","money","serve","appear","road","map","rain","rule","govern","pull","cold","notice","voice","unit","power","town","fine","certain","fly","fall","lead","cry","dark","machine","note","wait","plan","figure","star","box","noun","field","rest","correct","able","pound","done","beauty","drive","stood","contain","front","teach","week","final","gave","green","oh","quick","develop","ocean","warm","free","minute","strong","special","mind","behind","clear","tail","produce","fact","street","inch","multiply","nothing","course","stay","wheel","full","force","blue","object","decide","surface","deep","moon","island","foot","system","busy","test","record","boat","common","gold","possible","plane","stead","dry","wonder","laugh","thousand","ago","ran","check","game","shape","equate","hot","miss","brought","heat","snow","tire","bring","yes","distant","fill","east","paint","language","among","grand","ball","yet","wave","drop","heart","am","present","heavy","dance","engine","position","arm","wide","sail","material","size","vary","settle","speak","weight","general","ice","matter","circle","pair","include","divide","syllable","felt","perhaps","pick","sudden","count","square","reason","length","represent","art","subject","region","energy","hunt","probable","bed","brother","egg","ride","cell","believe","fraction","forest","sit","race","window","store","summer","train","sleep","prove","lone","leg","exercise","wall","catch","mount","wish","sky","board","joy","winter","sat","written","wild","instrument","kept","glass","grass","cow","job","edge","sign","visit","past","soft","fun","bright","gas","weather","month","million","bear","finish","happy","hope","flower","clothe","strange","gone","jump","baby","eight","village","meet","root","buy","raise","solve","metal","whether","push","seven","paragraph","third","shall","held","hair","describe","cook","floor","either","result","burn","hill","safe","cat","century","consider","type","law","bit","coast","copy","phrase","silent","tall","sand","soil","roll","temperature","finger","industry","value","fight","lie","beat","excite","natural","view","sense","ear","else","quite","broke","case","middle","kill","son","lake","moment","scale","loud","spring","observe","child","straight","consonant","nation","dictionary","milk","speed","method","organ","pay","age","section","dress","cloud","surprise","quiet","stone","tiny","climb","cool","design","poor","lot","experiment","bottom","key","iron","single","stick","flat","twenty","skin","smile","crease","hole","trade","melody","trip","office","receive","row","mouth","exact","symbol","die","least","trouble","shout","except","wrote","seed","tone","join","suggest","clean","break","lady","yard","rise","bad","blow","oil","blood","touch","grew","cent","mix","team","wire","cost","lost","brown","wear","garden","equal","sent","choose","fell","fit","flow","fair","bank","collect","save","control","decimal","gentle","woman","captain","practice","separate","difficult","doctor","please","protect","noon","whose","locate","ring","character","insect","caught","period","indicate","radio","spoke","atom","human","history","effect","electric","expect","crop","modern","element","hit","student","corner","party","supply","bone","rail","imagine","provide","agree","thus","capital","won't","chair","danger","fruit","rich","thick","soldier","process","operate","guess","necessary","sharp","wing","create","neighbor","wash","bat","rather","crowd","corn","compare","poem","string","bell","depend","meat","rub","tube","famous","dollar","stream","fear","sight","thin","triangle","planet","hurry","chief","colony","clock","mine","tie","enter","major","fresh","search","send","yellow","gun","allow","print","dead","spot","desert","suit","current","lift","rose","continue","block","chart","hat","sell","success","company","subtract","event","particular","deal","swim","term","opposite","wife","shoe","shoulder","spread","arrange","camp","invent","cotton","born","determine","quart","nine","truck","noise","level","chance","gather","shop","stretch","throw","shine","property","column","molecule","select","wrong","gray","repeat","require","broad","prepare","salt","nose","plural","anger","claim","continent","oxygen","sugar","death","pretty","skill","women","season","solution","magnet","silver","thank","branch","match","suffix","especially","fig","afraid","huge","sister","steel","discuss","forward","similar","guide","experience","score","apple","bought","led","pitch","coat","mass","card","band","rope","slip","win","dream","evening","condition","feed","tool","total","basic","smell","valley","nor","double","seat","arrive","master","track","parent","shore","division","sheet","substance","favor","connect","post","spend","chord","fat","glad","original","share","station","dad","bread","charge","proper","bar","offer","segment","slave","duck","instant","market","degree","populate","chick","dear","enemy","reply","drink","occur","support","speech","nature","range","steam","motion","path","liquid","log","meant","quotient","teeth","shell","neck"]
more_stopwords = ["profile", "help", "wordcloud", "quiz", "trivia", "slots", "poker", "set_tagline", "reports", "badges", "trade", "agimus", "one", "ive", "ill", "hes", "shes", "thats", "theyll", "theyve", "weve", "theirs", "wont", "lets", "dont", "cant", "didnt", "wouldnt", "couldnt", "shouldnt", "havent", "doesnt", "youre", "whats", "hasnt", "wouldve", "shouldve", "couldve", "hell", "shell", "something", "really", "theres", "there", "yeah", "get", "getting", "theyre", "they're", "actually", "maybe", "probably", "yes", "no", "make", "makes", "gotta", "okay", "ok", "stuff"]

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

def strip_emoji(string) -> string:
  """ remove discord emoji from a string """
  string = re.sub(match_discord_emoji, '', string)
  string = re.sub(emoji_regex, '', string)
  return string

def strip_urls(string) -> string:
  """ remove any urls (http[s]) from the string """
  return re.sub(match_urls, '', string)

def plaintext(string) -> string:
  """ turns a string into plain ASCII text """
  return string.encode("ascii", errors="ignore").decode().strip()


def is_loud(message: str) -> bool:
  """After stripping out allowed characters, return if the remaining string is uppercase or not"""
  # Strip out emojis because these are ok to be lowercase (and will not work as uppercase)
  message = strip_emoji(message).strip()
  # If stripping out a tag changes the message, then it had a tag and we shouldn't record it.
  if re.search(tag_regex, message):
    return False
  # Strip out any punctuation
  message = re.sub(punct_regex, '', message)
  # Only save shouts that are 3 or more characters
  if len(message) < 3:
    return False
  # If the message forced to uppercase matches the string itself, it is LOUD
  return message.upper() == message and message.lower() != message

def is_crystals(message: str) -> bool:
  """After stripping out allowed characters, return if the remaining string contains 'crystals' or not"""
  # Strip out emojis because these are ok to be lowercase (and will not work as uppercase)
  message = strip_emoji(message).strip()
  # If stripping out a tag changes the message, then it had a tag and we shouldn't trigger
  if re.search(tag_regex, message):
    return False
  # Strip out any punctuation (this doesn't really matter but whatever)
  message = re.sub(punct_regex, '', message)
  # Only trigger on messages that have some length to them
  word_count = len(message.split())
  required_min = random.randint(3, 6)
  if word_count < required_min:
    return False
  # If the message lowercased contains "crystals" return true
  return 'crystal' in message.lower()

def escape_discord_formatting(text: str) -> str:
  """
  Escapes characters in a string that Discord uses for Markdown formatting.
  """
  return re.sub(r'([\\*_~`|])', r'\\\1', text)

BULLSHIT_CHARACTERS = {
  '‘': "'",       # left single quote
  '’': "'",       # right single quote
  '“': '"',       # left double quote
  '”': '"',       # right double quote
  '–': '-',       # en dash
  '—': '-',       # em dash
  '−': '-',       # minus sign
  '…': '...',     # ellipsis
  '\u00A0': ' ',  # non-breaking space
  '\u200B': '',   # zero-width space
  '\u200C': '',   # zero-width non-joiner
  '\u200D': '',   # zero-width joiner
}

def strip_bullshit(text: str) -> str:
  """
  Normalize smart quotes, dashes, ellipses, and exotic spaces to ASCII equivalents.
  Remove this fukin garbage from Discord inputs.
  """
  return ''.join(BULLSHIT_CHARACTERS.get(c, c) for c in text)