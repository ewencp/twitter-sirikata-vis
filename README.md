Sirikata Twitter Visualization
==============================

This repository contains scripts to run the various components of a
visualization of Twitter data in realtime using Sirikata. It consists
of:

* A collection script lets you use non-realtime data for
  repeatability.

* A python script drives the parsing of this data, some preprocessing
  before addition into Sirikata, including putting the Twitter data
  (equivalent of meshes in normal Sirikata) onto a "CDN" and
  allocating Sirikata objects and notifying them of changes to their
  state (requiring new presences, updates to those presences).

* Emerson scripts for objects which host many Twitter presences, each
  covering a very small geometric region filled with a few
  tweets. These scripts listen for commands from the python driver
  script above.

* A client Emerson script that uses the 2D Clutter renderer in
  Sirikata to render the "world" of Twitter data, including
  aggregates.

* Driver scripts to get all the components of Sirikata up and running.

Usage
-----

1. Collect data. Create credentials.json with your username and
   password and use collect.py, which will generate hourly files
   containing tweet data.

2. Start the space server and an object host with appropriate
   settings, enabling Twitter specific settings.

    # The region covers the US region <-129.02, 24.9, 0> to <-58.71,
    # 50.6, 0>. The particular region doesn't actually matter much
    # until you move to multiple space servers, but the starting
    # location of the client must be in this region.
    ./space_d --command.commander=http \
              --command.commander-options=--port=7777 \
              --space.extra-plugins=space-twitter \
              "--region=<<-129.02,24.9,-1000>,<-58.71,50.6,1000>>"
              --aggmgr=twitter \
              --prox=libprox-manual \
              --prox.oh.handler=rtreecut \
              --prox.oh.node-data=twitter-term-bloom \
              --aggmgr.host=localhost \
              --aggmgr.service=10000 \
              --twitter.bloom.buckets=8192 \
              --twitter.bloom.hashes=2

    # OH for Tweet objects
    ./cppoh_d --command.commander=http \
              --command.commander-options=--port=7779 \
              --object-factory-opts=--db=nothing.db \
              --objecthost=--scriptManagers=js:{--import-paths=/home/ewencp/twitter-vis.git/emerson} \
              --oh.query-processor=manual \
              --oh.query-data=twitter-term-bloom \
              --manual-query.handler=term-region \
              --manual-query.handler-node-data=twitter-term-bloom
              --twitter.bloom.buckets=8192 \
              --twitter.bloom.hashes=2

    # Client
    ./cppoh_d --command.commander=http \
              --command.commander-options=--port=7778 \
              --oh.extra-plugins=oh-clutter \
              --object-factory-opts=--db=/path/to/repo/scenes/twitter-client.db \
              --objecthost=--scriptManagers=js:{--import-paths=/home/ewencp/twitter-vis.git/emerson} \
              --oh.query-processor=manual \
              --oh.query-data=twitter-term-bloom \
              --manual-query.handler=term-region \
              --manual-query.handler-node-data=twitter-term-bloom
              --twitter.bloom.buckets=8192 \
              --twitter.bloom.hashes=2

3. Replay the data with the Python script:

    ./replay tweets-[some-date-info].log

   which will read tweets from the file, do some processing and add
   "meshes" to the "CDN", generate objects on the object hosts, and
   use those objects to create presences for tweets.

4. Also run a client to visualize the world as tweets are added.
