"""
Copyright (c) 2012-2014 RockStor, Inc. <http://rockstor.com>
This file is part of RockStor.

RockStor is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published
by the Free Software Foundation; either version 2 of the License,
or (at your option) any later version.

RockStor is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import re
from django.utils.timezone import utc
from cli.rest_util import (api_call, set_token)
from storageadmin.exceptions import RockStorAPIException
from storageadmin.models import Appliance
import sys

BASE_URL = 'https://localhost/api/'

import logging


class ReplicationMixin(object):

    @classmethod
    def get_logger(cls):
        if (hasattr(cls, 'logger')):
            return cls.logger
        cls.logger = logging.getLogger()
        cls.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s', datefmt='%d/%b/%Y %H:%M:%S')
        ch.setFormatter(formatter)
        cls.logger.addHandler(ch)
        return cls.logger

    @staticmethod
    def validate_src_share(sender_uuid, sname):
        #do a simple get on the share of the sender.
        a = Appliance.objects.get(uuid=sender_uuid)
        url = ('https://%s:%s' % (a.ip, a.mgmt_port))
        set_token(client_id=a.client_id, client_secret=a.client_secret, url=url)
        api_call(url='%s/api/shares/%s' % (url, sname))

    @staticmethod
    def update_replica_status(rtid, data):
        try:
            url = ('%ssm/replicas/trail/%d' % (BASE_URL, rtid))
            return api_call(url, data=data, calltype='put')
        except Exception, e:
            msg = ('Exception while updating replica(%s) status to %s: %s' %
                   (url, data['status'], e.__str__()))
            raise Exception(msg)

    @staticmethod
    def disable_replica(rid):
        try:
            url = ('%ssm/replicas/%d' % (BASE_URL, rid))
            headers = {'content-type': 'application/json', }
            return api_call(url, data={'enabled': False, }, calltype='put',
                            save_error=False, headers=headers)
        except Exception, e:
            msg = ('Exception while disabling replica(%s): %s' %
                   (url, e.__str__()))
            raise Exception(msg)

    @staticmethod
    def create_replica_trail(rid, snap_name):
        url = ('%ssm/replicas/trail/replica/%d' % (BASE_URL, rid))
        return api_call(url, data={'snap_name': snap_name, },
                        calltype='post', save_error=False)

    @staticmethod
    def rshare_id(sname):
        url = ('%ssm/replicas/rshare/%s' % (BASE_URL, sname))
        rshare = api_call(url, save_error=False)
        return rshare['id']

    @classmethod
    def create_rshare(cls, data):
        try:
            url = ('%ssm/replicas/rshare' % BASE_URL)
            rshare = api_call(url, data=data, calltype='post', save_error=False)
            return rshare['id']
        except RockStorAPIException, e:
            if (e.detail == 'Replicashare(%s) already exists.' % data['share']):
                return cls.rshare_id(data['share'])
            raise e

    @staticmethod
    def create_receive_trail(rid, data):
        url = ('%ssm/replicas/rtrail/rshare/%d' % (BASE_URL, rid))
        rt = api_call(url, data=data, calltype='post', save_error=False)
        return rt['id']

    @staticmethod
    def update_receive_trail(rtid, data):
        url = ('%ssm/replicas/rtrail/%d' % (BASE_URL, rtid))
        try:
            return api_call(url, data=data, calltype='put', save_error=False)
        except Exception, e:
            msg = ('Exception while updating receive trail(%s): %s' %
                   (url, e.__str__()))
            raise Exception(msg)

    @staticmethod
    def prune_trail(url, days=1):
        try:
            data = {'days': days, }
            return api_call(url, data=data, calltype='delete', save_error=False)
        except Exception, e:
            msg = ('Exception while pruning trail for url(%s): %s' % (url, e.__str__()))
            raise Exception(msg)

    @classmethod
    def prune_receive_trail(cls, rid):
        url = ('%ssm/replicas/rtrail/rshare/%d' % (BASE_URL, rid))
        return cls.prune_trail(url)

    @classmethod
    def prune_replica_trail(cls, rid):
        url = ('%ssm/replicas/trail/replica/%d' % (BASE_URL, rid))
        return cls.prune_trail(url)

    @staticmethod
    def create_snapshot(sname, snap_name, logger, snap_type='replication'):
        try:
            url = ('%sshares/%s/snapshots/%s' % (BASE_URL, sname, snap_name))
            return api_call(url, data={'snap_type': snap_type, }, calltype='post',
                            save_error=False)
        except RockStorAPIException, e:
            if (e.detail == ('Snapshot(%s) already exists for the Share(%s).' %
                             (snap_name, sname))):
                return logger.debug(e.detail)
            raise e

    @staticmethod
    def delete_snapshot(sname, snap_name, logger):
        try:
            url = ('%sshares/%s/snapshots/%s' % (BASE_URL, sname, snap_name))
            return api_call(url, calltype='delete', save_error=False)
        except RockStorAPIException, e:
            if (e.detail == 'Snapshot(%s) does not exist.' % snap_name):
                return logger.debug(e.detail)
            raise e

    @staticmethod
    def create_share(sname, pool, logger):
        try:
            url = ('%sshares' % BASE_URL)
            data = {'pool': pool,
                    'replica': True,
                    'sname': sname, }
            headers = {'content-type': 'application/json', }
            return api_call(url, data=data, calltype='post', headers=headers,
                            save_error=False)
        except RockStorAPIException, e:
            if (e.detail == 'Share(%s) already exists. Choose a different name' % sname):
                return logger.debug(e.detail)
            raise e
