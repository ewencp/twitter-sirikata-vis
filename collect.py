#!/usr/bin/env python

import json
import tweetstream
import time, datetime, os

with open('credentials.json', 'r') as fp:
    cred = json.load(fp)

delay = 1
out_fp_dt = datetime.datetime.now()
out_fp = None
started = datetime.datetime.now()
while True:
    try:
        count = 0
        missed_count = 0
        #locations = ["-180,-90,180,90"] # Everything
        locations = ["-129.02,24.9,-58.71,50.6"] # ~ United States
        #locations = ["-122.75,36.8,-121.75,37.8"] # ~ San Francisco
        with tweetstream.FilterStream(cred["username"], cred["password"], locations=locations) as stream:
            for tweet in stream:
                # Skip deletions
                if u"delete" in tweet: continue
                # We might bump up against limits. We'll be limited
                # for the global, unfiltered stream no matter what. If
                # we hit that limit when filtering, we'll be notified
                # that we're missing tweets. Not a real problem, we
                # can just log the information and let the user know
                if u"limit" in tweet:
                    missed_count = tweet[u"limit"][u"track"]
                    continue
                # print anything we don't understand
                if not u"user" in tweet or not u"text" in tweet:
                    print tweet
                else:
                    cur_dt = datetime.datetime.now()
                    if cur_dt.hour != out_fp_dt.hour:
                        out_fp_dt = cur_dt
                        if out_fp is not None:
                            out_fp.close()
                            out_fp = None
                    if out_fp is None:
                        out_fp = open('tweets-%d-%d-%d-%d.log' % (out_fp_dt.year, out_fp_dt.month, out_fp_dt.day, out_fp_dt.hour), 'ab')

                    print >>out_fp, "%s\r" % (json.dumps(tweet))
                    count += 1
                    if count % 1000 == 0:
                        out_fp.flush()
                        os.fsync(out_fp.fileno())
                        current = datetime.datetime.now()
                        print "Recorded %d tweets in %s (%f tweets/s)" % (count, str(current-started), float(count)/(current-started).seconds),
                        if missed_count > 0:
                            print "and missed %d tweets (%f tweets/s)" % (missed_count, float(missed_count)/(current-started).seconds)
                        else:
                            print
    except tweetstream.ConnectionError, e:
        print "Disconnected from twitter. Reason:", e.reason

    # On disconnect, delay. Just do exponential backoff, we don't need
    # enough data to care about anything more complicated (or reducing
    # the timeout)
    time.sleep(delay)
    delay *= 2

out_fp.close()
