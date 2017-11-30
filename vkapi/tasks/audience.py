import logging
import math
from collections import namedtuple
from datetime import datetime as DateTime, timedelta as TimeDelta, timezone
from queue import deque

from vkapi import errors
from vkapi.db import Database
from vkapi.tasks.basetask import BaseTask


STEP = 20000


Profile = namedtuple('Profile', ['sex_vkid', 'age_range_id', 'country_vkid', 'app_id'])


class AudienceOfCommunity:

    UNKNOWN_COUNTRY = None
    countries_ids = None

    AGE_UNKNOWN = None
    AGE_14_AND_YOUNGER = None
    AGE_15_17 = None
    AGE_18_21 = None
    AGE_22_25 = None
    AGE_26_29 = None
    AGE_30_34 = None
    AGE_35_39 = None
    AGE_40_44 = None
    AGE_45_49 = None
    AGE_50_59 = None
    AGE_60_AND_OLDER = None

    APP_UNKNOWN = None
    APP_IOS = None
    APP_ANDROID = None
    APP_MOBILE = None
    APP_BROWSER = None

    _profile2id = None

    @classmethod
    def _init_countries_ids(cls):
        sql = ('SELECT "vkid", "name" '
               'FROM "country"')
        kvpairs = Database().execute(sql, handler=lambda row: (row[1], row[0]))
        name2id = dict(kvpairs)
        cls.UNKNOWN_COUNTRY = name2id.pop('UNKNOWN')
        cls.countries_ids = frozenset(name2id.values())

    @classmethod
    def _init_age_ranges(cls):
        sql = ('SELECT "id", "name" '
               'FROM "age_range"')
        kvpairs = Database().execute(sql, handler=lambda row: (row[1], row[0]))
        name2id = dict(kvpairs)
        cls.AGE_UNKNOWN = name2id['UNKNOWN']
        cls.AGE_14_AND_YOUNGER = name2id['-14']
        cls.AGE_15_17 = name2id['15-17']
        cls.AGE_18_21 = name2id['18-21']
        cls.AGE_22_25 = name2id['22-25']
        cls.AGE_26_29 = name2id['26-29']
        cls.AGE_30_34 = name2id['30-34']
        cls.AGE_35_39 = name2id['35-39']
        cls.AGE_40_44 = name2id['40-44']
        cls.AGE_45_49 = name2id['45-49']
        cls.AGE_50_59 = name2id['50-59']
        cls.AGE_60_AND_OLDER = name2id['60+']

    @classmethod
    def _init_applications(cls):
        sql = ('SELECT "id", "name" '
               'FROM "application"')
        kvpairs = Database().execute(sql, handler=lambda row: (row[1], row[0]))
        name2id = dict(kvpairs)
        cls.APP_UNKNOWN = name2id['UNKNOWN']
        cls.APP_IOS = name2id['IOS']
        cls.APP_ANDROID = name2id['ANDROID']
        cls.APP_MOBILE = name2id['MOBILE']
        cls.APP_BROWSER = name2id['BROWSER']

    @classmethod
    def _load_profiles(cls):
        sql = ('SELECT "id", "sex_vkid", "age_range_id", "country_vkid", "app_id" '
               'FROM "profile"')
        kvpairs = Database().execute(sql, handler=lambda row: (Profile(row[1], row[2], row[3], row[4]), row[0]))
        cls._profile2id = dict(kvpairs)

    @classmethod
    def load_ordered_by_update_time(cls, min_members):
        sql = ('SELECT "vkid", "members" '
               'FROM "community" '
               'WHERE "deactivated" = FALSE '
               'AND "members" >= {0:d} '
               'ORDER BY "audience_updated" ASC').format(min_members)
        return Database().execute(sql, handler=lambda row: cls(row[0], row[1]))

    def __init__(self, comm_vkid, members):
        if self.UNKNOWN_COUNTRY is None:
            self._init_countries_ids()
            self._init_applications()
            self._init_age_ranges()
            self._load_profiles()
        self.vkid = comm_vkid
        self.members = members
        self.offset = 0
        self.profile2count = {}
        self.unfinished_tasks = math.ceil(members / STEP)

    @Database.retry
    def save(self):
        if not self.profile2count:
            return

        with Database() as db:
            audience_params_list = []
            sql = ('INSERT INTO "profile" ("sex_vkid", "age_range_id", "country_vkid", "app_id") '
                   'VALUES (%s, %s, %s, %s) '
                   'RETURNING "id"')
            for profile, count in self.profile2count.items():
                profile_id = self._profile2id.get(profile)
                if profile_id is None:
                    params = profile.sex_vkid, profile.age_range_id, profile.country_vkid, profile.app_id
                    profile_id = db.execute(sql, params, lambda row: row[0])[0]
                    self._profile2id[profile] = profile_id
                audience_params_list.append((self.vkid, profile_id, count))

            sql = ('DELETE FROM "audience" '
                   'WHERE "community_vkid" = %s')
            db.execute(sql, (self.vkid,))
            sql = ('INSERT INTO "audience" ("community_vkid", "profile_id", "count") '
                   'VALUES (%s, %s, %s)')
            db.executemany(sql, audience_params_list)
        logging.info('audience of community %s was saved' % self.vkid)


