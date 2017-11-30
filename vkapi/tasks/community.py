import logging
import math
from datetime import datetime as DateTime, timedelta as TimeDelta, timezone
from queue import deque

from vkapi import errors
from vkapi.db import Database
from vkapi.tasks.basetask import BaseTask


class Community:

    PUBLIC_PAGE = None
    OPEN_GROUP = None
    CLOSED_GROUP = None
    PRIVATE_GROUP = None

    @classmethod
    def _init_types(cls):
        sql = ('SELECT "id", "name" '
               'FROM "community_type"')
        kvpairs = Database().execute(sql, handler=lambda row: (row[1], row[0]))
        name2id = dict(kvpairs)
        cls.PUBLIC_PAGE = name2id['PUBLIC_PAGE']
        cls.OPEN_GROUP = name2id['OPEN_GROUP']
        cls.CLOSED_GROUP = name2id['CLOSED_GROUP']
        cls.PRIVATE_GROUP = name2id['PRIVATE_GROUP']

    @classmethod
    def load_ordered_by_update_time(cls):
        sql = ('SELECT "vkid" '
               'FROM "community" '
               'ORDER BY "updated" ASC')
        return Database().execute(sql, handler=lambda row: cls(row[0]))

    def __init__(self, vkid):
        if self.PUBLIC_PAGE is None:
            self._init_types()
        self.vkid = vkid
        self.deactivated = None
        self.type = None
        self.name = None
        self.description = None
        self.members = None
        self.status = None
        self.verified = None
        self.site = None
        self.age_limit = None

    @classmethod
    def create(cls, vkid, deactivated, type_, name, description, members, status, verified, site, age_limit):
        comm = cls(vkid)
        comm.deactivated = deactivated
        comm.type = type_
        comm.name = name
        comm.description = description
        comm.members = members
        comm.status = status
        comm.verified = verified
        comm.site = site
        comm.age_limit = age_limit

        sql = ('INSERT INTO "community" '
               '("vkid", "deactivated", "type", "name", "description", '
               '"members", "status", "verified", "site", "age_limit") '
               'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)')
        params = (comm.vkid, comm.deactivated, comm.type, comm.name, comm.description,
                  comm.members, comm.status, comm.verified, comm.site, comm.age_limit)
        Database().execute(sql, params)

        return comm

    def save(self):
        sql = ('UPDATE "community" '
               'SET "deactivated"=%s, "type"=%s, "name"=%s, "description"=%s, '
               '"members"=%s, "status"=%s, "verified"=%s, "site"=%s, "age_limit"=%s '
               'WHERE "vkid"=%s')
        params = (self.deactivated, self.type, self.name, self.description,
                  self.members, self.status, self.verified, self.site, self.age_limit,
                  self.vkid)
        Database().execute(sql, params)
        logging.info('community(id%s) was saved' % self.vkid)


class TaskToUpdateCommunities(BaseTask):

    _COMMUNITIES_PER_TASK = 350
    _TIME_FOR_FULL_UPDATE = TimeDelta(days=1)

    _URL_PATTERN = (
        'https://api.vk.com/method/groups.getById?group_ids={ids}&'
        'fields=type,is_closed,name,description,members_count,status,verified,site,age_limits&'
        'v=5.67&access_token={token}')

    _communities = deque()
    _main_deadline = None
    _max_time_per_task = None

    @classmethod
    def deadline(cls):
        if not cls._communities:
            cls._load_communities()
        ntasks = math.ceil(len(cls._communities) / cls._COMMUNITIES_PER_TASK)
        deadline = cls._main_deadline - cls._max_time_per_task * ntasks
        return deadline

    @classmethod
    def _load_communities(cls):
        communities = Community.load_ordered_by_update_time()
        cls._communities.extend(communities)
        cls._update_main_deadline()

    @classmethod
    def _update_main_deadline(cls):
        now = DateTime.now(timezone.utc)
        if cls._main_deadline is not None and now > cls._main_deadline:
            delay = now - cls._main_deadline
            logging.warning('TaskToUpdateCommunities missed the deadline by {0}'.format(delay))
        cls._main_deadline = now + cls._TIME_FOR_FULL_UPDATE
        ntasks = math.ceil(len(cls._communities) / cls._COMMUNITIES_PER_TASK)
        cls._max_time_per_task = cls._TIME_FOR_FULL_UPDATE / ntasks

    def __init__(self):
        super().__init__()
        if not self._communities:
            self._load_communities()
        self.id2community = {}
        self.response = None
        self._get_communities()

    def _get_communities(self):
        num = min(self._COMMUNITIES_PER_TASK, len(self._communities))
        for _ in range(num):
            comm = self._communities.popleft()
            self.id2community[comm.vkid] = comm

    async def handle(self, session, token):
        url = self._url(token)
        async with session.get(url) as resp:
            resp.raise_for_status()
            self.response = await resp.json()
        self._handle_response()

    def _url(self, token):
        ids_param = ','.join(str(vkid) for vkid in self.id2community.keys())
        return self._URL_PATTERN.format(ids=ids_param, token=token)

    def _handle_response(self):
        data_list = self.response.get('response')
        if data_list:
            id2data = {d['id']: d for d in data_list}
            for vkid, comm in self.id2community.items():
                data = id2data[vkid]
                self._update_community(comm, data)
        else:
            self._handle_error()

    def _update_community(self, comm, data):
        try:
            comm.deactivated = self._parse_deactivated(data)
            comm.type = self._parse_type(data)
            comm.name = data['name']
            comm.description = data.get('description', '')
            comm.members = data.get('members_count')
            comm.status = data.get('status', '')
            comm.verified = self._parse_verified(data)
            comm.site = data.get('site', '')
            comm.age_limit = self._parse_age_limit(data)
            comm.save()
        except errors.VKAPIParsingError as err:
            logging.error(err)

    @staticmethod
    def _parse_deactivated(data):
        # TODO: ??? state (active,banned,deleted,judgment)
        if data.get('deactivated'):
            return True
        if data['is_closed'] != 2 and 'members_count' not in data:
            # Court decision
            return True
        return False

    @staticmethod
    def _parse_type(data):
        vktype, closed = data['type'], data['is_closed']
        if vktype == 'page':
            type_ = Community.PUBLIC_PAGE
        elif vktype == 'group':
            if closed == 0:
                type_ = Community.OPEN_GROUP
            elif closed == 1:
                type_ = Community.CLOSED_GROUP
            elif closed == 2:
                type_ = Community.PRIVATE_GROUP
            else:
                raise errors.VKAPIParsingError('Unknown "is_closed"=%s' % closed)
        else:
            raise errors.VKAPIParsingError('Unknown "type"=%s' % vktype)
        return type_

    @staticmethod
    def _parse_verified(data):
        code = data.get('verified')
        if code is None:
            return None
        else:
            return code == 1

    @staticmethod
    def _parse_age_limit(data):
        code = data.get('age_limits')
        if code == 1:
            limit = 0
        elif code == 2:
            limit = 16
        elif code == 3:
            limit = 18
        elif code is None:
            limit = None
        else:
            raise errors.VKAPIParsingError('Unknown "age_limits"=%s' % code)
        return limit

    def _handle_error(self):
        errmsg = 'Unknown VKAPI error'
        err = self.response.get('error')
        if err:
            errmsg = err.get('error_msg', errmsg)
        raise errors.VKAPIResponseError(errmsg)

    def cancel(self):
        logging.debug('TaskToUpdateCommunities was cancelled')
