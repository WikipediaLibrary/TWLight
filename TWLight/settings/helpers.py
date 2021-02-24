import re
from typing import Any


def sentry_before_send(event: dict, hint: dict):
    """
    Callback for sentry's client-side event filtering.
    We're using it to mask sensitive data.
    https://docs.sentry.io/platforms/python/configuration/filtering/#filtering-error-events
    Parameters
    ----------
    event : dict
        Sentry event dictionary object
    hint : dict
        Source data dictionary used to create the event.
        https://docs.sentry.io/platforms/python/configuration/filtering/#using-hints
    Returns
    -------
    dict
        The modified event.
    """
    # We catch any exception, because if we don't, the event is dropped.
    # We want to keep passing them on so we can continually improve our scrubbing
    # while still sending events.
    # noinspection PyBroadException
    try:
        event = _scrub_event(event)
    except:
        pass

    return event


def _mask_pattern(dirty: str):
    """
    Masks out known sensitive data from string.
    Parameters
    ----------
    dirty : str
        Input that may contain sensitive information.
    Returns
    -------
    str
        Output with any known sensitive information masked out.
    """
    # DB credentials as found in called processes.
    call_proc_db_creds = re.compile(r"--(user|password)=[^', ]+([', ])")
    clean = call_proc_db_creds.sub(r"--\1=*****\2", dirty)

    return clean


def _scrub_event(event_data: Any):
    """
    Recursively traverses sentry event data returns a scrubbed version.
    Parameters
    ----------
    event_data : Any
        Input that may contain sensitive information.
    Returns
    -------
    Any
        Output with any known sensitive information masked out.
    """
    # Basically cribbed from stackoverflow:
    # https://stackoverflow.com/a/38970181
    if isinstance(event_data, dict):
        items = event_data.items()
    elif isinstance(event_data, (list, tuple)):
        items = enumerate(event_data)
    else:
        return _mask_pattern(str(event_data))

    for key, value in items:
        # When we can id sensitive data by the key, do a simple replacement.
        if key == "user" or key == "password" or key == "passwd":
            event_data[key] = "*****"
        # Otherwise, continue recursion.
        else:
            event_data[key] = _scrub_event(value)

    return event_data
