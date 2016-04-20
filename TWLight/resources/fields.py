"""
Copy-paste of the following Django 1.8 code:
    django.db.models.DurationField
    django.forms.fields.DurationField
    django.utils.duration.duration_string
    django.utils.dateparse.parse_duration, standard_duration_re, iso8601_duration_re

We need to store durations for our access grant terms, but DurationField didn't
exist until Django 1.8, and this project is 1.7. May as well use the
Django-tested way of doing things. This file can be removed if this project is
upgraded to Django 1.8+, with a corresponding import statement added to
models.py.
"""

import datetime
import re
import six

from django.core import exceptions
from django.db.models import Field
from django.forms.fields import Field as FormField
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _


standard_duration_re = re.compile(
    r'^'
    r'(?:(?P<days>-?\d+) (days?, )?)?'
    r'((?:(?P<hours>\d+):)(?=\d+:\d+))?'
    r'(?:(?P<minutes>\d+):)?'
    r'(?P<seconds>\d+)'
    r'(?:\.(?P<microseconds>\d{1,6})\d{0,6})?'
    r'$'
)


iso8601_duration_re = re.compile(
    r'^P'
    r'(?:(?P<days>\d+(.\d+)?)D)?'
    r'(?:T'
    r'(?:(?P<hours>\d+(.\d+)?)H)?'
    r'(?:(?P<minutes>\d+(.\d+)?)M)?'
    r'(?:(?P<seconds>\d+(.\d+)?)S)?'
    r')?'
    r'$'
)


def duration_string(duration):
    days = duration.days
    seconds = duration.seconds
    microseconds = duration.microseconds

    minutes = seconds // 60
    seconds = seconds % 60

    hours = minutes // 60
    minutes = minutes % 60

    string = '{:02d}:{:02d}:{:02d}'.format(hours, minutes, seconds)
    if days:
        string = '{} '.format(days) + string
    if microseconds:
        string += '.{:06d}'.format(microseconds)

    return string


def parse_duration(value):
    """Parses a duration string and returns a datetime.timedelta.
    The preferred format for durations in Django is '%d %H:%M:%S.%f'.
    Also supports ISO 8601 representation.
    """
    match = standard_duration_re.match(value)
    if not match:
        match = iso8601_duration_re.match(value)
    if match:
        kw = match.groupdict()
        if kw.get('microseconds'):
            kw['microseconds'] = kw['microseconds'].ljust(6, '0')
        kw = {k: float(v) for k, v in six.iteritems(kw) if v is not None}
        return datetime.timedelta(**kw)


class DurationField(Field):
    """Stores timedelta objects.
    Uses interval on postgres, INVERAL DAY TO SECOND on Oracle, and bigint of
    microseconds on other databases.
    """
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value has an invalid format. It must be in "
                     "[DD] [HH:[MM:]]ss[.uuuuuu] format.")
    }
    description = _("Duration")

    def get_internal_type(self):
        return "DurationField"

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, datetime.timedelta):
            return value
        try:
            parsed = parse_duration(value)
        except ValueError:
            pass
        else:
            if parsed is not None:
                return parsed

        raise exceptions.ValidationError(
            self.error_messages['invalid'],
            code='invalid',
            params={'value': value},
        )

    def get_db_prep_value(self, value, connection, prepared=False):
        if connection.features.has_native_duration_field:
            return value
        if value is None:
            return None
        # Discard any fractional microseconds due to floating point arithmetic.
        return int(round(value.total_seconds() * 1000000))

    def get_db_converters(self, connection):
        converters = []
        if not connection.features.has_native_duration_field:
            converters.append(connection.ops.convert_durationfield_value)
        return converters + super(DurationField, self).get_db_converters(connection)

    def value_to_string(self, obj):
        val = self.value_from_object(obj)
        return '' if val is None else duration_string(val)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': FormDurationField,
        }
        defaults.update(kwargs)
        return super(DurationField, self).formfield(**defaults)



class FormDurationField(FormField):
    default_error_messages = {
        'invalid': _('Enter a valid duration.'),
    }

    def prepare_value(self, value):
        if isinstance(value, datetime.timedelta):
            return duration_string(value)
        return value

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, datetime.timedelta):
            return value
        value = parse_duration(force_text(value))
        if value is None:
            raise exceptions.ValidationError(self.error_messages['invalid'], code='invalid')
        return value
