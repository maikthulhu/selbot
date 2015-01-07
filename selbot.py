import sys
import time
import ssl
import irc

from irc.bot import SingleServerIRCBot
from irc.connection import Factory
from threading import Timer

from util import *
from CommandFactory import CommandFactory
from Channel import *

SETTINGS_FILE = 'settings.json'


class SELBot(SingleServerIRCBot):
    def __init__(self, settings, connect_factory, debug):
        self.cfg = settings
        self.debug = debug
        self.start_time = time.time()
        self.channel_list = []
        if debug:
            self.nickname = 'testbot'
            self.realname = 'testbot'
            self.channel_list.append(Channel(self.cfg['channel_list'][0], self.nickname, self.cfg['quotes_dir']))
        else:
            self.nickname = self.cfg['nickname']
            self.realname = self.cfg['realname']
            for channel in self.cfg['channel_list']:
                self.channel_list.append(Channel(channel, self.nickname, self.cfg['quotes_dir']))
        self.ignore_list = []
        self.faq_timeout = self.cfg['faq_timeout']
        self.last_faq = FAQ_Command.get_latest_faq()
        SingleServerIRCBot.__init__(
            self,
            server_list=[(self.cfg['server'], self.cfg['port'])],
            nickname=self.nickname,
            realname=self.realname,
            connect_factory=connect_factory
        )
        self.connection.privmsg = self.privmsg

    def send_multiline_message(self, target, message):
        for line in message.split('\n'):
            if line.strip() == '': continue
            self.connection.privmsg(target, line)

    def get_stats(self, channel):
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_string = str(datetime.timedelta(seconds=uptime_seconds))
        out = "My server's uptime: {0}.  ".format(uptime_string)
        out += "My uptime: {0}.  ".format(datetime.timedelta(seconds=(time.time() - self.start_time)))
        total_quotes = len(channel.quotes_list.quotes) + len(channel.quotes_list.spent_quotes)
        out += "Quotes left: {0}/{1}.  ".format(len(channel.quotes_list.quotes), total_quotes)
        return out

    def start_faq_timer(self):
        self._faq_timer = Timer(self.faq_timeout, self.start_faq_timer)
        self._faq_timer.daemon = True
        self._faq_timer.start()
        tmp = FAQ_Command.get_latest_faq()
        if str(self.last_faq.docid) != str(tmp.docid):
            self.last_faq = tmp
            for ch in self.channel_list:
                if 'faq' in ch.services:
                    ch.connection.privmsg(ch.name, "NEW FAQ - {0}".format(tmp))

    def privmsg(self, target, text):
        """Send a PRIVMSG command."""
        if groots_birthday():
            self.connection.send_raw("PRIVMSG {0} :{1}".format(target, "I am Groot."))
            target = "BOT_OWNER"
        self.connection.send_raw("PRIVMSG {0} :{1}".format(target, text))

    def on_welcome(self, connection, event):
        self.connection = connection
        for channel in self.channel_list:
            connection.join(channel.name)
            channel.connection = self.connection
            channel.start_quote_timer()
            self.start_faq_timer()

    def on_action(self, connection, event):
        source = event.source.split('!')[0]
        for ch in self.channel_list:
            if event.target == ch.name:
                ch.last_speaker = source
        args = event.arguments[0].split()
        if len(args) < 1: return
        self.match_keyword_list(connection, event, args)

    def on_privmsg(self, connection, event):
        source = event.source.split('!')[0]
        args = event.arguments[0].split()
        connection.privmsg("BOT_OWNER", source + " said: " + str(args))
        if source in self.cfg['admins'] and args[0].startswith("!"):
            if "!say" == args[0].lower() and args[1:]:
                connection.privmsg(args[1], ' '.join(args[2:]))
            elif "!act" == args[0].lower() and args[1:]:
                connection.action(args[1], ' '.join(args[2:]))
            elif "!rb" == args[0].lower() and args[1:]:
                output = check_output(['toilet', '--irc', '-f', 'standard', '-F', 'gay', ' '.join(args[2:])])
                self.send_multiline_message(args[1], output)
            elif "!op" == args[0].lower() and len(args) > 2:
                ch = args[1]
                nick = args[2]
                connection.mode(ch, "+o %s" % nick)

    # "keyword[ ...]" OR "[... ]keyword\S"
    # "[... ]keyword[ ...]" AND "[... ]nickname[ ...]" or vice versa
    def match_keyword(self, args, keyword):
        message = ' '.join(args)
        regex = '(.*?({0}.+{1}|{1}.+{0}).*?)|((^{0}.*?)|(.*?{0}\S*?$))'.format(keyword, self.nickname)
        return re.match(regex, message, re.IGNORECASE)

    def match_keyword_list(self, connection, event, args):
        if self.match_keyword(args, 'botsnack'):
            connection.privmsg(event.target, "nom nom nom")
        elif self.match_keyword(args, 'botsmack'):
            with open('smack_responses.txt', 'r') as f:
                responses = f.readlines()
            response = random.choice(responses).strip('\n').strip('\r')
            if '/me' in response:
                response = ' '.join(response.split(' ')[1:])
                response = response.replace('[speaker]', event.source.split('!')[0])
                connection.action(event.target, response)
            else:
                connection.privmsg(event.target, response)


    #inherited function from SingleServerIRCBot
    def on_pubmsg(self, connection, event):
        source = event.source.split('!')[0]
        chan = None
        if source in self.ignore_list:
            return
        for ch in self.channel_list:
            if event.target == ch.name:
                chan = ch
        chan.last_speaker = source
        # --- DEBUG ONLY ---#
        # connection.privmsg(event.target, '%s: %s' % (source, ' '.join(event.arguments)))
        #------------------#
        args = event.arguments[0].split()
        # Check for any urls in the arguments
        url_args = [arg for arg in args if arg.startswith('http')]
        if len(args) < 1:
            return
        #Look for triggered commands
        if args[0].startswith("!"):
            cmd_class = CommandFactory.factory(args[0], connection, event, chan, self.start_time)
            cmd_class.resolve()
        #Last-Ten Quote Voting handler
        elif chan.is_valid_vote(args, source):
            choice = int(args[1])
            choice_idx = choice - 1
            if 0 < choice <= len(chan.quote_bets):  # PYTHON WOOH
                # Check if someone else already picked it
                if not chan.quote_bets[choice_idx]['who']:
                    chan.quote_bets[choice_idx]['who'] = source
                    vote_response = '\x02{}\x0f chose \x02{}\x0f'.format(source, chan.quote_bets[choice_idx]['src'])
                else:
                    vote_response = '\x02{}\x0f was already chosen by \x02{}\x0f'.format(
                        chan.quote_bets[choice_idx]['who'], source)
                connection.privmsg(event.target, vote_response)
        # Grab/display <title> text for URLs
        elif len(url_args) > 0:
            for arg in url_args:
                soup = make_soup(arg, event.target, self.cfg)
                if soup and soup.title and soup.title.string:
                    title = re.sub(r'\s+', r' ', soup.title.string).strip()
                    good_title = ""
                    for char in title:
                        try:
                            good_title += char.decode('utf-8')
                        except UnicodeEncodeError:
                            print char
                    connection.privmsg(event.target, '[title] {}'.format(good_title))
        # He should only look for things like 'botsnack' if there's nothing else to do!
        else:
            self.match_keyword_list(connection, event, args)


if __name__ == "__main__":
    SETTINGS = parse_settings(SETTINGS_FILE)
    debug_mode = False
    # Check for debug mode
    if len(sys.argv) > 1 and sys.argv[1].lower() == "test":
        debug_mode = True
    # This is how you connect to an SSL IRC server with this library
    factory = Factory(wrapper=ssl.wrap_socket)
    bot = SELBot(SETTINGS, factory, debug=debug_mode)
    # Prevent UnicodeDecodeError exceptions caused by echo 0x80 | xxd -r
    bot.connection.buffer_class = irc.buffer.LenientDecodingLineBuffer
    bot.start()
