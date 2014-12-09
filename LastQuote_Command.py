from Command import Command


class LastQuote_Command(Command):
    def __init__(self, config):
        self.connection = config['connection']
        self.event = config['event']
        self.channel = config['channel']

    def resolve(self):
        if self.channel.last_quote:
            self.respond(self.event.target, self.channel.last_quote.source)

    def respond(self, target, message):
        self.connection.privmsg(target, message)
