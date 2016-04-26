# -*- coding: utf-8 -*-
from django.utils import formats, six
from django.forms.widgets import TextInput
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text
from datetime import timedelta

# This is an attempt to resolve a RemovedInDjango19Warning raised when
#  using version 0.5.1 on Django 1.8
try:
    from django.forms.utils import flatatt
except ImportError:
    from django.forms.util import flatatt


class DurationInput(TextInput):
    def render(self, name, value, attrs=None):
        """
        output.append(u'<li>%(cb)s<label%(for)s>%(label)s</label></li>' % {"for": label_for, "label": option_label, "cb": rendered_cb})
        """
        if value is None:
            value = ''

        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            if isinstance(value, six.integer_types):
                value = timedelta(microseconds=value)

            # Otherwise, we've got a timedelta already

            final_attrs['value'] = force_text(formats.localize_input(value))
        return mark_safe('<input%s />' % flatatt(final_attrs))
