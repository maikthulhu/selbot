from Command import Command


class Ballot_Command(Command):
    def __init__(self, cfg):
        self.connection = cfg['self.connection']
        self.event = cfg['self.event']
        self.channel = cfg['self.channel']

    def resolve(self):
        # Only enabled during voting (final 10 quotes)
        if self.channel.quote_last_ten:
            #Check if anyone has voted yet
            if self.channel.quote_bets:
                output = ' '.join(["{}: {}".format(q['who'], q['src']) for q in self.channel.quote_bets])
                self.respond(self.event.target, output)
            else:
                self.respond(self.event.target, "No one has voted yet, place your bets!")
        else:
            self.respond(self.event.target, "No votes going on right now.  Check back later.")

    def respond(self, target, message):
        self.connection.privmsg(target, message)
