#!/usr/bin/env bash

shopt -s expand_aliases

testBadPyNewlines() {
    prefix=${TWLIGHT_HOME}/tests/shunit/data/bad_i18n_newline_
    for file in ${prefix}*.py
    do
        assertFalse "${file} should cause an error." "${TWLIGHT_HOME}/bin/twlight_i18n_lint.pl ${file}"
    done
}

testGoodPy() {
    prefix=${TWLIGHT_HOME}/tests/shunit/data/good_i18n_
    for file in ${prefix}*.py
    do
        assertTrue "${file} should not cause an error." "${TWLIGHT_HOME}/bin/twlight_i18n_lint.pl ${file}" ||:
    done
}

testBadPyComments() {
    prefix=${TWLIGHT_HOME}/tests/shunit/data/bad_i18n_comment_
    for file in ${prefix}*.py
    do
        assertFalse "${file} should cause an error." "${TWLIGHT_HOME}/bin/twlight_i18n_lint.pl ${file}"
    done
}

. ${TWLIGHT_HOME}/tests/shunit/shunit2
