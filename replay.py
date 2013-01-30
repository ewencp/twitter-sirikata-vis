#!/usr/bin/env python

import sys, json, time, calendar
from collections import namedtuple
from itertools import chain, product

import httplib, urllib, socket, math
import threading, os, shutil

import nltk, twtokenize
import SimpleHTTPServer, SocketServer

def ascii_safe(item):
    if type(item) == tuple:
        item = ' '.join(item)
    item = unicodedata.normalize('NFKD', unicode(item)).encode('ascii', 'ignore')
    return item

# Stop words. NLTK provides some in their data set (you need to use
# their nltk.download() tool to get them). They could probably be
# better. Add a few more to deal with obvious missing items,
# punctuation, bad spelling. These aren't actually critical since we compare to a
# baseline data set, but they help cut down the size of the data.
stopwords = nltk.corpus.stopwords.words('english') + [
    '?', '!', ';', '$', '%', '&', '-', '+', '=', '|', '`', '_', '.', '{', '}', ',', '/', '[', ']', '#', '@', ':', "'", '(', ')', '^', '~', '*', #punctuation
    'c', 'u', 'r', 'o', 'd', 'e', 'f', 'g', 'v', 'h', 'x', 'w', 'j', 'y', 'k', 'l', 'z', 'm', 'n', 'p', 'b', 'q' # bad spelling
    ]
# Some more things that our processing doesn't catch, often weird
# parts of words like 't, web things like http, or bad conversions
# like < and > to lt and gt
stopwords = stopwords + [
    'http', 'gt', 'lt', "'t", 'la', "'s", "''", 'amp', "n't", "'m", "...", "de", "``"
]
stopwords = set(stopwords)

def splitlist(l, on):
    '''Split a list into a sublists when any element in 'on' is found,
    removing that element in the process.'''
    last_idx = 0
    idx = 0
    while idx < len(l):
        while idx < len(l):
            if l[idx] in on:
                break
            idx += 1
        yield l[last_idx:idx]
        idx += 1
        last_idx = idx

def tokenize_and_ngram(text):
    tokens = [x.lower() for x in twtokenize.word_tokenize(text)]
    # Split into sublists using stopwords. This keeps us from
    # generating n-grams from words that aren't actually next
    # to each other. This step also removes the stopwords
    tokens = list(splitlist(tokens, stopwords))
    bgrams = [nltk.ibigrams(subtokens) for subtokens in tokens]
    tgrams = [nltk.itrigrams(subtokens) for subtokens in tokens]
    terms = list(chain(*(tokens + bgrams + tgrams)))
    return terms

def average(l):
    return float(sum(l))/len(l)

Coord = namedtuple('Coord', ['lon', 'lat'])
CoordBox = namedtuple('CoordBox', ['min', 'max'])

class Grid(object):
    def __init__(self, box, div):
        self._box = box
        self._diag = Coord(self._box.max.lon-self._box.min.lon, self._box.max.lat-self._box.min.lat)
        self._div = div
        self._bins = [None for y,x in product(range(self._div.lat), range(self._div.lon))]

    def diag(self):
        return self._diag

    def _get_bin_index(self, coord):
        lon_bin_index = int(((coord.lon - self._box.min.lon) / self._diag.lon) * self._div.lon)
        lon_bin_index = min(max(lon_bin_index, 0), self._div.lon-1)
        lat_bin_index = int(((coord.lat - self._box.min.lat) / self._diag.lat) * self._div.lat)
        lat_bin_index = min(max(lat_bin_index, 0), self._div.lat-1)
        return Coord(lon_bin_index, lat_bin_index)

    def bin_id(self, pos):
        '''Get a unique ID for the bin a position is in'''
        int_pos = self._get_bin_index(pos)
        return int_pos.lat*self._div.lon + int_pos.lon

    def __getitem__(self, pos):
        return self._bins[self.bin_id(pos)]

    def __setitem__(self, pos, value):
        self._bins[self.bin_id(pos)] = value

    def num_active(self):
        '''Returns the total number of active (non empty) grid regions'''
        return len([True for b in self._bins if b is not None])




