// Copyright (c) 2013 Sirikata Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can
// be found in the LICENSE file.

system.require('std/clutter.em');

var win_size = <844*2, 375*2, 0>;
var divs = <300, 300, 0>;

// ~ United States
var world_min = <-129.02, 24.9, 0>;
var world_max = <-58.71, 50.6, 0>;

var region_min = world_min;
var region_max = world_max;
//region_min = <-76.1859711937204, 39.40015416666667, 0>;
//region_max = <-73.98878369372039, 40.203279166666675, 0>;

// Get the scaling factor given the current view region
var zoom_scale_factor = function() {
    // We assume regions are set to match aspect ratio of window/world
    return (world_max.x-world_min.x)/(region_max.x-region_min.x);
}

// Get scale of one division
var div_scale = function() {
    return <win_size.x/divs.x, win_size.y/divs.y, 0> * zoom_scale_factor();
}
var div_scale_avg = function() {
    return (win_size.x/divs.x + win_size.y/divs.y)/2 * zoom_scale_factor();
}

var world_div_size = function() {
    return <(world_max.x - world_min.x)/divs.x, (world_max.y - world_min.y)/divs.y, 0>;
}
var world_div_size_avg = function() {
    var wds = world_div_size();
    return (wds.x + wds.y)/2;
}


var world_to_screen = function(pos) {
    var frac_x = (pos.x - region_min.x) / (region_max.x - region_min.x);
    var frac_y = (pos.y - region_min.y) / (region_max.y - region_min.y);
    return <frac_x*win_size.x, (1-frac_y)*win_size.y, 0>;
}

var screen_to_world = function(pos) {
    var frac_x = (pos.x/win_size.x);
    var frac_y = (pos.y/win_size.y);
    var result_x = region_min.x + frac_x * (region_max.x - region_min.x);
    var result_y = region_min.y + (1.0-frac_y) * (region_max.y - region_min.y);
    return <result_x, result_y, 0>;
}

