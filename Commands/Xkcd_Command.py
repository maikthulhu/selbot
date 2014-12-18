import urllib
import json
import re

from Commands import Command


class Xkcd_Command(Command):
    def __init__(self, cfg):
        self.connection = cfg['connection']
        self.event = cfg['event']

    def resolve(self):
        args = self.event.arguments[0].split()
        key = ' '.join(args[1:])
        query = urllib.urlencode({'q': key + ' site:explainxkcd.com'})
        url = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&%s' % query
        search_response = urllib.urlopen(url)
        search_results = search_response.read()
        results = json.loads(search_results)
        data = results['responseData']
        hits = data['results']
        if len(hits) > 0:
            m = re.search('^http://www\.explainxkcd\.com/wiki/index\.php/[0-9]*[:]?[\_A-Za-z0-9]*', hits[0]['url'])
        else:
            m = None
        if m:
            url = hits[0]['url']
            self.respond(self.event.target, url)
        elif m is None:
            self.respond(self.event.target, "Could not find relevant XKCD!  Try a different keyword?")

    def respond(self, target, message):
        self.connection.privmsg(target, message)
