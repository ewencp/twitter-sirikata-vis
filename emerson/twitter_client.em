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
        system.require('std/clutter.em');

        scriptable = new std.script.Scriptable();
        movable = new std.movement.Movable(true); // Self only
        animatable = new std.movement.Animatable();

        // For convenience in debugging, figuring out who's trying to
        // contact you, etc, while we don't have a UI for it, print
        // out any requests that ask you to
        function(msg, sender) { system.prettyprint('Message from ', sender.toString(), ': ', msg); } << [{'printrequest'::}];


        var init = function() {
            renderer = new std.clutter.ClutterRenderer(system.self);
            renderer.stage_set_size(900, 600);
            renderer.stage_set_color(0, 0, 0);
            var dots = {};

            system.self.onProxAdded(function(vis) {
                var rect_id = renderer.rectangle_create();
                renderer.rectangle_set_color(rect_id, 127, 127, 127);

                // ~ United States
                var world_min = <-129.02, 24.9, 0>;
                var world_max = <-58.71, 50.6, 0>;
                var win_size = <800, 600, 0>;
                var frac_x = (vis.position.x - world_min.x) / (world_max.x - world_min.x);
                var frac_y = (vis.position.y - world_min.y) / (world_max.y - world_min.y);
                renderer.actor_set_position(rect_id, frac_x*win_size.x, (1-frac_y)*win_size.y);

                //renderer.actor_set_size(rect_id, vis.scale, vis.scale);
                renderer.actor_set_size(rect_id, 2, 2);
                renderer.actor_show(rect_id);

                dots[vis.toString()] = rect_id;

                vis.onScaleChanged(function(vis) {
                    //renderer.actor_set_size(rect_id, vis.scale, vis.scale);
                    var col = vis.scale-1;
                    if (col > 16) col = 16;
                    col = 127 + (8 * col);
                    renderer.rectangle_set_color(rect_id, col, 127, 127);
                });
            });

            system.self.onProxRemoved(function(vis) {
                var rect_id = dots[vis.toString()];
                if (rect_id !== undefined) {
                    renderer.actor_destroy(rect_id);
                }
            });
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
