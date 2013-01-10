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
