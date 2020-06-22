#!/usr/bin/perl
use strict;
use warnings;
no warnings 'experimental';

# Checks for localization issues.
# https://phabricator.wikimedia.org/T255167

my $filename = $ARGV[0];
my $code = 0;
my $input = do { local $/; <> };

my @newline_errors = ($input =~ /(?<!_)_\(\n(([ \t]*)?"[^\n]*"\n?)*([ \t]*)\)/sg);
foreach my $match (@newline_errors) {
    my $error = "ugettext messages can't be preceded by a newline, even though it's valid python";
    print_error($error, $filename, $input, $match);
}

my @missing_comment_errors = ($input =~ /(?<!# Translators:[^\n]{1,240}\n)([^\n]*(?<!_)_\((([ \t]*)?"[^\n]*"\n?)*([ \t]*)\)[^\n]\n)/sg);
foreach my $match (@missing_comment_errors) {
    my $error = "Missing Translator comment";
    print_error($error, $filename, $input, $match);
}

sub print_error {
    my $error = $_[0];
    my $filename = $_[1];
    my @input = split /\n/, $_[2];
    chomp(my $match = $_[3]);
    if (length($match) > 0) {
        for my $i (0 .. $#input) {
            if ("$input[$i]" eq "$match") {
                my $number = $i + 1;
                print "ERROR: $filename:$number $error\n";
                print "$match\n";
                $code = 1;
            }
        }
    }
}

exit $code;
