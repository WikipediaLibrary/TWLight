#!/usr/bin/env node

// Load modules
var fs = require('fs');
var cssjanus = require('cssjanus');

// Recursively search directory for files. Cribbed from:
// https://stackoverflow.com/a/21459809
var _getAllFilesFromFolder = function(dir) {

    var results = [];

    fs.readdirSync(dir).forEach(function(file) {

        file = dir+'/'+file;
        var stat = fs.statSync(file);

        if (stat && stat.isDirectory()) {
            results = results.concat(_getAllFilesFromFolder(file))
        } else results.push(file);

    });

    return results;

};

// Get all the files from the css dir
var infiles = _getAllFilesFromFolder('./TWLight/static/css');

// Loop through all the files
infiles.forEach(function(infile) {
    
    // Check for files with .css extension
    // but ignore files that we've already converted
    if (!infile.endsWith('-rtl.css')) {
        // Set up output filename to be the same as the input, but ending in -rtl.css.
        var outfile = infile.replace(new RegExp(/^(.+)\.css$/), '$1-rtl.css');
        if ( typeof outfile !== 'undefined' && outfile) {
        
            // Read left to right css, create right to left css
            var ltrcss = fs.readFileSync(infile, 'utf8');
            var rtlcss = cssjanus.transform(ltrcss);
            
            // Write right to left css to file
            fs.writeFileSync(outfile, rtlcss, 'utf8');
        };
    };
});
