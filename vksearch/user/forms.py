import re

from django import forms
from django.contrib import auth


User = auth.get_user_model()


class AbstractUserModelForm(forms.ModelForm):
    password = forms.CharField(min_length=8, max_length=32, widget=forms.PasswordInput(), label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput(), label='Repeat the password')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(u'A user with that email already exists')
        return email

    def clean_password(self):
        password = self.cleaned_data['password']
        has_letter = bool(re.search('[A-Za-z]', password))
        has_digit = bool(re.search('\d', password))
        has_special = bool(re.search("[#$%'^,()*+.:|=?@/\[\]_`{}!;\-~]", password))
        if has_letter + has_digit + has_special < 2:
            raise forms.ValidationError(u"Password must include at least two of the following elements: "
                                        u"a letter, a digit, a special character (#$%'^,()*+.:|=?@/[]_`{}!;-~)")
        return password

    def clean(self):
        super().clean()
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password:
            if password != password2:
                raise forms.ValidationError(u'Passwords do not match')

    def save(self, commit=True):
        raw_password = self.cleaned_data.get('password')
        self.instance.set_password(raw_password)
        super().save(commit)

    class Meta:
        model = User
        fields = ('email', 'password')


class RegistrationModelForm(AbstractUserModelForm):
    pass


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())

    def __init__(self, req=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._req = req
        self.user = None

    def clean(self):
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']
        self.user = auth.authenticate(self._req, email=email, password=password)
        if not self.user:
            raise forms.ValidationError(u'Incorrect email/password')


class SettingsModelForm(AbstractUserModelForm):
    current_password = forms.CharField(widget=forms.PasswordInput(), label='Current password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_email(self):
        user = self.instance
        email = self.cleaned_data['email']
        if email != user.email:
            email = super().clean_email()
        return email

    def clean(self):
        super().clean()
        user = self.instance
        current_password = self.cleaned_data.get('current_password')
        if not user.check_password(current_password):
            print('Incorrect password:', current_password)
            raise forms.ValidationError('Incorrect password')
