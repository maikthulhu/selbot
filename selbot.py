# -*- coding: utf-8 -*-

import sys, os, random, re, subprocess, datetime, time
import textwrap
from threading import Timer

import requests, json

from BeautifulSoup import BeautifulSoup

import irc
from irc.bot import SingleServerIRCBot
from irc.connection import Factory

import ssl

# For maxbuss' !relevant (xkcd)
import urllib

proxies = {'http':  'PULL FROM SETTINGS FILE',
           'https': 'PULL FROM SETTINGS FILE'}

FAQ_TIMEOUT = 600.0
QUOTE_TIMEOUT = 900.0
QUOTES_DIR = "/srv/selbot/quotes/"


class SELBot(SingleServerIRCBot):
   def __init__(self, channel_list, nickname, realname, server, port, connect_factory):
      SingleServerIRCBot.__init__(self, server_list=[(server, port)], nickname=nickname, realname=realname, connect_factory=connect_factory)
      self.start_time = time.time()
      self.nickname = nickname
      self.channel_list = channel_list
      self.ignore_list = ["xkcdbot"]

      self.connection.privmsg = self.privmsg

   def groots_birthday(self):
      if datetime.date.today().strftime("%m-%d") == "11-10":
         return True
      else:
         return False

   def send_multiline_message(self, target, message):
      for line in message.split('\n'):
         if line.strip() == '': continue
         self.connection.privmsg(target, line)

   def get_stats(self, channel):
      with open('/proc/uptime', 'r') as f:
         uptime_seconds = float(f.readline().split()[0])
         uptime_string = str(datetime.timedelta(seconds = uptime_seconds))

      out  = "My server's uptime: " + uptime_string + ".  "
      out += "My uptime: " + str(datetime.timedelta(seconds = (time.time() - self.start_time))) + ".  "
      out += "Quotes left: " + str(len(channel.quotes_list.quotes)) + "/" + str((len(channel.quotes_list.quotes) + len(channel.quotes_list.spent_quotes))) + ".  "

      return out

   # From maxbuss 15 August 2014
   def find_xkcd(self, c, e, key):
      #key = re.sub(r'\W+', '', key)
      query = urllib.urlencode({'q': key+' site:explainxkcd.com'})
      url = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&%s' % query
      search_response = urllib.urlopen(url)
      search_results = search_response.read()
      results = json.loads(search_results)
      data = results['responseData']
      hits = data['results']
      if len(hits) > 0:
         m = re.search("^http://www\.explainxkcd\.com/wiki/index\.php/[0-9]*[:]?[\_A-Za-z0-9]*", hits[0]['url'])
      else:
         m = None
      if m:
         url = hits[0]['url']
         c.privmsg(e.target, url)
         parts = url.split('/')
         number = parts[len(parts)-2]
         # c.privmsg(e.target, "Explanation:  http://www.explainxkcd.com/wiki/index.php/%s" % number)
      elif m is None:
         c.privmsg(e.target, "Could not find relevant XKCD!  Try a different keyword?")
      # MAKE CHECK IF 0 RESULTS FOUND
   
   def privmsg(self, target, text):
      """Send a PRIVMSG command."""
      if self.groots_birthday():
         self.connection.send_raw("PRIVMSG %s :%s" % (target, "I am Groot."))
         target = "BOT_OWNER"
      self.connection.send_raw("PRIVMSG %s :%s" % (target, text))

   def on_welcome(self, connection, event):
      self.connection = connection
      for channel in self.channel_list:
         connection.join(channel.name)
         channel.connection = self.connection
         channel.start_quote_timer()
         channel.start_faq_timer()
      
   def on_action(self, connection, event):
      source = event.source.split('!')[0]
      for ch in self.channel_list:
         if event.target == ch.name:
            ch.last_speaker = source

      args = event.arguments[0].split()
      
      if len(args) < 1: return

      if re.match(r'(.*?(botsnack.+selbot|selbot.+botsnack).*?)|((^botsnack.*?)|(.*?botsnack\S*?$))', ' '.join(args), re.IGNORECASE):
         connection.privmsg(event.target, "nom nom nom")

   def on_privmsg(self, connection, event):
      approved_nicks = ['NICKNAME1', 'NICKNAME2']
      source = event.source.split('!')[0]
      args = event.arguments[0].split()
      
      connection.privmsg("BOT_OWNER", source + " said: " + str(args))
   
      if source in approved_nicks:
         if args[0].startswith("!"):
            if args[0].lower() == "!say":
               if args[1:]:
                  connection.privmsg(args[1], ' '.join(args[2:]))
            if args[0].lower() == "!act":
               if args[1:]:
                   connection.action(args[1], ' '.join(args[2:]))
            if args[0].lower() == "!rb":
               if args[1:]:
                  output = check_output(['toilet', '--irc', '-f', 'standard', '-F', 'gay', ' '.join(args[2:])])
                  self.send_multiline_message(args[1], output)
            elif args[0].lower() == "!op":
                if len(args) > 2:
                    ch = args[1]
                    nick = args[2]
                    connection.mode(ch, "+o %s" % nick)

   def on_pubmsg(self, connection, event):
      source = event.source.split('!')[0]
      chan = None

      if source in self.ignore_list:
         return

      for ch in self.channel_list:
         if event.target == ch.name:
            chan = ch

      chan.last_speaker = source

      #connection.privmsg(event.target, '%s: %s' % (source, ' '.join(event.arguments)))

      args = event.arguments[0].split()

      if len(args) < 1: return
      
      if args[0].startswith("!"):
         if args[0].lower() == "!last":
            if chan.last_quote:
               connection.privmsg(event.target, chan.last_quote.source)

         elif args[0].lower() == "!quote":
	    if not chan.quote_last_ten:
               if len(args) > 1:
                  try:
                     q = chan.quotes_list.random_quote(args[1])
                  except Exception as e:
                     q = Quote("your_boss", "Don't you think you should be getting back to work?")
               else:
                  q = chan.quotes_list.random_quote()
               chan.last_quote = q
               connection.privmsg(event.target, q)
            
         elif args[0].lower() == "!faq":
            if len(args) > 1:
               faq = get_latest_faq(args[1])
               if faq != None:
                  connection.privmsg(event.target, str(faq))

         elif args[0].lower() == "!stats":
            stats = self.get_stats(chan)
            connection.privmsg(event.target, stats)

         elif args[0].lower() == "!relevant":
            self.find_xkcd(connection, event, ' '.join(args[1:]))

         elif args[0].lower() == "!ballot":
            if chan.quote_last_ten:
               if chan.quote_bets:
                  connection.privmsg(event.target, ' '.join(["{}: {}".format(q['who'], q['src']) for q in chan.quote_bets]))
               else:
                  connection.privmsg(event.target, "No one has voted yet, place your bets!")
            else:
               connection.privmsg(event.target, "No votes going on right now.  Check back later.")
               
         
      # "botsnack[ ...]" OR "[... ]botsnack\S"
      # "[... ]botsnack[ ...]" AND "[... ]nickname[ ...]" or vice versa
      elif re.match(r'(.*?(botsnack.+selbot|selbot.+botsnack).*?)|((^botsnack.*?)|(.*?botsnack\S*?$))', ' '.join(args), re.IGNORECASE):
         connection.privmsg(event.target, "nom nom nom")

      elif args[0].startswith(self.nickname):
         if len(args) > 1 and chan.quote_last_ten:
            if args[1].isdigit():
               # Make sure they haven't already voted
               if not any([x['who'] == source for x in chan.quote_bets]):
                  choice = int(args[1])
	          if choice > 0 and choice <= len(chan.quote_bets):
                     if not chan.quote_bets[choice-1]['who']:
                        chan.quote_bets[choice-1]['who'] = source
		        connection.privmsg(event.target, '\x02{}\x0f chose \x02{}\x0f'.format(source, chan.quote_bets[choice-1]['src']))
		     else:
                        connection.privmsg(event.target, '\x02{}\x0f was already chosen by \x02{}\x0f'.format(chan.quote_bets[choice-1]['who'], source))
	       
      else:
         # <title> grabber
         for arg in args:
            if arg.startswith("http"):
               try:
                  r = requests.get(arg, proxies=proxies)
                  if 'text/html' not in r.headers['content-type']:
                     connection.privmsg(event.target, r.headers['content-type'])
                     break
                  soup = BeautifulSoup(r.text, convertEntities=BeautifulSoup.HTML_ENTITIES)
               except:
                  print "ERROR: requests or BeautifulSoup: %s (%s)" % (event.target, arg)
                  pass
               else:
                  if soup.title != None and soup.title.string != None and soup.title.string != "ERROR: The requested URL could not be retrieved":
                     title = re.sub(r'\s+', r' ', soup.title.string).strip()
                     connection.privmsg(event.target, '[title] %s' % title)
                  break


