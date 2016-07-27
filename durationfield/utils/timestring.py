# -*- coding: utf-8 -*-
"""
Utility functions to convert back and forth between a timestring and timedelta.
"""

from django.conf import settings
from django.core.exceptions import ValidationError

from datetime import timedelta
import re

ALLOW_MONTHS = getattr(settings, "DURATIONFIELD_ALLOW_MONTHS", False)
ALLOW_YEARS = getattr(settings, "DURATIONFIELD_ALLOW_YEARS", False)
MONTHS_TO_DAYS = getattr(settings, "DURATIONFIELD_MONTHS_TO_DAYS", 30)
YEARS_TO_DAYS = getattr(settings, "DURATIONFIELD_YEARS_TO_DAYS", 365)


def str_to_timedelta(td_str):
    """
    Returns a timedelta parsed from the native string output of a timedelta.

    Timedelta displays in the format ``X day(s), H:MM:SS.ffffff``
    Both the days section and the microseconds section are optional and ``days``
    is singular in cases where there is only one day.

    Additionally will handle user input in months and years, translating those
    bits into a count of days which is 'close enough'.
    """
    if not td_str:
        return None

    time_format = r"(?:(?P<weeks>\d+)\W*(?:weeks?|w),?)?\W*(?:(?P<days>\d+)\W*(?:days?|d),?)?\W*(?:(?P<hours>\d+):(?P<minutes>\d+)(?::(?P<seconds>\d+)(?:\.(?P<microseconds>\d+))?)?)?"
    if ALLOW_MONTHS:
        time_format = r"(?:(?P<months>\d+)\W*(?:months?|m),?)?\W*" + time_format
    if ALLOW_YEARS:
        time_format = r"(?:(?P<years>\d+)\W*(?:years?|y),?)?\W*" + time_format
    time_matcher = re.compile(time_format)
    time_matches = time_matcher.match(td_str)
    time_groups = time_matches.groupdict()

    # If passed an invalid string, the regex will return all None's, so as
    # soon as we get a non-None value, we are more confident the string
    # is valid (possibly some invalid numeric formats this will not catch.
    # Refs #11
    is_valid = False
    for key in time_groups.keys():
        if time_groups[key] is not None:
            is_valid = True
            value = time_groups[key]
            if key == 'microseconds':
                # When parsing time regex, make sure the microseconds value
                # uses the correct number of digits. This must be correctly
                # padded so 3.14 == 3.140 == 3.1400 == 3.14000 == 3.140000
                # 3.14 == 3 seconds 140,000 microseconds
                value = value.ljust(6, '0')
            time_groups[key] = int(value)

        else:
            time_groups[key] = 0

    if not is_valid:
        raise ValidationError("Invalid timedelta string, '{0}'".format(td_str))

    if "years" in time_groups.keys():
        time_groups["days"] = time_groups["days"] + (time_groups["years"] * YEARS_TO_DAYS)
    if "months" in time_groups.keys():
        time_groups["days"] = time_groups["days"] + (time_groups["months"] * MONTHS_TO_DAYS)
    time_groups["days"] = time_groups["days"] + (time_groups["weeks"] * 7)

    return timedelta(
        days=time_groups["days"],
        hours=time_groups["hours"],
        minutes=time_groups["minutes"],
        seconds=time_groups["seconds"],
        microseconds=time_groups["microseconds"]
    )
