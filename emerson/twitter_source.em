// Copyright (c) 2013 Sirikata Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can
// be found in the LICENSE file.


// Maintain info for each grouping of tweets we're informed
// about. Should include info about tweets we need, the presence used
// to represent it in the world, etc. Keyed by the identifiers
// provided by commands which update these groups
groups = {};

var init = function() {
    system.registerCommandHandler(
        function(data) {
            if (data.event === undefined)
                return { 'error' : 'Invalid format' };

            // Initialize the new group, creating a new presence, if necessary
            var group_id = data.group;
            if (groups[group_id] === undefined) {

                groups[group_id] = {
                    'presence' : null,
                    'presence_ready_callbacks' : [],
                    'notify_presence_ready' : function(pres) {
                        for(var cbi in this.presence_ready_callbacks)
                            this.presence_ready_callbacks[cbi](pres);
                        this.presence_ready_callbacks = [];
                    },
                    'add_presence_ready_callback' : function(cb) {
                        this.presence_ready_callbacks.push(cb);
                        if (this.presence !== null)
                            this.notify_presence_ready(this.presence);
                    }
                };

                //system.print('Creating tweet group presence at <' + data.pos.lon + ', ' + data.pos.lat + '> ("' + data.text + '")\n');
                //system.print('Creating tweet group presence with "mesh" URL ' + data.mesh + '\n');
                system.createPresence({
                    'space': '12345678-1111-1111-1111-DEFA01759ACE',
                    'pos': <data.pos.lon, data.pos.lat, 0>,
                    //'orient': x,
                    'mesh': data.mesh,
                    'scale': 1,
                    //'solidAngleQuery': x,
                    'callback': function(pres) {
                        if (!pres)
                            system.print("Failed to connect for tweet (" + data.text + ")\n");
                        groups[group_id].presence = pres;
                        groups[group_id].notify_presence_ready(pres);
                    }
                });

            }
            else {
                var group = groups[group_id];
                group.add_presence_ready_callback(function(pres) {
                    system.print('Group ' + data.group + ' grew to size ' + data.group_count + '\n');
                    pres.scale = data.group_count;
                    pres.mesh = data.mesh;
                });
            }

            return {
                'success' : 'true'
            };
        }
    );
};

init();