class Quote():
   def __init__(self, source, text):
      self.source = source
      self.text = text

   def __getitem__(self, key):
      if hasattr(self, key):
         return getattr(self, key)

   def __str__(self):
      return self.text

   def source(self):
      return self.source


class QuotesList():
   def __init__(self, quotes_dir):
      self.quotes_dir = quotes_dir
      print "Loading quotes database..."
      self.quotes = self.load_quotes()
      self.spent_quotes = []

   def __len__(self):
      return len(self.quotes)

   def load_quotes(self):
      quotes = []
      for f in os.listdir(self.quotes_dir):
         fh = open(os.path.join(self.quotes_dir, f), 'r')
         for line in fh.readlines():
            src = os.path.splitext(os.path.basename(f))[0]
            q = Quote(src.replace("_", " ").title(), line.strip())
            quotes.append(q)

         fh.close()

      return quotes

   def check_for_updates(self):
      ret = False
      orig = [x.text for x in self.quotes + self.spent_quotes]
      new = [x.text for x in self.load_quotes()]

      diff = list(set(orig).union(set(new)) - set(orig).intersection(set(new)))
      if diff:
         ret = True
         print "New quotes, reloading..."
         #print sorted(new), sorted(orig)
         #print list(set(sorted(new)) - set(sorted(orig)))
         print diff
         self.spent_quotes = [] 
         self.quotes = self.load_quotes()
      
      return ret

   def random_quote(self, source=None):
      if source:
         q = random.choice([x for x in self.quotes if source.upper() in x['source'].upper()])
      else:
         q = random.choice(self.quotes)
      self.quotes.remove(q)
      self.spent_quotes.append(q)

      if len(self.quotes) < 1:
         self.quotes = self.load_quotes()
         self.spent_quotes = []

      return q


