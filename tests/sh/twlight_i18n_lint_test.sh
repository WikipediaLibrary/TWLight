#!/usr/bin/env bash

shopt -s expand_aliases

testBadPyNewlines() {
    start=1
    end=6
    for ((i=$start; i<=$end; i++))
    do
        file=${TWLIGHT_HOME}/tests/sh/data/bad_i18n_newline_$i.py
        assertTrue "${file} should cause an error." "perl ${TWLIGHT_HOME}/bin/twlight_i18n_lint.pl ${file}"
    done
}

. ${TWLIGHT_HOME}/bin/shunit2
