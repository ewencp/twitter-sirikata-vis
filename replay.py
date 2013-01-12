#!/usr/bin/env python

import sys, json, time, calendar
from collections import namedtuple
from itertools import chain, product

import httplib, urllib, socket, math

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
oh_port = 7778
speed_factor = 1

with open(sys.argv[1], 'r') as fp:
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
        cmd_params = {
            'object' : ho_id,
            'event' : 'new_tweet',
            'group' : tweet_group['id'],
            'group_count' : tweet_group['count'],
            'pos' : {
                'lon' : tweet_pos.lon,
                'lat' : tweet_pos.lat,
                },
            'text' : tweet['text'],
            }
        result = http_command(oh_host, oh_port, 'oh.objects.command', params=cmd_params)
        if result is None or 'error' in result: print "Error handling command:", result and result['error']