class FAQ():
   def __init__(self, title, author, url, docid):
      self.title = title
      self.author = author
      self.url = url
      self.docid = docid

   def __str__(self):
      return self.title + " (" + self.author + ") - " + self.url


class Channel():
   def __init__(self, name, nickname, quote_timeout=QUOTE_TIMEOUT):
      self.name = name
      self.services = { 'faq': True,
                        'quotes': True,
                      }
      self.quotes_list = QuotesList(QUOTES_DIR)
      self.last_quote = None
      self.last_faq = get_latest_faq()
      self.connection = None
      self.nickname = nickname
      self.last_speaker = self.nickname
      self.quote_timeout = quote_timeout
      self.quote_last_ten = False
      self.quote_bets = None

   def start_quote_timer(self):
      if not self.services['quotes']:
         return

      self._quote_timer = Timer(self.quote_timeout, self.start_quote_timer)
      self._quote_timer.daemon = True
      self._quote_timer.start()
      
      if self.last_speaker != self.nickname:
         q = self.quotes_list.random_quote()
         self.last_quote = q
         qtmp = None
         right_word = None
         # Chance for word typo (10%)
         if random.randint(1,100) == 1:
            q_split = q.text.split()
            # Choose a word index (never choose the first or last word)
            word = random.randint(1, (len(q_split) - 1) - 1)
            # Ignore words with punctuation attached
            while re.search('[^\w ]', q_split[word]):
               word = random.randint(1, (len(q_split) - 1) - 1)
            # Construct the quote up to the word we chose
            qtmp = ' '.join(q_split[:word])
            if len(q_split[word]) < 2:
               qtmp += ' '.join(q_split[word:])
               right_word = q_split[word-1] + ' ' + q_split[word]
            else:
               # transpose two neighboring letters
               qtmp += ' '
               # Never include the last letter so we can always transpose n:n+1
               letter = random.randint(1, (len(q_split[word]) - 1) - 1)
               # Make sure the letters aren't the same (been, feed, etc.)
               while q_split[word][letter] == q_split[word][letter+1]:
                  letter = random.randint(1, (len(q_split[word]) - 1) - 1)
               right_word = q_split[word]
               munged_word = q_split[word][:letter]
               munged_word += q_split[word][letter+1]
               munged_word += q_split[word][letter]
               if (letter+1) < len(q_split[word])-1:
                  munged_word += q_split[word][letter+2:]
               qtmp += munged_word + ' '
               qtmp += ' '.join(q_split[word+1:])
         try:
            if qtmp:
               # We have typo'd.  Set quote text to typo'd quote and start 1-5sec timer to send correction
               q = Quote(q.source, qtmp)
               Timer(random.randint(5,10), lambda: self.connection.privmsg(self.name, right_word + '*')).start()
            self.connection.privmsg(self.name, q)
         except :
            print "Error sending quote:", q

         self.last_speaker = self.nickname

      if self.quotes_list.check_for_updates():
         self.quote_last_ten = False
         self.connection.privmsg("BOT_OWNER", "New quotes!  Reloading...")

      if self.quote_last_ten == False:
         # If we are here then we know we have 10 or less left
         if len(self.quotes_list) == 10:
            self.quote_last_ten = True
            self.connection.privmsg(self.name, "Place your bets!  10 quotes remaining.")
	    self.quote_bets = [ { 'src': q.title(), 'who': None } for q in sorted(list(set([x.source for x in self.quotes_list.quotes + self.quotes_list.spent_quotes])))]
	    str_sources = str(' '.join(['\x02{}:\x0f {}'.format(i+1, q['src']) for i, q in enumerate(self.quote_bets)]))
	    for line in textwrap.wrap(str_sources, 400):
	       self.connection.privmsg(self.name, line)
         # And since we have 10 or less left, if we're suddenly above 10 then we have reloaded and the previous quote was the last one.
      else:
         if len(self.quotes_list) > 10:
            for q in self.quote_bets:
               if q['src'] == self.last_quote.source.title():
                  if q['who']:
                     self.connection.privmsg(self.name, '\x02{}\x0f is the winner with \x02{}\x0f!'.format(q['who'], q['source']))
                  else:
                     self.connection.privmsg(self.name, 'No winner this time!')
            self.quote_last_ten = False

   def start_faq_timer(self):
      if not self.services['faq']:
         return

      self._faq_timer = Timer(FAQ_TIMEOUT, self.start_faq_timer)
      self._faq_timer.daemon = True
      self._faq_timer.start()
      
      tmp = get_latest_faq()
      if str(self.last_faq.docid) != str(tmp.docid):
         self.last_faq = tmp
         for ch in self.channel_list:
            if ch.services['faq']:
               ch.connection.privmsg(ch.name, "NEW FAQ - " + str(tmp))


