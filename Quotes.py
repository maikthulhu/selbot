import os
import random


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
            # print sorted(new), sorted(orig)
            # print list(set(sorted(new)) - set(sorted(orig)))
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
