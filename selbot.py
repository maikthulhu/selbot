# -*- coding: utf-8 -*-

import sys
import subprocess
import time
import json
import ssl
import urllib
import irc

from irc.bot import SingleServerIRCBot
from irc.connection import Factory
from threading import Timer

from util import *
from Quotes import *
from FAQ import *
from Channel import *

SETTINGS_FILE = 'settings.json'


class SELBot(SingleServerIRCBot):
    def __init__(self, settings, connect_factory, debug):
        self.cfg = settings
        self.debug = debug
        self.start_time = time.time()
        if debug:
            self.nickname = 'testbot'
            self.realname = 'testbot'
        else:
            self.nickname = self.cfg['nickname']
            self.realname = self.cfg['realname']
        self.channel_list = []
        self.parse_channels()
        self.ignore_list = ["xkcdbot"]
        self.faq_timeout = self.cfg['faq_timeout']
        SingleServerIRCBot.__init__(
            self,
            server_list=[(self.cfg['server'], self.cfg['port'])],
            nickname=self.nickname,
            realname=self.realname,
            connect_factory=connect_factory
        )

        self.connection.privmsg = self.privmsg

    def parse_channels(self):
        for channel in self.cfg['channel_list']:
            self.channel_list.append(Channel(channel, self.nickname, self.cfg['quotes_dir']))

    def send_multiline_message(self, target, message):
        for line in message.split('\n'):
            if line.strip() == '': continue
            self.connection.privmsg(target, line)

    def get_stats(self, channel):
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_string = str(datetime.timedelta(seconds=uptime_seconds))

        out = "My server's uptime: " + uptime_string + ".  "
        out += "My uptime: " + str(datetime.timedelta(seconds=(time.time() - self.start_time))) + ".  "
        out += "Quotes left: " + str(len(channel.quotes_list.quotes)) + "/" + str(
            (len(channel.quotes_list.quotes) + len(channel.quotes_list.spent_quotes))) + ".  "

        return out

    def start_faq_timer(self):
        self._faq_timer = Timer(self.faq_timeout, self.start_faq_timer)
        self._faq_timer.daemon = True
        self._faq_timer.start()

        tmp = get_latest_faq()
        if str(self.last_faq.docid) != str(tmp.docid):
            self.last_faq = tmp
            for ch in self.channel_list:
                if 'faq' in ch.services:
                    ch.connection.privmsg(ch.name, "NEW FAQ - " + str(tmp))

    def privmsg(self, target, text):
        """Send a PRIVMSG command."""
        if groots_birthday():
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

        if re.match(r'(.*?(botsnack.+selbot|selbot.+botsnack).*?)|((^botsnack.*?)|(.*?botsnack\S*?$))', ' '.join(args),
                    re.IGNORECASE):
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
        # --- DEBUG ONLY ---#
        # connection.privmsg(event.target, '%s: %s' % (source, ' '.join(event.arguments)))
        #------------------#
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
                        except Exception:
                            q = Quote("your_boss", "Don't you think you should be getting back to work?")
                    else:
                        q = chan.quotes_list.random_quote()
                    chan.last_quote = q
                    connection.privmsg(event.target, q)
            elif args[0].lower() == "!faq":
                if len(args) > 1:
                    faq = get_latest_faq(args[1])
                    if faq is not None:
                        connection.privmsg(event.target, str(faq))
            elif args[0].lower() == "!stats":
                stats = self.get_stats(chan)
                connection.privmsg(event.target, stats)
            elif args[0].lower() == "!relevant":
                find_xkcd(connection, event, ' '.join(args[1:]))
            elif args[0].lower() == "!ballot":
                if chan.quote_last_ten:
                    if chan.quote_bets:
                        connection.privmsg(event.target,
                                           ' '.join(["{}: {}".format(q['who'], q['src']) for q in chan.quote_bets]))
                    else:
                        connection.privmsg(event.target, "No one has voted yet, place your bets!")
                else:
                    connection.privmsg(event.target, "No votes going on right now.  Check back later.")
        # "botsnack[ ...]" OR "[... ]botsnack\S"
        # "[... ]botsnack[ ...]" AND "[... ]nickname[ ...]" or vice versa
        elif re.match(r'(.*?(botsnack.+selbot|selbot.+botsnack).*?)|((^botsnack.*?)|(.*?botsnack\S*?$))',
                      ' '.join(args), re.IGNORECASE):
            connection.privmsg(event.target, "nom nom nom")
        elif args[0].startswith(self.nickname):
            if len(args) > 1 and chan.quote_last_ten:
                if args[1].isdigit():
                    # Make sure they haven't already voted
                    if not any([x['who'] == source for x in chan.quote_bets]):
                        choice = int(args[1])
                        if choice > 0 and choice <= len(chan.quote_bets):
                            if not chan.quote_bets[choice - 1]['who']:
                                chan.quote_bets[choice - 1]['who'] = source
                                connection.privmsg(
                                    event.target,
                                    '\x02{}\x0f chose \x02{}\x0f'.format(source, chan.quote_bets[choice - 1]['src'])
                                )
                            else:
                                connection.privmsg(
                                    event.target,
                                    '\x02{}\x0f was already chosen by \x02{}\x0f'.format(
                                        chan.quote_bets[choice - 1]['who'], source)
                                )
        else:
            # <title> grabber
            for arg in args:
                if arg.startswith("http"):
                    try:
                        r = requests.get(arg, proxies=self.cfg['proxies'])
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
