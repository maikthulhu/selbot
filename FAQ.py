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