class TaskToUpdateAudience(BaseTask):

    _audiences = deque()

    _URL_PATTERN = (
        'https://api.vk.com/method/execute?code={code}&v=5.67&access_token={token}'
    )
    _CODE_LINE = ('API.groups.getMembers({"group_id":%d,"offset":%d,"count":1000,"sort":"id_asc",'
                  '"fields":"sex,bdate,country,last_seen"})')

    @classmethod
    def deadline(cls):
        return DateTime.now(timezone.utc) + TimeDelta(seconds=10)

    @classmethod
    def _load_audiences(cls):
        audiences = AudienceOfCommunity.load_ordered_by_update_time(50000)
        logging.info('Loaded %s communities' % len(audiences))
        cls._audiences.extend(audiences)

    def __init__(self):
        super().__init__()
        self.blank = False
        self.aud = None
        self.offset = None
        self.response = None
        if not self._audiences:
            self._load_audiences()
        self.aud = self._audiences[0]
        if self.aud.offset >= self.aud.members:
            self.blank = True
        else:
            self.offset = self.aud.offset
            self.aud.offset += STEP

    async def handle(self, session, token):
        if self.blank:
            return
        url = self._url(token)
        async with session.get(url) as resp:
            resp.raise_for_status()
            self.response = await resp.json()
        self._handle_response()
        logging.debug('TaskToUpdateAudience(%s) done, %s tasks left' % (self.aud.vkid, self.aud.unfinished_tasks))

    def _url(self, token):
        code = 'return ['
        code += ','.join(
            (self._CODE_LINE % (self.aud.vkid, offset))
            for offset in range(self.offset, self.offset+STEP, 1000)
        )
        code += '];'
        return self._URL_PATTERN.format(code=code, token=token)

    def _handle_response(self):
        parts = self.response.get('response')
        if parts:
            for part in parts:
                if part:
                    self._update_audience(part['items'])
            self.aud.unfinished_tasks -= 1
            if self.aud.unfinished_tasks == 0:
                self.aud.save()
                self._audiences.popleft()
        else:
            self._handle_error()

    def _update_audience(self, users):
        for user in users:
            try:
                sex_vkid = self._parse_sex(user)
                age_range_id = self._parse_bdate(user)
                country_vkid = self._parse_country(user)
                app_id = self._parse_last_platform(user)
                profile = Profile(sex_vkid, age_range_id, country_vkid, app_id)
                self.aud.profile2count[profile] = self.aud.profile2count.get(profile, 0) + 1
            except errors.VKAPIParsingError as err:
                logging.error(err)

    @staticmethod
    def _parse_sex(user):
        sex_id = user.get('sex')
        if sex_id not in (0, 1, 2):
            raise errors.VKAPIParsingError('unexpected value of "sex": %s' % sex_id)
        return sex_id

    @staticmethod
    def _parse_bdate(user):
        bdate = user.get('bdate')
        if bdate is None:
            return AudienceOfCommunity.AGE_UNKNOWN
        parts = bdate.split('.')
        if len(parts) < 3:
            return AudienceOfCommunity.AGE_UNKNOWN
        try:
            bdate = DateTime(int(parts[2]), int(parts[1]), int(parts[0]))
        except ValueError:
            return AudienceOfCommunity.AGE_UNKNOWN
        now = DateTime.utcnow()
        if bdate > now:
            return AudienceOfCommunity.AGE_UNKNOWN
        age = (now - bdate).days / 365.25
        if age < 15:
            return AudienceOfCommunity.AGE_14_AND_YOUNGER
        if age < 18:
            return AudienceOfCommunity.AGE_15_17
        if age < 22:
            return AudienceOfCommunity.AGE_18_21
        if age < 26:
            return AudienceOfCommunity.AGE_22_25
        if age < 30:
            return AudienceOfCommunity.AGE_26_29
        if age < 35:
            return AudienceOfCommunity.AGE_30_34
        if age < 40:
            return AudienceOfCommunity.AGE_35_39
        if age < 45:
            return AudienceOfCommunity.AGE_40_44
        if age < 50:
            return AudienceOfCommunity.AGE_45_49
        if age < 60:
            return AudienceOfCommunity.AGE_50_59
        return AudienceOfCommunity.AGE_60_AND_OLDER

    @staticmethod
    def _parse_country(user):
        country = user.get('country')
        if country is None:
            return AudienceOfCommunity.UNKNOWN_COUNTRY
        country_id = country['id']
        if country_id in AudienceOfCommunity.countries_ids:
            return country_id
        else:
            return AudienceOfCommunity.UNKNOWN_COUNTRY

    @staticmethod
    def _parse_last_platform(user):
        last_seen = user.get('last_seen')
        if last_seen is None:
            return AudienceOfCommunity.APP_UNKNOWN
        platform_id = last_seen.get('platform')
        if platform_id is None or platform_id == 6:
            return AudienceOfCommunity.APP_UNKNOWN
        if platform_id in (2, 3):
            return AudienceOfCommunity.APP_IOS
        if platform_id == 4:
            return AudienceOfCommunity.APP_ANDROID
        if platform_id in (1, 5, 8):
            return AudienceOfCommunity.APP_MOBILE
        if platform_id == 7:
            return AudienceOfCommunity.APP_BROWSER
        raise errors.VKAPIParsingError('unknown platform_id: %s' % platform_id)

    def _handle_error(self):
        errmsg = 'Unknown VKAPI error'
        err = self.response.get('error')
        if err:
            errmsg = err.get('error_msg', errmsg)
        raise errors.VKAPIResponseError(errmsg)

    def cancel(self):
        self.aud.unfinished_tasks -= 1
        logging.debug('TaskToUpdateAudience(id%s) was cancelled, %s tasks left' % (self.aud.vkid, self.aud.unfinished_tasks))
        if self.aud.unfinished_tasks == 0:
            self.aud.save()
            self._audiences.popleft()
