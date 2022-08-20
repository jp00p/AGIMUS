from numpy import full
from common import *
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
from handlers.xp import increment_user_xp

class Wordcloud(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    
    # mask images
    self.image_masks = [
      Image.open("./images/cloud_masks/combadge_mask.png"),
      Image.open("./images/cloud_masks/ds9_mask.png"),
      Image.open("./images/cloud_masks/enterprise_d_mask.png"),
      Image.open("./images/cloud_masks/exocomp_mask.png"),
      Image.open("./images/cloud_masks/llap_mask.png"),
      Image.open("./images/cloud_masks/spock_mask.png")
    ]

    # 1000 most common english words (https://gist.github.com/deekayen/4148741)
    self.common_words = ["the","of","to","and","a","in","is","it","you","that","he","was","for","on","are","with","as","I","his","they","be","at","one","have","this","from","or","had","by","not","word","but","what","some","we","can","out","other","were","all","there","when","up","use","your","how","said","an","each","she","which","do","their","time","if","will","way","about","many","then","them","write","would","like","so","these","her","long","make","thing","see","him","two","has","look","more","day","could","go","come","did","number","sound","no","most","people","my","over","know","water","than","call","first","who","may","down","side","been","now","find","any","new","work","part","take","get","place","made","live","where","after","back","little","only","round","man","year","came","show","every","good","me","give","our","under","name","very","through","just","form","sentence","great","think","say","help","low","line","differ","turn","cause","much","mean","before","move","right","boy","old","too","same","tell","does","set","three","want","air","well","also","play","small","end","put","home","read","hand","port","large","spell","add","even","land","here","must","big","high","such","follow","act","why","ask","men","change","went","light","kind","off","need","house","picture","try","us","again","animal","point","mother","world","near","build","self","earth","father","head","stand","own","page","should","country","found","answer","school","grow","study","still","learn","plant","cover","food","sun","four","between","state","keep","eye","never","last","let","thought","city","tree","cross","farm","hard","start","might","story","saw","far","sea","draw","left","late","run","don't","while","press","close","night","real","life","few","north","open","seem","together","next","white","children","begin","got","walk","example","ease","paper","group","always","music","those","both","mark","often","letter","until","mile","river","car","feet","care","second","book","carry","took","science","eat","room","friend","began","idea","fish","mountain","stop","once","base","hear","horse","cut","sure","watch","color","face","wood","main","enough","plain","girl","usual","young","ready","above","ever","red","list","though","feel","talk","bird","soon","body","dog","family","direct","pose","leave","song","measure","door","product","black","short","numeral","class","wind","question","happen","complete","ship","area","half","rock","order","fire","south","problem","piece","told","knew","pass","since","top","whole","king","space","heard","best","hour","better","true","during","hundred","five","remember","step","early","hold","west","ground","interest","reach","fast","verb","sing","listen","six","table","travel","less","morning","ten","simple","several","vowel","toward","war","lay","against","pattern","slow","center","love","person","money","serve","appear","road","map","rain","rule","govern","pull","cold","notice","voice","unit","power","town","fine","certain","fly","fall","lead","cry","dark","machine","note","wait","plan","figure","star","box","noun","field","rest","correct","able","pound","done","beauty","drive","stood","contain","front","teach","week","final","gave","green","oh","quick","develop","ocean","warm","free","minute","strong","special","mind","behind","clear","tail","produce","fact","street","inch","multiply","nothing","course","stay","wheel","full","force","blue","object","decide","surface","deep","moon","island","foot","system","busy","test","record","boat","common","gold","possible","plane","stead","dry","wonder","laugh","thousand","ago","ran","check","game","shape","equate","hot","miss","brought","heat","snow","tire","bring","yes","distant","fill","east","paint","language","among","grand","ball","yet","wave","drop","heart","am","present","heavy","dance","engine","position","arm","wide","sail","material","size","vary","settle","speak","weight","general","ice","matter","circle","pair","include","divide","syllable","felt","perhaps","pick","sudden","count","square","reason","length","represent","art","subject","region","energy","hunt","probable","bed","brother","egg","ride","cell","believe","fraction","forest","sit","race","window","store","summer","train","sleep","prove","lone","leg","exercise","wall","catch","mount","wish","sky","board","joy","winter","sat","written","wild","instrument","kept","glass","grass","cow","job","edge","sign","visit","past","soft","fun","bright","gas","weather","month","million","bear","finish","happy","hope","flower","clothe","strange","gone","jump","baby","eight","village","meet","root","buy","raise","solve","metal","whether","push","seven","paragraph","third","shall","held","hair","describe","cook","floor","either","result","burn","hill","safe","cat","century","consider","type","law","bit","coast","copy","phrase","silent","tall","sand","soil","roll","temperature","finger","industry","value","fight","lie","beat","excite","natural","view","sense","ear","else","quite","broke","case","middle","kill","son","lake","moment","scale","loud","spring","observe","child","straight","consonant","nation","dictionary","milk","speed","method","organ","pay","age","section","dress","cloud","surprise","quiet","stone","tiny","climb","cool","design","poor","lot","experiment","bottom","key","iron","single","stick","flat","twenty","skin","smile","crease","hole","trade","melody","trip","office","receive","row","mouth","exact","symbol","die","least","trouble","shout","except","wrote","seed","tone","join","suggest","clean","break","lady","yard","rise","bad","blow","oil","blood","touch","grew","cent","mix","team","wire","cost","lost","brown","wear","garden","equal","sent","choose","fell","fit","flow","fair","bank","collect","save","control","decimal","gentle","woman","captain","practice","separate","difficult","doctor","please","protect","noon","whose","locate","ring","character","insect","caught","period","indicate","radio","spoke","atom","human","history","effect","electric","expect","crop","modern","element","hit","student","corner","party","supply","bone","rail","imagine","provide","agree","thus","capital","won't","chair","danger","fruit","rich","thick","soldier","process","operate","guess","necessary","sharp","wing","create","neighbor","wash","bat","rather","crowd","corn","compare","poem","string","bell","depend","meat","rub","tube","famous","dollar","stream","fear","sight","thin","triangle","planet","hurry","chief","colony","clock","mine","tie","enter","major","fresh","search","send","yellow","gun","allow","print","dead","spot","desert","suit","current","lift","rose","continue","block","chart","hat","sell","success","company","subtract","event","particular","deal","swim","term","opposite","wife","shoe","shoulder","spread","arrange","camp","invent","cotton","born","determine","quart","nine","truck","noise","level","chance","gather","shop","stretch","throw","shine","property","column","molecule","select","wrong","gray","repeat","require","broad","prepare","salt","nose","plural","anger","claim","continent","oxygen","sugar","death","pretty","skill","women","season","solution","magnet","silver","thank","branch","match","suffix","especially","fig","afraid","huge","sister","steel","discuss","forward","similar","guide","experience","score","apple","bought","led","pitch","coat","mass","card","band","rope","slip","win","dream","evening","condition","feed","tool","total","basic","smell","valley","nor","double","seat","arrive","master","track","parent","shore","division","sheet","substance","favor","connect","post","spend","chord","fat","glad","original","share","station","dad","bread","charge","proper","bar","offer","segment","slave","duck","instant","market","degree","populate","chick","dear","enemy","reply","drink","occur","support","speech","nature","range","steam","motion","path","liquid","log","meant","quotient","teeth","shell","neck"]
    
    # how many messages to pull from the database
    self.max_query_limit = 1701

  @commands.slash_command(
    name="wordcloud",
    description="Show your own most popular words in a wordcloud! Enable logging with `/settings`"
  )
  @option(
    name="public",
    description="Show to public?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="No",
        value="no"
      ),
      discord.OptionChoice(
        name="Yes",
        value="yes"
      )
    ]
  )
  async def wordcloud(self, ctx:discord.ApplicationContext, public:str):
    """
    Entrypoint for `/wordcloud` command
    generates a wordcloud image based on users most-used words
    """
    user = get_user(ctx.author.id)

    # if they have previously disabled logging
    if user.get("log_messages") != 1:
      await ctx.respond(content="You do not have logging enabled. Use `/settings` to enable logging!", ephemeral=True)
      return

    public = bool(public == "yes")

    await ctx.defer(ephemeral=not public)
    # get their message data
    user_details = self.get_wordcloud_text_for_user(ctx.author.id)

    # if they have no data yet
    if user_details is None:
      await ctx.respond(content="No user data is available for you yet. Post some messages around the server!", ephemeral=True)
      return
    else:
      await increment_user_xp(ctx.author, 1, "used_wordcloud", ctx.channel)

    # performing these modifications to the user's data again (in case they have old, uncleaned up data)
    full_wordlist = user_details['full_message_text'].lower().split(' ')
    full_wordlist = " ".join(full_wordlist)
    remove_emoji = re.compile('<.*?>')
    special_chars = re.escape(string.punctuation)
    full_wordlist = re.sub(remove_emoji, '', full_wordlist) # strip discord emoji from message
    full_wordlist = re.sub(r'https?:\/\/\S*', '', full_wordlist) # strip all URLs from the content
    full_wordlist = re.sub(r'['+special_chars+']', '', full_wordlist) # strip any remaining special characters
    full_wordlist = full_wordlist.replace("  ", " ").strip() # convert double spaces to single space
    
    more_stopwords = ["profile", "help", "wordcloud", "quiz", "trivia", "slots", "poker", "set_tagline", "reports", "badges", "trade", "agimus", "one",]
    for word in more_stopwords:
      STOPWORDS.add(word)
    for word in self.common_words:
      STOPWORDS.add(word)
    # mask image (combadge in this case, something else might work better)
    mask = np.array(random.choice(self.image_masks))

    # build wordcloud with magic of wordcloud lib
    wc = WordCloud(
      scale=1,
      contour_color="#000000",
      color_func=lambda *args, **kwargs: random.choice(["#ffaa00", "#33cc99", "#ff2200", "#ff9966", "#cc33ff"]),
      contour_width=1,
      min_font_size=8,
      max_words=500,
      stopwords=STOPWORDS,
      mask=mask,
      font_path="./fonts/tng_credits.ttf",
      background_color="#000000",
      mode="RGB",
      width=1200,
      height=800,
      min_word_length=3).generate(full_wordlist)

    # create PIL image
    image = wc.to_image()
    image.save(f"./images/reports/wordcloud-{user_details['name']}.png")

    # create discord image
    discord_image = discord.File(f"./images/reports/wordcloud-{user_details['name']}.png")

    # send the image!
    await ctx.followup.send(content=f"(Based on your last {user_details['num_messages']} messages)", file=discord_image, ephemeral=not public)
    logger.info(f"{Style.BRIGHT}{ctx.author.display_name}{Style.RESET_ALL} has generated a {Fore.CYAN}wordcloud!{Fore.RESET}")

  def get_wordcloud_text_for_user(self, user_discord_id:int):
    """
    get user's message history and return it in a dict
    """
    db = getDB()
    query = db.cursor(dictionary=True)
    sql = "SELECT message_history.user_discord_id, message_history.message_text as text, users.name FROM message_history LEFT JOIN users ON message_history.user_discord_id = users.discord_id WHERE message_history.user_discord_id = %s ORDER BY message_history.time_created DESC LIMIT %s"
    vals = (user_discord_id,self.max_query_limit)
    query.execute(sql, vals)
    results = query.fetchall()
    query.close()
    db.close()
    if len(results) < 1:
      response = None
    else:
      response = {
        "name" : results[0]["name"],
        "num_messages" : len(results),
        "full_message_text" : ""
      }
      for row in results:
        # strip out duplicate words (in old messages)
        response["full_message_text"] += " ".join(set(row["text"].split(" ")))
    return response
    