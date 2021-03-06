from django import forms

from tower import ugettext_lazy as _lazy

import amo
from mkt.constants import (CATEGORY_CHOICES, TARAKO_CATEGORY_CHOICES,
                           TARAKO_CATEGORIES_MAPPING)
from mkt.constants.applications import DEVICE_LOOKUP


SORT_CHOICES = [
    (None, _lazy(u'Relevance')),
    ('popularity', _lazy(u'Popularity')),
    ('downloads', _lazy(u'Weekly Downloads')),
    ('rating', _lazy(u'Top Rated')),
    ('price', _lazy(u'Price')),
    ('created', _lazy(u'Newest')),
    ('reviewed', _lazy(u'Reviewed')),
    ('name', _lazy(u'Name')),
]

FREE_SORT_CHOICES = [(k, v) for k, v in SORT_CHOICES if k != 'price']

APP_TYPE_CHOICES = [
    ('', _lazy(u'Any App Type')),
    ('hosted', _lazy(u'Hosted')),
    ('packaged', _lazy(u'Packaged')),
    ('privileged', _lazy(u'Privileged packaged app')),
]

PREMIUM_CHOICES = [
    ('free', _lazy(u'Free')),
    ('free-inapp', _lazy(u'Free with In-app')),
    ('premium', _lazy(u'Premium')),
    ('premium-inapp', _lazy(u'Premium with In-app')),
    ('other', _lazy(u'Other System for In-App')),
]

# Device choice.
DEV_CHOICES = [
    ('', _lazy(u'Any Device')),
    ('desktop', _lazy(u'Desktop')),
    ('android', _lazy(u'Android')),
    ('firefoxos', _lazy(u'Firefox OS')),
]

# Device type choice, only enabled for Android for the moment, see clean()
# implementation below.
DEVICE_CHOICES = [
    ('', _lazy(u'Any Device Type')),
    ('firefoxos', _lazy(u'Firefox OS')),  # Unused, for backwards-compat.
    ('mobile', _lazy(u'Mobile')),
    ('tablet', _lazy(u'Tablet')),
]

CATEGORY_CHOICES = (('', _lazy(u'All Categories')),) + CATEGORY_CHOICES

# Tags are only available to admins. They are free-form, and we expose them in
# the API, but they are not supposed to be manipulated by users atm, so we only
# allow to search for specific, whitelisted ones.
TAG_CHOICES = [
    ('tarako', 'tarako'),
]

# "Relevance" doesn't make sense for Category listing pages.
LISTING_SORT_CHOICES = SORT_CHOICES[1:]
FREE_LISTING_SORT_CHOICES = [(k, v) for k, v in LISTING_SORT_CHOICES
                             if k != 'price']


SEARCH_PLACEHOLDERS = {'apps': _lazy(u'Search for apps')}


class SimpleSearchForm(forms.Form):
    """Powers the search box on every page."""
    q = forms.CharField(required=False)
    cat = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_cat(self):
        return self.data.get('cat', 'all')

    def placeholder(self, txt=None):
        return txt or SEARCH_PLACEHOLDERS['apps']


class ApiSearchForm(forms.Form):
    q = forms.CharField(
        required=False, label=_lazy(u'Search'),
        widget=forms.TextInput(attrs={'autocomplete': 'off',
                                      'placeholder': _lazy(u'Search')}))
    cat = forms.ChoiceField(required=False, label=_lazy(u'Categories'),
                            choices=CATEGORY_CHOICES + TARAKO_CATEGORY_CHOICES)
    dev = forms.ChoiceField(
        required=False, choices=DEV_CHOICES, label=_lazy(u'Device'))
    device = forms.ChoiceField(
        required=False, choices=DEVICE_CHOICES, label=_lazy(u'Device type'))
    premium_types = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(), required=False,
        label=_lazy(u'Premium types'), choices=PREMIUM_CHOICES)
    # TODO: Make some fancy `MultipleCommaSeperatedChoiceField` field.
    app_type = forms.MultipleChoiceField(
        required=False, choices=APP_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple(), label=_lazy(u'App type'))
    manifest_url = forms.CharField(required=False, label=_lazy('Manifest URL'))
    offline = forms.NullBooleanField(required=False,
                                     label=_lazy('Works offline'))
    languages = forms.CharField(required=False,
                                label=_lazy('Supported languages'))
    author = forms.CharField(required=False, label=_lazy('Author name'))

    sort = forms.MultipleChoiceField(required=False,
                                     choices=LISTING_SORT_CHOICES)
    limit = forms.IntegerField(required=False, widget=forms.HiddenInput())
    tag = forms.ChoiceField(required=False, label=_lazy(u'Tags'),
                            choices=TAG_CHOICES)

    def __init__(self, *args, **kw):
        super(ApiSearchForm, self).__init__(*args, **kw)
        self.initial.update({
            'type': 'app',
            'status': 'pending',
        })

    def clean_cat(self):
        # If request category is a tarako one, get the corresponding list of
        # slugs, otherwise just build a list with the slug requested.
        if self.cleaned_data['cat']:
            return TARAKO_CATEGORIES_MAPPING.get(self.cleaned_data['cat'],
                                                 [self.cleaned_data['cat']])
        return None

    def clean_premium_types(self):
        """After cleaned, return a list of ints for the constants."""
        pt_ids = []
        for pt in self.cleaned_data.get('premium_types'):
            pt_id = amo.ADDON_PREMIUM_API_LOOKUP.get(pt)
            if pt_id is not None:
                pt_ids.append(pt_id)
        return pt_ids

    def clean_app_type(self):
        """After cleaned, return a list of ints for the constants."""
        at_ids = []
        for at in self.cleaned_data.get('app_type'):
            at_id = amo.ADDON_WEBAPP_TYPES_LOOKUP.get(at)
            if at_id is not None:
                at_ids.append(at_id)

        # Include privileged apps even when we search for packaged.
        if (amo.ADDON_WEBAPP_PACKAGED in at_ids and
            amo.ADDON_WEBAPP_PRIVILEGED not in at_ids):
            at_ids.append(amo.ADDON_WEBAPP_PRIVILEGED)

        return at_ids

    def clean_languages(self):
        languages = self.cleaned_data.get('languages')
        return [l.strip() for l in languages.split(',')] if languages else []

    def clean_device_and_dev(self):
        device = self.cleaned_data.get('dev')
        device_type = self.cleaned_data.get('device')
        # For android, we need to know the device type to determine the real
        # device we are going to filter with, because we distinguish between
        # mobile and tablets.
        if device == 'android' and device_type:
            device = '%s-%s' % (device, device_type)
        if device in DEVICE_LOOKUP:
            self.cleaned_data['device'] = DEVICE_LOOKUP.get(device).id
            self.cleaned_data.pop('dev', None)
        elif device:
            raise forms.ValidationError('Invalid device or device type.')

    def clean_author(self):
        return self.cleaned_data.get('author', '').lower()

    def clean(self):
        self.clean_device_and_dev()
        return self.cleaned_data
