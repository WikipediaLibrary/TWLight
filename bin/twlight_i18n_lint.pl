#!/usr/bin/env perl

# Checks for localization issues.
# https://phabricator.wikimedia.org/T255167

use strict;
use warnings;
use feature "switch";
use Term::ANSIColor;

# Experimental features add warning output, which we don't want in our CI logs.
no warnings 'experimental';

# Exit code.
my $code = 0;

# File extensions we allow for searching.
my %allowed = (
    'html' => 1,
    'py' => 1
);

# We take a file path as the first argument.
my $filename = $ARGV[0];

# Extract the extension from the input filename.
$filename =~ /\.([^.]+)$/;
my $extension = $1;

# Only proceed if the file extension is allowed.
if (exists($allowed{$extension})) {

    # Capture file content as string.
    my $input = do { local $/; <> };

    given($extension) {

        # Python files.
        when($extension eq 'py') {

            # Check for newlines that can cause message mismatches with translatewiki.
            my @newline_errors = ($input =~ /(?<!_)_\(\n((?:[ \t]*)?(?:"|')[^\n]*(?:"|')\n?)+(?:[ \t]*)\)/sg);
            foreach my $match (@newline_errors) {
                my $message = "ugettext messages should't be preceded by a newline";
                print_error($message, $filename, $input, $match) if $match;
            }

            # Check for messages not preceded by a translator comment with a max length of 240 characters.
            # Note the variable-width negative lookbehind, which has experimental support.
            # We're keeping the pattern within the limitations of the engine.
            my @comment_errors = ($input =~ /(?<!# Translators:[^\n]{1,240})\n([^\n]*(?<!_)_\((?:[ \t]*"[^\n]*"\n?)+[ \t]*\)[^\n]*\n)/sg);

            foreach my $match (@comment_errors) {
                my $message = 'Missing or overlong (> 240 chars) translator comment';
                print_error($message, $filename, $input, $match) if $match;
            }
        }

        # HTML files.
        # @TODO: clean up these expressions based on the work done on the python expressions.
        when ($extension eq 'html') {
            # Check for blocktrans without the 'trimmed' option, which allows arbitrary newline changes.
            # These easily create message mismatches with translatewiki.
            my @blocktrans_trimmed_errors = ($input =~ /([^\n]*\{% blocktrans(?! trimmed) %\}[^\n]*)\n/sg);
            foreach my $match (@blocktrans_trimmed_errors) {
                my $message = "blocktrans used without trimmed option";
                print_error($message, $filename, $input, $match) if $match;
            }

            # Check for messages not preceded by a translator comment with a max length of 213 characters.
            # Note the variable-width negative lookbehind, which has experimental support.
            # We're keeping the pattern within the limitations of the engine.
            my @trans_comment_errors = ($input =~ /(?<!\{% comment %\}Translators:[^\n]{1,213}\{% endcomment %\}\n)([ \t]*\{% trans "[^\n]*" %\}[^\n]*\n)/sg);
            foreach my $match (@trans_comment_errors) {
                my $message = 'Missing or overlong (> 213 chars) translator comment';
                print_error($message, $filename, $input, $match) if $match;
            }
            my @blocktrans_comment_errors = ($input =~ /(?<!\{% comment %\}Translators:[^\n]{1,213}\{% endcomment %\}\n)([ \t]*\{% blocktrans[^\n]* %\}[^\n]*\n)/sg);
            foreach my $match (@blocktrans_comment_errors) {
                my $message = 'Missing or overlong (> 213 chars) translator comment';
                print_error($message, $filename, $input, $match) if $match;
            }
        }
    }
}

# Prints errors. Surpise!
sub print_error {

    my $message = $_[0];
    my $filename = $_[1];
    my @input = split /\n/, $_[2];
    # Drop newlines that complicate comparison.
    chomp(my $match = $_[3]);

    # Loop through the input lines
    for my $i (0 .. $#input) {
        # Print the error with line number when we get to the match.
        if (index($input[$i], $match) != -1) {
            my $number = $i + 1;
            $code = 1;
            print colored("ERROR: $message\n$filename:$number\n$match\n", 'red');
        }
    }
}

exit $code;