class User():
   def __init__(self, nickmask):
      self.nickmask = nickmask
      self.total_words = 0
      self.url_points = 0
      self.urls = []


def get_latest_faq(search=None):
   BASE_URL = "FAQ_BASE_URL"
   q = None

   if search:
      q = { "vm": "0", "searchValue": search }

   try:
      r = requests.get(BASE_URL + "FAQ_URL_PATH", params=q)
   except IOError:
      return None

   soup = BeautifulSoup(r.text, convertEntities=BeautifulSoup.HTML_ENTITIES)
   
   latest_faq = soup.find( "a", { "class": "xspLinkViewTopicTitle" } )
   try:
      title = latest_faq.text
      author = latest_faq.findParent("td").findNextSibling().findNextSibling().text
      url = BASE_URL + latest_faq['href']
      docid = url.split('documentId=')[1]
   except AttributeError:
      return None
   else:
      return FAQ(title, author, url, docid)


def check_output(command):
   process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
   output = process.communicate()
   retcode = process.poll()
   if retcode:
      raise subprocess.CalledProcessError(retcode, command, output=output[0])
   return output[0]


def main():
   server = "IRC_SERVER"
   port = 1234 # IRC_PORT
   channels = []
   if len(sys.argv) > 1 and sys.argv[1].lower() == "test":
      nickname = "testbot"
      channels = [Channel("#test", nickname=nickname)]
   else:
      nickname = "selbot"
      ch = Channel("#CHANNEL1", nickname=nickname)
      ch.services['quotes'] = False
      channels.append(ch)
      ch = Channel("#CHANNEL2", nickname=nickname, quote_timeout=600.0)
      channels.append(ch)

   realname = nickname

   # This is how you connect to an SSL IRC server with this library
   factory = Factory(wrapper=ssl.wrap_socket)
   bot = SELBot(channels, nickname, realname, server, port, connect_factory=factory)
   # Prevent UnicodeDecodeError exceptions caused by echo 0x80 | xxd -r
   bot.connection.buffer_class = irc.buffer.LenientDecodingLineBuffer
   bot.start()

if __name__ == "__main__":
   main()
