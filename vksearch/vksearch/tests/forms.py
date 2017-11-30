from os.path import join

from django.test import TestCase
from django.conf import settings
from django.db import connection
from django.contrib.auth import get_user_model

from ..forms import CommunitiesFilterForm


User = get_user_model()


class TestCommunitiesFilterForm(TestCase):

    COMMUNITIES_NUM = 200

    def setUp(self):
        super().setUp()

        communities_ids = range(self.COMMUNITIES_NUM)

        with open(join(settings.BASE_DIR, '..', 'schema.sql'), encoding='utf-8') as fd:
            sql = fd.read()
        connection.cursor().execute(sql)

        sql = r'INSERT INTO "community" ("vkid","deactivated","type","name","description","status","site","members") VALUES'
        sql += ','.join(
            "({0:d},FALSE,1,'NAME_{0:d}','DESCRIPTION_{0:d}','STATUS_{0:d}','SITE_{0:d}',{1:d})".format(cid,
                                                                                                        cid * 1000 + 1)
            for cid in communities_ids
        )
        sql += ';'
        connection.cursor().execute(sql)

        sql = (r'INSERT INTO "profile" ("id","sex_vkid","age_range_id","country_vkid","app_id") '
               r'VALUES (1,1,1,1,1)')
        connection.cursor().execute(sql)

        sql = r'INSERT INTO "audience" ("profile_id","community_vkid","count") VALUES'
        sql += ','.join("(1,{0:d},{1:d})".format(cid, cid * 1000 + 1) for cid in communities_ids)
        sql += ';'
        connection.cursor().execute(sql)

    def test_correct_data(self):
        data = {
            'min_members': 0,
            'max_members': 1000000,

            'min_audience': 0,
            'max_audience': 1000000,

            'min_audience_perc': 0,
            'max_audience_perc': 100,

            'sex': [1],
            'age_ranges': [1],
            'countries': [1],
            'apps': [1],

            'ordering': 'audience_perc',
            'inverted': True
        }
        form = CommunitiesFilterForm(data)
        self.assertTrue(form.is_valid())

    def test_constrains(self):
        data = {
            'min_members': -1,
            'max_members': 10,

            'ordering': 'audience_perc',
            'inverted': True
        }
        form = CommunitiesFilterForm(data)
        self.assertFalse(form.is_valid())

        data = {
            'min_audience': -1,
            'max_audience': 10,

            'ordering': 'audience_perc',
            'inverted': True
        }
        form = CommunitiesFilterForm(data)
        self.assertFalse(form.is_valid())

        data = {
            'min_audience_perc': -1,
            'max_audience_perc': 10,

            'ordering': 'audience_perc',
            'inverted': True
        }
        form = CommunitiesFilterForm(data)
        self.assertFalse(form.is_valid())

        data = {
            'min_audience_perc': 0,
            'max_audience_perc': 101,

            'ordering': 'audience_perc',
            'inverted': True
        }
        form = CommunitiesFilterForm(data)
        self.assertFalse(form.is_valid())

    def test_ranges(self):
        data = {
            'min_members': 10,
            'max_members': 9,

            'ordering': 'audience_perc',
            'inverted': True
        }
        form = CommunitiesFilterForm(data)
        self.assertFalse(form.is_valid())

        data = {
            'min_audience': 10,
            'max_audience': 9,

            'ordering': 'audience_perc',
            'inverted': True
        }
        form = CommunitiesFilterForm(data)
        self.assertFalse(form.is_valid())

        data = {
            'min_audience_perc': 10,
            'max_audience_perc': 9,

            'ordering': 'audience_perc',
            'inverted': True
        }
        form = CommunitiesFilterForm(data)
        self.assertFalse(form.is_valid())
