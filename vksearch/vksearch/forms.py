from django import forms

from .models import Community, Profile, AgeRange, Country, Application


class CommunitiesFilterForm(forms.Form):
    min_members = forms.IntegerField(required=False, min_value=0)
    max_members = forms.IntegerField(required=False, min_value=0)

    min_audience = forms.IntegerField(required=False, min_value=0)
    max_audience = forms.IntegerField(required=False, min_value=0)

    min_audience_perc = forms.IntegerField(required=False, min_value=0, max_value=100, label='Min audience %')
    max_audience_perc = forms.IntegerField(required=False, min_value=0, max_value=100, label='Max audience %')

    sex = forms.MultipleChoiceField(Profile.SEX_CHOICES, required=False, widget=forms.CheckboxSelectMultiple())
    age_ranges = forms.ModelMultipleChoiceField(AgeRange.objects.all(), required=False, widget=forms.CheckboxSelectMultiple())
    countries = forms.ModelMultipleChoiceField(Country.objects.all(), required=False, widget=forms.CheckboxSelectMultiple())
    apps = forms.ModelMultipleChoiceField(Application.objects.all(), required=False, widget=forms.CheckboxSelectMultiple())

    ordering = forms.ChoiceField(Community.objects.ORDERING_CHOICES)
    inverted = forms.BooleanField(required=False)

    def clean_age_ranges(self):
        return tuple(self.cleaned_data['age_ranges'])

    def clean_countries(self):
        return tuple(self.cleaned_data['countries'])

    def clean_apps(self):
        return tuple(self.cleaned_data['apps'])

    def clean(self):
        super().clean()
        self._check_range('min_members', 'max_members')
        self._check_range('min_audience', 'max_audience')
        self._check_range('min_audience_perc', 'max_audience_perc')
        return self.cleaned_data

    def _check_range(self, min_field_name, max_field_name):
        min_value = self.cleaned_data.get(min_field_name)
        max_value = self.cleaned_data.get(max_field_name)
        if min_value is not None and max_value is not None:
            if min_value > max_value:
                raise forms.ValidationError('"{0}" must not be more than "{1}"'.format(
                    min_field_name, max_field_name))
