from FAQ_Command import FAQ_Command
from LastQuote_Command import LastQuote_Command
from Quote_Command import Quote_Command
from Stats_Command import Stats_Command
from Xkcd_Command import Xkcd_Command
from Ballot_Command import Ballot_Command


class CommandFactory():
    def factory(cmd, conn, event, channel, start_time):  # last, quote, faq, stats, relevant, ballot
        cfg = {
            'connection': conn,
            'event': event,
            'channel': channel,
            'start': start_time
        }
        if "!last" == cmd:
            return LastQuote_Command(cfg)
        elif "!quote" == cmd:
            return Quote_Command(cfg)
        elif "!faq" == cmd:
            return FAQ_Command(cfg)
        elif "!stats" == cmd:
            return Stats_Command(cfg)
        elif "!relevant" == cmd:
            return Xkcd_Command(cfg)
        elif "!ballot" == cmd:
            return Ballot_Command(cfg)

    factory = staticmethod(factory)
