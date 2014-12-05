import datetime
import urllib
import json
import re
import subprocess


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