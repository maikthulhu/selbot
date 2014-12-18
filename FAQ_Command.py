import requests

from BeautifulSoup import BeautifulSoup

from Command import Command
from util import *
from FAQ import FAQ


class FAQ_Command(Command):
    def __init__(self, config):
        self.connection = config['connection']
        self.event = config['event']
        self.args = self.event.arguments[0].split()

    def resolve(self):
        if len(self.args) > 1:
            faq = self.get_latest_faq(self.args[1])
            if faq is not None:
                self.respond(self.event.target, str(faq))

    def respond(self, target, message):
        self.connection.privmsg(target, message)

    def get_latest_faq(search=None):
        cfg = parse_settings('settings.json')
        base_url = cfg['faq_base_url']
        faq_url_path = cfg['faq_url_path']
        q = None
        if search:
            q = {"vm": "0", "searchValue": search}

        try:
            r = requests.get(base_url + faq_url_path, params=q)
        except IOError:
            return None
        soup = BeautifulSoup(r.text, convertEntities=BeautifulSoup.HTML_ENTITIES)
        latest_faq = soup.find("a", {"class": "xspLinkViewTopicTitle"})
        try:
            title = latest_faq.text
            author = latest_faq.findParent("td").findNextSibling().findNextSibling().text
            url = base_url + latest_faq['href']
            docid = url.split('documentId=')[1]
        except AttributeError:
            return None
        else:
            return FAQ(title, author, url, docid)

    get_latest_faq = staticmethod(get_latest_faq)