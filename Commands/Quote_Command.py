from Commands import Command
from Quotes import Quote


class Quote_Command(Command):
    def __init__(self, config):
        self.connection = config['connection']
        self.event = config['event']
        self.channel = config['channel']
        pass

    def resolve(self):
        args = self.event.arguments[0].split()
        # Don't let people skip last 10 (for voting!)
        if not self.channel.quote_last_ten:
            #Check if they asked for a source
            if len(args) > 1:
                try:
                    #Grab a random quote from given source
                    q = self.channel.quotes_list.random_quote(args[1])
                except Exception:
                    #Invalid source name
                    q = Quote("your_boss", "Don't you think you should be getting back to work?")
            else:
                #Grab random quote from random source
                q = self.channel.quotes_list.random_quote()
            self.channel.last_quote = q
            #Print the quote
            self.respond(self.event.target, q)
        pass

    def respond(self, target, message):
        self.connection.privmsg(target, message)
