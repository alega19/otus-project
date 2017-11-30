from os.path import join

from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import connection
from django.test import TestCase

from ..models import Community


User = get_user_model()


class TestCommunity(TestCase):

    COMMUNITIES_NUM = 200

    def setUp(self):
        super().setUp()

        communities_ids = range(self.COMMUNITIES_NUM)

        with open(join(settings.BASE_DIR, '..', 'schema.sql'), encoding='utf-8') as fd:
            sql = fd.read()
        connection.cursor().execute(sql)

        sql = r'INSERT INTO "community" ("vkid","deactivated","type","name","description","status","site","members") VALUES'
        sql += ','.join(
            "({0:d},FALSE,1,'NAME_{0:d}','DESCRIPTION_{0:d}','STATUS_{0:d}','SITE_{0:d}',{1:d})".format(cid, cid*1000+1)
            for cid in communities_ids
        )
        sql += ';'
        connection.cursor().execute(sql)

        sql = (r'INSERT INTO "profile" ("id","sex_vkid","age_range_id","country_vkid","app_id") '
               r'VALUES (1,1,1,1,1)')
        connection.cursor().execute(sql)

        sql = r'INSERT INTO "audience" ("profile_id","community_vkid","count") VALUES'
        sql += ','.join("(1,{0:d},{1:d})".format(cid, cid*1000+1) for cid in communities_ids)
        sql += ';'
        connection.cursor().execute(sql)

    def test_select(self):
        communities = Community.objects.select('members', True)[:]
        self.assertEqual(len(communities), self.COMMUNITIES_NUM)
        self.assertEqual(communities[0].vkid, self.COMMUNITIES_NUM - 1)

        communities = Community.objects.select('audience_sum', True, sex_ids=[1], age_ranges=[1], countries=[1], apps=[1])[:]
        self.assertEqual(len(communities), self.COMMUNITIES_NUM)
        self.assertEqual(communities[0].vkid, self.COMMUNITIES_NUM - 1)
