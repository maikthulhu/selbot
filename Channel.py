import re
import textwrap

from threading import Timer

from FAQ import *
from Quotes import *
from FAQ_Command import FAQ_Command


class Channel():
    def __init__(self, channel_settings, nickname, quotes_dir):
        self.cfg = channel_settings
        self.name = channel_settings['name']
        self.services = channel_settings['services']
        self.quotes_list = QuotesList(quotes_dir)
        self.last_quote = None
        self.last_faq = FAQ_Command.get_latest_faq()
        self.connection = None
        self.nickname = nickname
        self.last_speaker = self.nickname
        self.quote_timeout = channel_settings['quote_timeout']
        self.quote_last_ten = False
        self.quote_bets = None

    def is_valid_vote(self, args, source):
        pinged_me = args[0].startswith(self.nickname)
        is_digit = len(args) > 1 and args[1].isdigit()
        first_vote = source not in [bet['who'] for bet in self.quote_bets]
        return pinged_me and is_digit and first_vote

    def start_quote_timer(self):
        if 'quotes' not in self.services:
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
            if random.randint(1, 100) == 1:
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
                    right_word = q_split[word - 1] + ' ' + q_split[word]
                else:
                    # transpose two neighboring letters
                    qtmp += ' '
                    # Never include the last letter so we can always transpose n:n+1
                    letter = random.randint(1, (len(q_split[word]) - 1) - 1)
                    # Make sure the letters aren't the same (been, feed, etc.)
                    while q_split[word][letter] == q_split[word][letter + 1]:
                        letter = random.randint(1, (len(q_split[word]) - 1) - 1)
                    right_word = q_split[word]
                    munged_word = q_split[word][:letter]
                    munged_word += q_split[word][letter + 1]
                    munged_word += q_split[word][letter]
                    if (letter + 1) < len(q_split[word]) - 1:
                        munged_word += q_split[word][letter + 2:]
                    qtmp += munged_word + ' '
                    qtmp += ' '.join(q_split[word + 1:])
            try:
                if qtmp:
                    # We have typo'd.  Set quote text to typo'd quote and start 1-5sec timer to send correction
                    q = Quote(q.source, qtmp)
                    Timer(random.randint(5, 10), lambda: self.connection.privmsg(self.name, right_word + '*')).start()
                self.connection.privmsg(self.name, q)
            except:
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
                self.quote_bets = [{'src': q.title(), 'who': None} for q in sorted(
                    list(set([x.source for x in self.quotes_list.quotes + self.quotes_list.spent_quotes])))]
                str_sources = str(
                    ' '.join(['\x02{}:\x0f {}'.format(i + 1, q['src']) for i, q in enumerate(self.quote_bets)]))
                for line in textwrap.wrap(str_sources, 400):
                    self.connection.privmsg(self.name, line)
        else:
            if len(self.quotes_list) > 10:
                # And since we have 10 or less left, if we're suddenly above 10 then we have reloaded and the previous quote was the last one.
                for q in self.quote_bets:
                    if q['src'] == self.last_quote.source.title():
                        if q['who']:
                            ballot_result = '\x02{0}\x0f is the winner with \x02{1}\x0f!'.format(q['who'], q['source'])
                        else:
                            ballot_result = 'No winner this time!'
                        self.connection.privmsg(self.name, ballot_result)
                self.quote_last_ten = False

