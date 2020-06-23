#!/usr/bin/perl

# Checks for localization issues.
# https://phabricator.wikimedia.org/T255167

use strict;
use warnings;
use Term::ANSIColor;
# Experimental features add warning output, which we don't want in our CI logs.
no warnings 'experimental';
# Exit code.
my $code = 0;

# We take a file path as the first argument.
my $filename = $ARGV[0];
my $input = do { local $/; <> };

# Check for newlines that can cause message mismatches with translatewiki.
my @newline_errors = ($input =~ /(?<!_)_\(\n(([ \t]*)?"[^\n]*"\n?)*([ \t]*)\)/sg);
foreach my $match (@newline_errors) {
    my $error = "ugettext messages should't be preceded by a newline";
    print_error($error, $filename, $input, $match);
}

# Check for messages not preceded by a translator comment.
# These will not be picked up for localization.
# Note the variable-width negative lookbehind, which has experimental support.
# We're keeping it the pattern well within the limitations of the engine.
my @missing_comment_errors = ($input =~ /(?<!# Translators:[^\n]{1,240}\n)([^\n]*(?<!_)_\((([ \t]*)?"[^\n]*"\n?)*([ \t]*)\)[^\n]\n)/sg);
foreach my $match (@missing_comment_errors) {
    my $error = "Missing Translator comment";
    print_error($error, $filename, $input, $match);
}

# Print the errors.
sub print_error {
    my $error = $_[0];
    my $filename = $_[1];
    my @input = split /\n/, $_[2];
    chomp(my $match = $_[3]);
    if (length($match) > 0) {
        for my $i (0 .. $#input) {
            if ("$input[$i]" eq "$match") {
                my $number = $i + 1;
                $code = 1;
                print colored("ERROR: $error\n$filename:$number\n$match\n", 'red');
            }
        }
    }
}

exit $code;