var init = function() {
    var query_term = "#prayfornewtown";
    var query_results = 30;

    var update_query = function() {
        var query = {
            'term' : query_term,
            'region' : {
                'min' : [region_min.x, region_min.y],
                'max' : [region_max.x, region_max.y]
            },
            'results' : query_results
        };
        system.self.query = JSON.stringify(query);
    };

    renderer = new std.clutter.ClutterRenderer(system.self);
    renderer.stage_set_size(win_size.x, win_size.y);
    renderer.stage_set_color(0, 0, 0);

    background_texture = renderer.texture_create_from_file("/home/ewencp/us_map_cropped.png");
    var update_background_pos_size = function() {
        var sz = <win_size.x*zoom_scale_factor(), win_size.y*zoom_scale_factor(), 0>;
        renderer.actor_set_size(background_texture, win_size.x*zoom_scale_factor(), win_size.y*zoom_scale_factor());
        var background_pos = world_to_screen(<world_min.x, world_max.y, 0>);
        system.print("Background position and size: " + background_pos.toString() + '  ' + sz.toString() + '\n');
        renderer.actor_set_position(background_texture, background_pos.x, background_pos.y);
    }
    update_background_pos_size();
    renderer.actor_show(background_texture);
    // Clicking on the background zooms
    var on_click = function(x, y, button) {
        var world_click_pos = screen_to_world(<x, y, 0>);
        var cur_size = region_max - region_min;

        var new_region_min = world_click_pos - cur_size/4;
        var new_region_max = world_click_pos + cur_size/4;

        if (new_region_min.x < world_min.x) {
            new_region_max.x = new_region_max.x + (world_min.x - new_region_min.x);
            new_region_min.x = world_min.x;
        }
        if (new_region_min.y < world_min.y) {
            new_region_max.y = new_region_max.y + (world_min.y - new_region_min.y);
            new_region_min.y = world_min.y;
        }

        system.print("New zoom region: " + new_region_min.toString() + " -- " + new_region_max.toString() + "\n");
        region_min = new_region_min;
        region_max = new_region_max;
        update_all_position_size();
        // To account for things outside our view but which will still be results
        query_results = query_results + 40;
        update_query();
    }
    renderer.actor_on_mouse_press(background_texture, function(x, y, button) { on_click(x, y, button); });


    var query_text_entry = renderer.text_create();
    renderer.text_set_color(query_text_entry, 0, 0, 0);
    renderer.text_set_text(query_text_entry, query_term);
    renderer.text_set_editable(query_text_entry, true);
    renderer.text_set_single_line(query_text_entry, true);
    renderer.text_on_activate(
        query_text_entry,
        function() {
            query_term = renderer.text_get_text(query_text_entry);
            system.print('Updating query term to "' + query_term + '"\n');
            update_query();
        }
    );
    renderer.actor_set_size(query_text_entry, 900, 20);
    renderer.actor_set_position(query_text_entry, 0, 0);
    renderer.actor_show(query_text_entry);
    renderer.stage_set_key_focus(query_text_entry);
    update_query(); // set initial query

    var dots = {};
    var labels = {};
    var render_updaters = {};

    var update_all_position_size = function() {
        update_background_pos_size();
        for(var vis_id in render_updaters) {
            render_updaters[vis_id]();
        }
    }

    system.self.onProxAdded(function(vis) {
        // Ugly hack, but keeps us from including top-level pinto
        // results, which currently aren't being cleared out properly
        // when we move to the lower-level trees.
        if (vis.scale > 500)
            return;

        //var rect_id = renderer.rectangle_create();
        var rect_id = renderer.circle_create();
        var label_id = undefined;
        var hovering = undefined;

        //renderer.rectangle_set_color(rect_id, 127, 127, 127);
        renderer.circle_set_fill_color(rect_id, 127, 127, 127);
        renderer.circle_set_border_color(rect_id, 127*0.5, 63, 63, 127);
        renderer.circle_set_border_width(rect_id, 3);

        var set_pos_size_color = function(vis) {
            // pos
            var screen_pos = world_to_screen(vis.position);
            renderer.actor_set_position(rect_id, screen_pos.x, screen_pos.y);
            if (label_id !== undefined)
                renderer.actor_set_position(label_id, screen_pos.x, screen_pos.y-10);


            var sc = vis.scale;
            if (sc < 1) // Individual tweet group. Scale based on divisions, but also try to fit things without overlap....
                sc = world_div_size_avg() * 0.25;

            var col = sc-1;
            if (col > 16) col = 16;
            if (col < 0) col = 0;
            col = 127 + (8 * col);

            if (hovering !== undefined && hovering.toString() == vis.toString())
                col = col + 64;

            if (col > 255) col = 255;

            var r = col, g = 127, b = 127;
            if (hovering !== undefined && hovering.toString() == vis.toString()) {
                var x = r;
                r = g;
                g = x;
            }
            //renderer.rectangle_set_color(rect_id, r, g, b, 127);
            renderer.circle_set_fill_color(rect_id, r, g, b, 127);
            renderer.circle_set_border_color(rect_id, r*0.5, g*0.5, b*0.5, 127);
            // The base scaling without zoom so we can make sizes logarithmic with zoom
            //var scale_to_win = <win_size.x/(world_max.x - world_min.x), win_size.y/(world_max.y - world_min.y), 0>;
            //system.print('scale: ' + vis.scale + ' '  + sc * scale_to_win.x * (1+Math.log(zoom_scale_factor())) + '\n');
            //renderer.actor_set_size(rect_id, sc * scale_to_win.x * (1+Math.log(zoom_scale_factor())), sc * scale_to_win.y * (1+Math.log(zoom_scale_factor())));
            //renderer.circle_set_radius(rect_id, sc * (scale_to_win.x+scale_to_win.y)/2 * (1+Math.log(zoom_scale_factor())) * Math.sqrt(2));
            var scale_factor = <win_size.x/divs.x, win_size.y/divs.y, 0> * (1+Math.log(zoom_scale_factor())/Math.log(1.2));
            renderer.actor_set_size(rect_id, sc * scale_factor.x, sc * scale_factor.y);
            renderer.circle_set_radius(rect_id, sc * (scale_factor.x+scale_factor.y)/2);
            //renderer.actor_set_size(rect_id, sc * div_scale().x, sc * div_scale().y);
            //renderer.circle_set_radius(rect_id, sc * div_scale_avg());
        }
        vis.onPositionChanged(set_pos_size_color);
        vis.onScaleChanged(set_pos_size_color);
        set_pos_size_color(vis);

        var on_hover = function(vis) {
            system.print('on hover ' + vis.toString() + ' ' + vis.mesh + '\n');
            if (hovering !== undefined)
                on_unhover(hovering);
            hovering = vis;
            set_pos_size_color(vis);
        };
        renderer.actor_on_mouse_enter(rect_id, function() { on_hover(vis); });
        var on_unhover = function(vis) {
            system.print('on unhover ' + vis.toString() + '\n');
            // Clear and unhighlight
            if (hovering !== undefined && hovering.toString() == vis.toString()) {
                hovering = undefined;
                set_pos_size_color(vis);
            }
        };
        renderer.actor_on_mouse_leave(rect_id, function() { on_unhover(vis); });
        renderer.actor_on_mouse_press(rect_id, function(x, y, button) { on_click(x, y, button); });

        var cur_mesh = undefined;
        var getMesh = function(vis) {
            // Might get spurious updates
            if (vis.mesh === cur_mesh) return;
            cur_mesh = vis.mesh;

            var mesh = vis.mesh;
            if (mesh.substr(0, 7) != "http://") return;
            system.http.get(
                mesh, undefined,
                function(success, result) {
                    // May have been removed while downloading
                    if (dots[vis.toString()] == undefined) return;

                    if (mesh != vis.mesh) return; // mesh changed, ignore
                    if (result.statusCode != 200) return;
                    //system.print("Got data for " + mesh + " of size " + result.data.length + '\n');

                    var data = JSON.parse(result.data);
                    var display_text = "";
                    if (data.clusters === undefined) {
                        // Individual tweet
                        tweet = data.tweets[ Math.floor(Math.random()*data.tweets.length*100) % data.tweets.length ];
                        var parts = tweet.text.split(' ');
                        // Split for wrapping
                        for(var idx in parts) {
                            display_text = display_text + parts[idx];
                            if (idx % 4 == 3)
                                display_text = display_text + '\n';
                            else
                                display_text = display_text + ' ';
                        }
                    }
                    else {
                        //system.print("Clusters for " + mesh + '\n');
                        for(var idx in data.clusters) {
                            //system.print(' Cluster ' + idx + '\n');
                            var max_term = '', max_frequency = 0;
                            for(var tidx in data.clusters[idx].terms) {
                                if (data.clusters[idx].terms[tidx].frequency > max_frequency) {
                                    max_term = data.clusters[idx].terms[tidx].term;
                                    max_frequency = data.clusters[idx].terms[tidx].frequency;
                                }
                                //system.print('   ' + data.clusters[idx].terms[tidx].term + ' (' + data.clusters[idx].terms[tidx].frequency + ')\n');
                            }
                            display_text = display_text + max_term + '\n';
                        }
                    }

                    if (label_id === undefined) {
                        label_id = renderer.text_create();
                        labels[vis.toString()] = label_id;
                        renderer.text_set_color(label_id, 0, 0, 0);
                        renderer.text_set_font(label_id, "Sans 10");
                        renderer.actor_set_size(label_id, 100, 100);
                        renderer.actor_show(label_id);
                        // Force repositioning just so we get the label in the right starting position
                        set_pos_size_color(vis);

                        renderer.actor_on_mouse_enter(label_id, function() { on_hover(vis); });
                        renderer.actor_on_mouse_leave(label_id, function() { on_unhover(vis); });
                        renderer.actor_on_mouse_press(label_id, function(x, y, button) { on_click(x, y, button); });
                    }
                    renderer.text_set_text(label_id, display_text);
                }
            );
        };
        vis.onMeshChanged(getMesh);
        getMesh(vis);

        renderer.actor_show(rect_id);
        dots[vis.toString()] = rect_id;
        render_updaters[vis.toString()] = function() { set_pos_size_color(vis); };
    });

    system.self.onProxRemoved(function(vis) {
        var rect_id = dots[vis.toString()];
        if (rect_id !== undefined)
            renderer.actor_destroy(rect_id);

        var label_id = labels[vis.toString()];
        if (label_id !== undefined)
            renderer.actor_destroy(label_id);

        var updater = render_updaters[vis.toString()];
        if (updater !== undefined) delete render_updaters[vis.toString()];

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
