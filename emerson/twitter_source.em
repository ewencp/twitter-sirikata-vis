// Copyright (c) 2013 Sirikata Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can
// be found in the LICENSE file.


var init = function() {
    system.registerCommandHandler(
        function(data) {
            if (data.event === undefined)
                return { 'error' : 'Invalid format' };

            system.print('Creating tweet presence at <' + data.pos.lon + ', ' + data.pos.lat + '> ("' + data.text + '")\n');
            system.createPresence({
                'space': '12345678-1111-1111-1111-DEFA01759ACE',
                'pos': <data.pos.lon, data.pos.lat, 0>,
                //'orient': x,
                'mesh': '',
                'scale': 1,
                //'solidAngleQuery': x,
                'callback': function(pres) {
                    if (!pres)
                        system.print("Failed to connect for tweet (" + data.text + ")\n");
                }
            });

            return {
                'success' : 'true'
            };
        }
    );
};

init();