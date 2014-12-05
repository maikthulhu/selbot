import requests

from BeautifulSoup import BeautifulSoup


class FAQ():
    def __init__(self, title, author, url, docid):
        self.title = title
        self.author = author
        self.url = url
        self.docid = docid

    def __str__(self):
        return self.title + " (" + self.author + ") - " + self.url


def get_latest_faq(search=None):
    BASE_URL = "FAQ_BASE_URL"
    q = None

    if search:
        q = {"vm": "0", "searchValue": search}

    try:
        r = requests.get(BASE_URL + "FAQ_URL_PATH", params=q)
    except IOError:
        return None

    soup = BeautifulSoup(r.text, convertEntities=BeautifulSoup.HTML_ENTITIES)

    latest_faq = soup.find("a", {"class": "xspLinkViewTopicTitle"})
    try:
        title = latest_faq.text
        author = latest_faq.findParent("td").findNextSibling().findNextSibling().text
        url = BASE_URL + latest_faq['href']
        docid = url.split('documentId=')[1]
    except AttributeError:
        return None
    else:
        return FAQ(title, author, url, docid)

