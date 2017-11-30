from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model

from ..forms import RegistrationModelForm, SettingsModelForm


User = get_user_model()


class TestRegistrationModelForm(TestCase):

    def test_correct_data(self):
        data = {'email': 'bob@mail.ru',
                'password': '186r128f7c222c',
                'password2': '186r128f7c222c'}
        form = RegistrationModelForm(data)
        self.assertTrue(form.is_valid())

    def test_too_simple_password(self):
        data = {'email': 'bob@mail.ru',
                'password': '72164971649',
                'password2': '72164971649'}
        form = RegistrationModelForm(data)
        self.assertFalse(form.is_valid())

        data = {'email': 'bob@mail.ru',
                'password': 'gesgsegegwykf',
                'password2': 'gesgsegegwykf'}
        form = RegistrationModelForm(data)
        self.assertFalse(form.is_valid())

    def test_different_passwords(self):
        data = {'email': 'bob@mail.ru',
                'password': '186r128f7c222c',
                'password2': 'Z186r128f7c222c'}
        form = RegistrationModelForm(data)
        self.assertFalse(form.is_valid())

    def test_existing_email(self):
        User.objects.create(email='bob@mail.ru', password='123')
        data = {'email': 'bob@mail.ru',
                'password': '186r128f7c222c',
                'password2': '186r128f7c222c'}
        form = RegistrationModelForm(data)
        self.assertFalse(form.is_valid())


class TestSettingsModelForm(TestCase):

    def test_correct_data(self):
        passwd = r'186r128f7c222c'
        new_passwd = r'hb8h938hb0q2h'
        bob = User(email='bob@mail.ru')
        bob.set_password(passwd)
        bob.save()
        data = {'email': 'superstar@mail.ru',
                'current_password': passwd,
                'password': new_passwd,
                'password2': new_passwd}
        form = SettingsModelForm(instance=bob, data=data)
        self.assertTrue(form.is_valid())

    def test_existing_email(self):
        bob = User.objects.create(email='bob@mail.ru', password='123')
        alice = User.objects.create(email='alice@mail.ru', password='123')
        data = {'email': bob.email}
        form = SettingsModelForm(instance=alice, data=data)
        self.assertFalse(form.is_valid())
