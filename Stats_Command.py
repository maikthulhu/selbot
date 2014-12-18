import datetime
import time

from Command import Command


class Stats_Command(Command):
    def __init__(self, cfg):
        self.connection = cfg['connection']
        self.event = cfg['event']
        self.channel = cfg['channel']
        self.start_time = cfg['start']

    def resolve(self):
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_string = str(datetime.timedelta(seconds=uptime_seconds))
        out = "My server's uptime: {0}.  ".format(uptime_string)
        out += "My uptime: {0}.  ".format(datetime.timedelta(seconds=(time.time() - self.start_time)))
        total_quotes = len(self.channel.quotes_list.quotes) + len(self.channel.quotes_list.spent_quotes)
        out += "Quotes left: {0}/{1}.  ".format(len(self.channel.quotes_list.quotes), total_quotes)
        self.connection.privmsg(self.event.target, out)

    def respond(self, target, message):
        self.connection.privmsg(target, message)

