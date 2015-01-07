import datetime
import requests
import urllib
import json
import re
import subprocess
from BeautifulSoup import BeautifulSoup


def parse_settings(settings_file):
    json_data = open(settings_file).read()
    return json.loads(json_data)


def groots_birthday():
    if datetime.date.today().strftime("%m-%d") == "11-10":
        return True
    else:
        return False


# From maxbuss 15 August 2014
def find_xkcd(c, e, key):
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
        c.privmsg(e.target, url)
    elif m is None:
        c.privmsg(e.target, "Could not find relevant XKCD!  Try a different keyword?")


def check_output(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    output = process.communicate()
    retcode = process.poll()
    if retcode:
        raise subprocess.CalledProcessError(retcode, command, output=output[0])
    return output[0]

def make_soup(url, target):
    soup = None
    try:
        r = requests.get(url, proxies=self.cfg['proxies'])
        if 'text/html' not in r.headers['content-type']:
            print r.headers['content-type']
        soup = BeautifulSoup(r.text, convertEntities=BeautifulSoup.HTML_ENTITIES)
    except:
        print "ERROR: requests or BeautifulSoup: {0} ({1})".format(target, url)
    if soup and "ERROR: The requested URL could not be retrieved" == soup.title.string:
        soup = None
    return soup