def http_command(host, port, command, params=None, retries=2, wait=1):
    '''
    Execute the given command, with optional JSON params, against the node. Return the response.

    command -- command name, e.g. 'meta.commands'
    params -- options, in form of dict to be JSON encoded
    retries -- number of times to retries if there's a connection failure
    wait -- time to wait between retries
    '''

    tries = 0
    max_retries = (retries or 1)
    while tries < max_retries:
        try:
            result = None
            conn = httplib.HTTPConnection(host, port, timeout=int(5*math.pow(2, tries)))
            body = (params and json.dumps(params)) or None
            conn.request("POST", "/" + command, body=body)
            resp = conn.getresponse()
            if resp.status == 200:
                result = json.loads(resp.read())
            else:
                print "Bad response:", resp.status
                print resp.read()
            conn.close()
            return result
        except socket.error:
            tries += 1
            if wait:
                time.sleep(wait)
        except httplib.HTTPException, exc:
            # Got connection, but it failed. Log and indicate failure
            print "HTTP command", command, "failed:", str(exc), exc
            return None

    # If we didn't finish successfull, indicate failure
    print "HTTP command", command, "failed after", tries, "tries"
    return None



locations = CoordBox( Coord(-129.02,24.9), Coord(-58.71,50.6) ) # ~ United States
object_grid = Grid(locations, Coord(10, 10)) # HostedObjects
tweet_grid = Grid(locations, Coord(300, 300)) # Presences to map tweets into

started = time.time()
first_tweet_at = None
processed = 0
oh_host = 'localhost'
oh_port = 7779
HTTP_HOST = 'ahoy.stanford.edu'
HTTP_PORT = 10000
speed_factor = 1

tweet_file = os.path.abspath(sys.argv[1])

def ensure_dir(p):
    if not os.path.exists(p):
        os.mkdir(p)

# Start up a web server
# Set this up and make sure it's ready in this thread so it'll
# definitely be ready to hold data generated in the main thread
data_dir = os.path.join(os.getcwd(), 'data')
if os.path.exists(data_dir): shutil.rmtree(data_dir)
ensure_dir(data_dir)
class AggregateHttpRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    '''Handles receiving and serving aggregate tweet data. It extends
    SimpleHTTPRequestHandler to serve read requests from the
    filesystem and overrides do_POST to handle upload requests, which
    are stored on disk to be served for GETs.'''
    def do_POST(self):
        #print "Handling POST", self.path

        raw_id = self.path[1:] # remove / from front
        data_dir_primary = os.path.join(data_dir, raw_id[0])
        ensure_dir(data_dir_primary)
        data_dir_secondary = os.path.join(data_dir_primary, raw_id[1])
        ensure_dir(data_dir_secondary)
        mesh_file = os.path.join(data_dir_secondary, raw_id)
        with open(mesh_file, 'wb') as fp:
            target_count = int(self.headers.get('Content-Length', 0))
            count = 0
            while count < target_count:
                data = self.rfile.read(target_count-count)
                count += len(data)
                fp.write(data)

        #print "Saved file POST", self.path

        self.send_response(200)
        self.send_header("Content-Type", "text/json")
        self.send_header("Content-Length", 0)
        self.end_headers()

        #print "Finished handling POST", self.path

    def do_GET(self):
        # Need to change "/abcd1234f5" to "/a/b/abcd1234f5" so our hierarchical layout on disk gets mapped to properly
        self.path = "/" + self.path[1] + "/" + self.path[2] + "/" + self.path
        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

def http_server_main():
    os.chdir(data_dir)
    # No HTTP_HOST, '' indicates all interfaces
    httpd = SocketServer.TCPServer(('',HTTP_PORT), AggregateHttpRequestHandler)
    httpd.serve_forever()

http_thread = threading.Thread(target=http_server_main)
http_thread.daemon = True
http_thread.start()



