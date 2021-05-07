#!/usr/bin/env bash

shopt -s expand_aliases

testBadPyNewlines() {
    prefix=${TWLIGHT_HOME}/tests/shunit/data/bad_i18n_newline_
    for i in ${prefix}*.py
    do
        assertFalse "${file} should cause an error." "${TWLIGHT_HOME}/bin/twlight_i18n_lint.pl ${i}"
    done
}

testGoodPy() {
    prefix=${TWLIGHT_HOME}/tests/shunit/data/good_i18n_
    for i in ${prefix}*.py
    do
        assertTrue "${file} should not cause an error." "${TWLIGHT_HOME}/bin/twlight_i18n_lint.pl ${i}" ||:
    done
}

testBadPyComments() {
    prefix=${TWLIGHT_HOME}/tests/shunit/data/bad_i18n_comment_
    for i in ${prefix}*.py
    do
        assertFalse "${file} should cause an error." "${TWLIGHT_HOME}/bin/twlight_i18n_lint.pl ${i}"
    done
}

. ${TWLIGHT_HOME}/tests/shunit/shunit2
