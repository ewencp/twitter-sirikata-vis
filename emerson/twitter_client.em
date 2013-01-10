// Copyright (c) 2013 Sirikata Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can
// be found in the LICENSE file.

// A sane, simple, default. Only includes functionality from libraries.
system.require('std/shim/restore/simpleStorage.em');

std.simpleStorage.setScript(
    function()
    {
        system.require('std/shim/restore/persistService.em');
        system.require('std/scriptingGui/fileReceiver.em');
        system.require('std/movement/movable.em');
        system.require('std/movement/animatable.em');
        system.require('std/twitter.em');

        scriptable = new std.script.Scriptable();
        movable = new std.movement.Movable(true); // Self only
        animatable = new std.movement.Animatable();

        // For convenience in debugging, figuring out who's trying to
        // contact you, etc, while we don't have a UI for it, print
        // out any requests that ask you to
        function(msg, sender) { system.prettyprint('Message from ', sender.toString(), ': ', msg); } << [{'printrequest'::}];


        var init = function() {
            renderer = new std.twitter.TwitterRenderer(system.self);
            system.registerCommandHandler(
                function(data) {
                    if (data.event === undefined)
                        return { 'error' : 'Invalid format' };

                    system.print('Creating tweet presence at <' + data.pos.lon + ', ' + data.pos.lat + '> ("' + data.text + '")');

                    return {
                        'success' : 'true'
                    };
                }
            );
        };

        if (system.self)
        {
            //already have a connected presence, use it.
            init();
        }
        else if (system.presences.length != 0)
        {
            system.changeSelf(system.presences[0]);
            //already have a connected presence, use it.
            init();
        }
        else
        {
            //if do not have a connected presence
            system.onPresenceConnected(
                function(pres,toClearPresFunction) {
                    init();
                    toClearPresFunction.clear();
                }
            );
        }
    }, true);