# Parse tweets, generate "meshes", and create/notify objects of their tweets
with open(tweet_file, 'r') as fp:
    for line in fp:
        tweet = json.loads(line)
        # FIXME? the +0000 should be %z but is currently failing. It
        # probably doesn't matter since Twitter specifies this will be
        # UTC anyway
        tweeted_at = calendar.timegm(time.strptime(tweet['created_at'], "%a %b %d %H:%M:%S +0000 %Y"))
        if first_tweet_at is None: first_tweet_at = tweeted_at

        # Wait until we should actually process the tweet
        now = time.time()
        since_started = now - started
        since_started = since_started * speed_factor # Allow high-speed
        tweeted_after = tweeted_at - first_tweet_at
        if tweeted_after > since_started:
            time.sleep(tweeted_after - since_started)

        # Compute coordinates info
        if tweet['coordinates']:
            assert(tweet['coordinates']['type'] == 'Point')
            lon, lat = tweet['coordinates']['coordinates'][0], tweet['coordinates']['coordinates'][1]
        elif tweet['place']:
            bboxes = tweet['place']['bounding_box']['coordinates']
            # This is actually a list of bounding boxes, each
            # itself a list of points. Average each box, then
            # average the averages of the boxes.
            lon = average([average([point[0] for point in poly]) for poly in bboxes])
            lat = average([average([point[1] for point in poly]) for poly in bboxes])
        else:
            continue

        processed += 1
        tweet_pos = Coord(lon, lat)

        # Get the HostedObject ID we need to talk to, or create it
        ho_id = object_grid[tweet_pos]
        if ho_id is None:
            print "[%d] Tweet triggered new tweet object, resulting in %d objects for %d tweets so far" % (tweeted_after, object_grid.num_active(), processed)
            obj_params = {
                'script' : {
                    'type' : 'js',
                    'contents' : "system.import('twitter_source.em');"
                    }
                }
            result = http_command(oh_host, oh_port, 'oh.objects.create', params=obj_params)
            if result is None or 'error' in result or 'id' not in result:
                print "Error creating object", result
            else:
                ho_id = result['id']
                object_grid[tweet_pos] = ho_id
                # Bad, but for now, lets us make sure that the command
                # handler has been registered so any requests to
                # create/update presences works.
                time.sleep(1)

        # Send message to add it to the right presence (maybe creating the presence in the Emerson script)
        tweet_group = tweet_grid[tweet_pos]
        if tweet_group is None:
            tweet_group = {
                'id' : tweet_grid.bin_id(tweet_pos),
                'count' : 0
                }
            tweet_grid[tweet_pos] = tweet_group
            print "[%d] Tweet triggered new tweet group, resulting in %d groups for %d tweets so far (%s)" % (tweeted_after, tweet_grid.num_active(), processed, tweet['text'])
        tweet_group['count'] += 1
        terms = tokenize_and_ngram(tweet['text'])

        # Add this tweet to its group's "mesh" data, or create it
        json_filename = '%d.json' % tweet_group['id']
        data_dir_primary = os.path.join(data_dir, json_filename[0])
        data_dir_secondary = os.path.join(data_dir_primary, json_filename[1])
        mesh_file = os.path.join(data_dir_secondary, json_filename)
        if os.path.exists(mesh_file):
            mesh_data = json.load(open(mesh_file, 'rb'))
        else:
            mesh_data = {'tweets': []}
            ensure_dir(data_dir_primary)
            ensure_dir(data_dir_secondary)
        mesh_data['tweets'].append({
                'text' : tweet['text'],
                'terms' : terms
                });
        json.dump(mesh_data, open(mesh_file, 'wb'))
        # The URL has an extra query parameter on the end to make each
        # version unique since we use the same basic ID for the object
        # but change the "mesh" file contents
        mesh_url = 'http://%s:%d/%s?v=%d' % (HTTP_HOST, HTTP_PORT, json_filename, len(mesh_data['tweets']))

        cmd_params = {
            'object' : ho_id,
            'event' : 'new_tweet',
            'group' : tweet_group['id'],
            'group_count' : tweet_group['count'],
            'pos' : {
                'lon' : tweet_pos.lon,
                'lat' : tweet_pos.lat,
                },
            'mesh' : mesh_url,
            'text' : tweet['text'],
            }
        result = http_command(oh_host, oh_port, 'oh.objects.command', params=cmd_params)
        if result is None or 'error' in result: print "Error handling command:", result and result['error']

# Leave HTTP server thread running after we finish loading objects
while True:
    time.sleep(1)
